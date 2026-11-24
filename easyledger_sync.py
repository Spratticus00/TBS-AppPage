#!/usr/bin/env python3
"""Easy Ledger sync server.

A tiny, dependency-free server for sharing Easy Ledger data between two phones
over a private network such as Tailscale. Each person's phone writes only its
own data and reads the other person's data.

    python3 easyledger_sync.py

Python 3.8 or newer is required. No packages need to be installed.

Version 1.2 also serves the Track Budget Save web app (the version added to the
Home Screen from Safari). Safari only talks to https addresses, so the server
asks Tailscale to publish it at https://<this-computer>.<tailnet>.ts.net
("tailscale serve"). The web app then only needs that address: it fetches the
access token itself, which the server hands out only to devices on your tailnet.
"""
import argparse
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

# When started with pythonw.exe (no console window) Python has no stdout/stderr,
# so every print or log line would crash the request. Send them to a log file instead.
if sys.stdout is None or sys.stderr is None:
    _log = open(Path(__file__).with_name("server.log"), "a", buffering=1, encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = _log
    if sys.stderr is None:
        sys.stderr = _log

NAME_RE = re.compile(r"^[A-Za-z0-9 _.\-]{1,40}$")
PHOTO_RE = re.compile(r"^[A-Za-z0-9\-]{1,64}$")
MAX_PHOTO = 12 * 1024 * 1024
MAX_BODY = 25 * 1024 * 1024
LOCK = threading.Lock()

DATA_DIR = Path("easyledger-data")
TOKEN = ""
SHARE_TOKEN = True


def slug(name):
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "member"
    digest = hashlib.sha1(name.lower().encode("utf-8")).hexdigest()[:10]
    return "%s-%s" % (base, digest)


def data_path(name):
    return DATA_DIR / (slug(name) + ".json")


def key_path(name):
    return DATA_DIR / (slug(name) + ".key")


def photo_dir(name):
    return DATA_DIR / "photos" / slug(name)


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Handler(BaseHTTPRequestHandler):
    server_version = "EasyLedgerSync/1.2"

    def log_message(self, fmt, *args):
        try:
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))
        except Exception:
            pass

    # ---- helpers ----
    def end_headers(self):
        # Lets the web app (served from GitHub Pages) call this server. Access still needs the token.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, X-Member-Key")
        self.send_header("Access-Control-Max-Age", "600")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def from_internet(self):
        """True for requests that came in through Tailscale Funnel (the public internet), not your tailnet."""
        return bool(self.headers.get("Tailscale-Funnel-Request"))

    def send_json(self, status, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def authorized(self):
        header = self.headers.get("Authorization", "")
        supplied = header[7:] if header.startswith("Bearer ") else ""
        return hmac.compare_digest(supplied.encode("utf-8"), TOKEN.encode("utf-8"))

    def member_from_path(self):
        prefix = "/v1/data/"
        if not self.path.startswith(prefix):
            return None
        name = unquote(self.path[len(prefix):].split("?", 1)[0])
        return name if NAME_RE.match(name) else None

    def photo_route(self):
        """Returns (name, photo_id) for /v1/photo/<name>/<id>, or None."""
        prefix = "/v1/photo/"
        if not self.path.startswith(prefix):
            return None
        rest = self.path[len(prefix):].split("?", 1)[0]
        if "/" not in rest:
            return None
        raw_name, pid = rest.rsplit("/", 1)
        name = unquote(raw_name)
        if not NAME_RE.match(name) or not PHOTO_RE.match(pid):
            return None
        return name, pid

    # ---- routes ----
    def do_GET(self):
        route = self.path.split("?", 1)[0]
        if route == "/health":
            out = {"ok": True, "version": "1.2"}
            # Devices that can reach this server are on your tailnet, so the web app may pick up the token here.
            if SHARE_TOKEN and not self.from_internet():
                out["token"] = TOKEN
            return self.send_json(200, out)
        if self.from_internet():
            return self.send_json(403, {"error": "This server is private to your tailnet. Turn off Tailscale Funnel."})
        if not self.authorized():
            return self.send_json(401, {"error": "Wrong or missing token."})

        if route == "/v1/members":
            out = []
            with LOCK:
                for path in sorted(DATA_DIR.glob("*.json")):
                    try:
                        rec = json.loads(path.read_text("utf-8"))
                        out.append({"name": rec["name"], "rev": rec["rev"], "updatedAt": rec["updatedAt"]})
                    except (ValueError, KeyError, OSError):
                        continue
            return self.send_json(200, out)

        if route.startswith("/v1/photos/"):
            name = unquote(route[len("/v1/photos/"):])
            if not NAME_RE.match(name):
                return self.send_json(400, {"error": "Invalid name."})
            with LOCK:
                d = photo_dir(name)
                ids = sorted(p.stem for p in d.glob("*.jpg")) if d.exists() else []
            return self.send_json(200, {"ids": ids})

        if route.startswith("/v1/photo/"):
            found = self.photo_route()
            if found is None:
                return self.send_json(400, {"error": "Invalid photo."})
            name, pid = found
            with LOCK:
                p = photo_dir(name) / (pid + ".jpg")
                if not p.exists():
                    return self.send_json(404, {"error": "No such photo."})
                body = p.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if route.startswith("/v1/data/"):
            name = self.member_from_path()
            if name is None:
                return self.send_json(400, {"error": "Invalid name."})
            with LOCK:
                path = data_path(name)
                if not path.exists():
                    return self.send_json(404, {"error": "No data for that name yet."})
                body = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_json(404, {"error": "Not found."})

    def put_photo(self):
        found = self.photo_route()
        if found is None:
            return self.send_json(400, {"error": "Invalid photo."})
        name, pid = found
        member_key = self.headers.get("X-Member-Key", "")
        if len(member_key) < 16:
            return self.send_json(400, {"error": "Missing device key."})
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_PHOTO:
            return self.send_json(413, {"error": "Photo is empty or too large."})
        body = self.rfile.read(length)
        with LOCK:
            kp = key_path(name)
            if not kp.exists() or not hmac.compare_digest(kp.read_text("utf-8").strip(), sha256(member_key)):
                return self.send_json(403, {"error": "Not allowed."})
            d = photo_dir(name)
            d.mkdir(parents=True, exist_ok=True)
            tmp = d / (pid + ".tmp")
            tmp.write_bytes(body)
            os.replace(str(tmp), str(d / (pid + ".jpg")))
        self.send_json(200, {"ok": True})

    def do_PUT(self):
        if self.from_internet():
            return self.send_json(403, {"error": "This server is private to your tailnet."})
        if not self.authorized():
            return self.send_json(401, {"error": "Wrong or missing token."})
        if self.path.startswith("/v1/photo/"):
            return self.put_photo()
        name = self.member_from_path()
        if name is None:
            return self.send_json(400, {"error": "Invalid name. Use letters, numbers and spaces, up to 40 characters."})

        member_key = self.headers.get("X-Member-Key", "")
        if len(member_key) < 16:
            return self.send_json(400, {"error": "Missing device key."})

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY:
            return self.send_json(413, {"error": "Body is empty or too large."})
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except ValueError:
            return self.send_json(400, {"error": "Body is not valid JSON."})

        with LOCK:
            kp = key_path(name)
            hashed = sha256(member_key)
            if kp.exists():
                if not hmac.compare_digest(kp.read_text("utf-8").strip(), hashed):
                    return self.send_json(403, {"error": "That name is already used by another device. Pick a different name."})
            else:
                kp.write_text(hashed, "utf-8")

            path = data_path(name)
            rev = 0
            if path.exists():
                try:
                    rev = int(json.loads(path.read_text("utf-8")).get("rev", 0))
                except (ValueError, OSError):
                    rev = 0
            # Keep the last few versions so a bad erase or restore on a phone can be recovered by hand.
            if path.exists():
                try:
                    hist = DATA_DIR / "history"
                    hist.mkdir(exist_ok=True)
                    (hist / ("%s-rev%06d.json" % (slug(name), rev))).write_bytes(path.read_bytes())
                    old = sorted(hist.glob(slug(name) + "-rev*.json"))
                    for extra in old[:-5]:
                        extra.unlink()
                except OSError:
                    pass
            rec = {"name": name, "rev": rev + 1, "updatedAt": now_iso(), "payload": payload}
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(rec), "utf-8")
            os.replace(str(tmp), str(path))
            self.prune_photos(name, payload)
        self.send_json(200, {"rev": rec["rev"], "updatedAt": rec["updatedAt"]})

    def prune_photos(self, name, payload):
        """Removes stored photos that the member's data no longer refers to."""
        try:
            d = photo_dir(name)
            if not d.exists():
                return
            used = set()
            for t in payload.get("txns", []):
                used.update(t.get("photoIDs", []))
            for c in payload.get("categories", []):
                if c.get("photoID"):
                    used.add(c["photoID"])
            for p in d.glob("*.jpg"):
                if p.stem not in used:
                    p.unlink()
        except (OSError, AttributeError, TypeError):
            pass

    def do_DELETE(self):
        if self.from_internet():
            return self.send_json(403, {"error": "This server is private to your tailnet."})
        if not self.authorized():
            return self.send_json(401, {"error": "Wrong or missing token."})
        name = self.member_from_path()
        if name is None:
            return self.send_json(400, {"error": "Invalid name."})
        member_key = self.headers.get("X-Member-Key", "")
        with LOCK:
            kp = key_path(name)
            if not kp.exists() or not hmac.compare_digest(kp.read_text("utf-8").strip(), sha256(member_key)):
                return self.send_json(403, {"error": "Not allowed."})
            for p in (data_path(name), kp):
                try:
                    p.unlink()
                except OSError:
                    pass
            try:
                for p in photo_dir(name).glob("*"):
                    p.unlink()
            except OSError:
                pass
        self.send_json(200, {"ok": True})


def load_token(cli_token):
    token_file = DATA_DIR / "token.txt"
    if cli_token:
        return cli_token
    if os.environ.get("EASYLEDGER_TOKEN"):
        return os.environ["EASYLEDGER_TOKEN"]
    if token_file.exists():
        return token_file.read_text("utf-8").strip()
    token = secrets.token_urlsafe(18)
    token_file.write_text(token, "utf-8")
    try:
        os.chmod(str(token_file), 0o600)
    except OSError:
        pass
    return token


def tailscale_ip():
    """The machine's Tailscale address, so the server is only reachable inside your tailnet."""
    import shutil
    import subprocess
    exe = shutil.which("tailscale")
    candidates = [exe] if exe else []
    candidates += [r"C:\Program Files\Tailscale\tailscale.exe", "/Applications/Tailscale.app/Contents/MacOS/Tailscale"]
    for c in candidates:
        try:
            out = subprocess.run([c, "ip", "-4"], capture_output=True, text=True, timeout=5)
            ip = out.stdout.strip().splitlines()[0].strip() if out.returncode == 0 and out.stdout.strip() else ""
            if re.match(r"^\d+\.\d+\.\d+\.\d+$", ip):
                return ip
        except (OSError, subprocess.SubprocessError):
            continue
    return ""


def tailscale_exe():
    import shutil
    exe = shutil.which("tailscale")
    for c in ([exe] if exe else []) + [r"C:\Program Files\Tailscale\tailscale.exe", "/Applications/Tailscale.app/Contents/MacOS/Tailscale"]:
        if c and os.path.exists(c):
            return c
    return ""


def publish_https(port):
    """Asks Tailscale to publish this server at https://<computer>.<tailnet>.ts.net for the web app.
    Returns that address, or "" with a printed explanation if it could not be done."""
    import subprocess
    exe = tailscale_exe()
    if not exe:
        print("Web app: Tailscale was not found, so no https address was set up.")
        return ""
    try:
        st = subprocess.run([exe, "status", "--json"], capture_output=True, text=True, timeout=10)
        dns = json.loads(st.stdout).get("Self", {}).get("DNSName", "").rstrip(".") if st.returncode == 0 else ""
    except (OSError, ValueError, subprocess.SubprocessError):
        dns = ""
    try:
        r = subprocess.run([exe, "serve", "--bg", "--https=443", "http://127.0.0.1:%d" % port], capture_output=True, text=True, timeout=30)
        ok = r.returncode == 0
        msg = (r.stdout + r.stderr).strip()
    except (OSError, subprocess.SubprocessError) as e:
        ok, msg = False, str(e)
    if not ok:
        print("Web app: could not set up the https address automatically.")
        if msg:
            print("  Tailscale said: " + msg.splitlines()[-1])
        print("  In the Tailscale admin console, turn on MagicDNS and HTTPS Certificates (DNS page), then run:")
        print("    tailscale serve --bg --https=443 http://127.0.0.1:%d" % port)
        return ""
    return ("https://" + dns) if dns else ""


def main():
    global DATA_DIR, TOKEN, SHARE_TOKEN
    ap = argparse.ArgumentParser(description="Easy Ledger sync server")
    ap.add_argument("--host", default="", help="address to listen on (default: this PC's Tailscale address)")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--data", default="easyledger-data", help="folder for stored data")
    ap.add_argument("--token", default="", help="shared secret (otherwise one is generated and saved)")
    ap.add_argument("--no-web", action="store_true", help="do not set up the https address for the web app")
    ap.add_argument("--keep-token-private", action="store_true", help="never hand the token to the web app (people then type it in)")
    args = ap.parse_args()
    SHARE_TOKEN = not args.keep_token_private

    host = args.host
    if not host:
        host = tailscale_ip()
        if host:
            print("Listening only on your Tailscale address %s." % host)
        else:
            sys.exit("Could not find Tailscale, so the server will not start (it would listen on every network). Start Tailscale, or pass --host with your Tailscale IP.")
    DATA_DIR = Path(args.data)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN = load_token(args.token)
    if len(TOKEN) < 8:
        sys.exit("The token must be at least 8 characters.")

    httpd = ThreadingHTTPServer((host, args.port), Handler)
    print("Easy Ledger sync server running on %s:%d" % (host, args.port))
    print("Data folder: %s" % DATA_DIR.resolve())
    print("Token (enter this in the iPhone app): %s" % TOKEN)
    if not args.no_web and host not in ("127.0.0.1", "localhost"):
        # Tailscale's https front door forwards to this computer only (127.0.0.1), never the wider network.
        try:
            local = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
            threading.Thread(target=local.serve_forever, daemon=True).start()
        except OSError as e:
            local = None
            print("Web app: could not listen on 127.0.0.1:%d (%s)." % (args.port, e))
        if local:
            url = publish_https(args.port)
            if url:
                print("")
                print("Web app address (enter this in the web app's Sync screen): %s" % url)
                print("")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
