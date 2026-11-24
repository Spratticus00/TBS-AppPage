# Track Budget Save: sync between two phones

You need one always-on computer (Windows, Mac or Linux) with Tailscale, and both phones on the same tailnet.

## On the always-on computer (once)

1. Install Python 3.8+ and Tailscale, and sign in to Tailscale.
2. In the Tailscale admin console, open **DNS** and turn on **MagicDNS** and **HTTPS Certificates**.
3. Run the server:
   `python3 easyledger_sync.py`
4. It prints a line like:
   `Web app address (enter this in the web app's Sync screen): https://my-pc.tail1234.ts.net`

Keep that window open (or set it to start with the computer).

## On each phone

1. Install the Tailscale app and sign in to the same tailnet (or have the computer shared with you). Leave Tailscale on.
2. Open Track Budget Save > Settings > Sync with partner.
3. Paste the https address from step 4 and tap **Connect**.

That's all. The app picks up the access code from the server by itself. Your name comes from Settings > Appearance.

## Notes

- Sync runs while the app is open (every few seconds, and right after you change something).
- Private transactions, private categories, private merchants and accounts not shared with your partner never leave the phone.
- The iPhone app (Xcode build) works with this same server. It uses the http://100.x.y.z:8787 address and the token printed in the window.
- The server refuses requests that come from the public internet (Tailscale Funnel). Do not turn Funnel on for it.
