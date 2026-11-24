## Install on an iPhone
Open the link in Safari, tap Share, then "Add to Home Screen".

## Updating
Updates come automatically when the owner makes changes to the app. People get it the next time they open the app while online.

## What is saved, and what is not

- Everything you add, including photos, is stored in this browser on the phone (IndexedDB) and is there when you reopen the app.
- A backup is saved automatically each day (last 7 kept). "Save a backup to Files" makes a real file; with a backup password it is encrypted (AES-GCM).
- The PIN locks the app when it opens. It is stored scrambled, but it only hides the screen: the data itself is not encrypted on the phone.
- "Share my data with partner" makes a file; "Import Partner Data" reads one.
- Clearing Safari website data, or deleting the home-screen app, erases the data. Keep a backup file in Files or iCloud Drive.
- Sync with a partner works through the sync server (see sync-server/SETUP.md) while the app is open.

## Updating safely

- Your data, photos, background image, colors and widget order are stored in the installed app's own storage, separate from the code. Uploading new files to GitHub never touches it.
- The first time a new version opens, it saves a copy of your data first ("Before the last app update" under Settings > Backups and safety).
- If a new version can't read the saved data, it changes nothing and saves nothing.
- Do not delete the Home Screen icon to update. On iPhone that erases the installed app's data. Updates arrive on their own: close and reopen the app.

# Track-Budget-Save

<img width="180" height="180" alt="Image" src="https://github.com/user-attachments/assets/845a186d-c497-4ba5-826b-3c7bcb90375c" />

Track Budget Save is a native SwiftUI budgeting app for iPhone (iOS 17+). Everything stays on your device: there are no accounts, no bank logins and no analytics, and CSV files are read on the phone and never uploaded.  Check out the User Guide PDF under the new release for a full breakfown of the app!

## Features

### Summary
- Month navigator with net, income and spending
- Six-month chart as bars, pie or line
- Spending by category against monthly budgets
- Goals and rearrangeable widgets
- A hide-amounts button for private viewing
- Current and saved monthly PDF statements

### Activity
- Searchable, filterable transaction list grouped by day with running balances
- Transaction editor with split transactions, photos, comments and notes
- Swipe actions, bulk edit and saved filters

### Accounts
- Checking, savings, cards, loans, cash and brokerage
- Six-month Net Worth trend
- Bank CSV import with duplicate detection and your own merchant rules (your categories always win over the bank's)

### Alerts
- Bill reminders and budget warnings
- Unusual-charge alerts
- A review queue for transactions that need a category

### Partner sharing
- Sync over Tailscale to a self-hosted server
- Air sync between two nearby phones, with no internet needed
- Share and import a data file
- View your own, your partner's, or combined data
- Private items never leave your phone

### Settings
- Recurring transactions, quick add, smarter imports, insights and budget pacing
- Appearance options including background, widget color and an optional bunny companion

### Security and reliability
- PIN and Face ID lock, with a Forgot PIN reset that erases data after two confirmations
- Encrypted backups, restore and hourly safety copies
- Amounts stored as whole cents so totals always add up

## Tech

SwiftUI, Keychain, Multipeer Connectivity and URLSession. An optional Python sync server (easyledger_sync.py) binds to a Tailscale address and uses hashed paths and token authentication.
