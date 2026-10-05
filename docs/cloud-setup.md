# Cloud setup: scan to OneDrive, everything else automatic, PC can be off

## How it works once set up
1. You (or Wahidullah) open the **OneDrive app > + > Scan**, photograph the receipt, save to
   `Desktop > VAT RETURNS > Receipts Inbox`. Emailed receipts need nothing: they are picked up from Gmail.
2. Every night at 20:30 UTC (21:30 UK summer time) a Claude agent in Anthropic's cloud:
   mirrors the VAT RETURNS folder (downloads only the trackers and the inbox), fetches new receipt
   emails, logs each new expense in the Sept-Dec tracker, renames and files the receipt in its vendor
   folder, verifies the tracker, and pushes the changes back to OneDrive.
3. You get an email only when an expense was logged, something needs you, or something failed.
   Silence otherwise. Each run adds a line to `VAT RETURNS\_automation\run-log.md`.

Safety: nothing is ever deleted in OneDrive; every tracker write is backed up to `_backups`; the
tracker is only uploaded if nobody edited it during the run (otherwise nothing is pushed and the next
night retries); V18 is never changed; the agent cannot delete tracker rows.

## One-time setup (about 25 minutes, on the PC)

### 1. Google (Gmail + a hidden Drive folder for the job's sign-in)
1. https://console.cloud.google.com (signed in as fonenovaltd@gmail.com) > create project `fonenova-expenses`.
2. APIs and Services > Library: enable **Gmail API** and **Google Drive API**.
3. OAuth consent screen: External; app name `Fone Nova expenses`; add test user fonenovaltd@gmail.com;
   then **Publish app** (otherwise Google expires the sign-in every 7 days). The "unverified app"
   warning at sign-in is expected for your own app: Advanced > continue.
4. Credentials > Create credentials > OAuth client ID > **Desktop app** > Download JSON.
5. Save it as `C:\Users\fonen\fonenova-expenses\secrets\credentials.json`.
6. In PowerShell:
   `cd C:\Users\fonen\fonenova-expenses; .venv\Scripts\python.exe -m fonenova.cli gmail-auth`
   Approve in the browser (Gmail read, send-to-self, and the app's own hidden Drive folder only).

### 2. Microsoft (OneDrive access for the cloud job)
1. https://portal.azure.com (sign in with the Microsoft account that owns the OneDrive) >
   search **App registrations** > New registration.
2. Name `Fone Nova expenses`; Supported account types: **Personal Microsoft accounts only**; Register.
3. Copy the **Application (client) ID** and paste it into `config.toml` under `[cloud] ms_client_id`.
   (Not a secret.)
4. Authentication > Advanced settings > **Allow public client flows: Yes** > Save.
5. In PowerShell: `.venv\Scripts\python.exe -m fonenova.cloud ms-auth`
   It prints a code and a URL; open the URL, enter the code, approve. It stores the sign-in in the
   hidden Google folder from step 1 and confirms the VAT RETURNS folder is visible.

### 3. GitHub (the cloud job runs the code from here)
1. https://github.com > New repository > name `fonenova-expenses` > **Private** > Create (no README).
2. Tell Claude the repo URL; Claude pushes the code (`secrets\`, `state\`, `out\` and spreadsheets
   are excluded by .gitignore, so no tokens or financial files go to GitHub).
3. At https://claude.ai/code, connect GitHub if asked and give it access to this repo.

### 4. Cloud environment (claude.ai/code > environment "OneDrive" > settings)
Add environment variables:
- `GOOGLE_TOKEN_JSON` = the whole content of `C:\Users\fonen\fonenova-expenses\secrets\token.json`
- `MS_CLIENT_ID` = the Application (client) ID from step 2
Treat GOOGLE_TOKEN_JSON like a password: paste it only into that settings page.

### 5. Claude creates the routine and runs it once while you watch
Then the PC task can be switched off.

## Your routine afterwards
- Scan receipts into **Receipts Inbox**. That is all.
- Tell Wahidullah to scan too, and to stop typing rows into the spreadsheet (the job still repairs
  hand-typed rows, but scanning is cleaner).
- If an email says "action needed", reply to Claude in a session or fix the item it names.
