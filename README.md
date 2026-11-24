# Track Budget Save iPhone Preview

A web preview of the Track Budget Save iPhone app. It uses example data only.

## Put it on GitHub Pages
1. Create a new public repository on GitHub, for example `tbs-preview`.
2. Upload every file in this folder to the main branch (including `.nojekyll`).
3. In the repository, open Settings, then Pages. Under "Build and deployment" choose "Deploy from a branch", pick `main` and `/ (root)`, and save.
4. After a minute the site is live at `https://YOUR-USERNAME.github.io/tbs-preview/`.

## Install on an iPhone
Open the link in Safari, tap Share, then "Add to Home Screen".

## Updating
Replace `index.html` on GitHub with the new version. People get it the next time they open the app while online.

## What is saved, and what is not (v3)

- Everything you add, including photos, is stored in this browser on the phone (IndexedDB) and is there when you reopen the app.
- A backup is saved automatically each day (last 7 kept). "Save a backup to Files" makes a real file; with a backup password it is encrypted (AES-GCM).
- The PIN locks the app when it opens. It is stored scrambled, but it only hides the screen: the data itself is not encrypted on the phone.
- "Share my data with partner" makes a file; "Import Partner Data" reads one. This works between two people using this preview only.
- Clearing Safari website data, or deleting the home-screen app, erases the data. Keep a backup file in Files or iCloud Drive.
- Not possible in a web app: Face ID, live sync, Siri/Shortcuts, push notifications.

## Updating safely (v9)

- Your data, photos, background image, colors and widget order are stored in the installed app's own storage, separate from the code. Uploading new files to GitHub never touches it.
- The first time a new version opens, it saves a copy of your data first ("Before the last app update" under Settings > Backups and safety).
- If a new version can't read the saved data, it changes nothing and saves nothing.
- Do not delete the Home Screen icon to update. On iPhone that erases the installed app's data. Updates arrive on their own: close and reopen the app.
- When you publish a new version, change APPVER in index.html (search for `var APPVER=`) and the cache name in sw.js.
