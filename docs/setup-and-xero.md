# Setup steps for Hamza, and the Xero recommendation

## A. To switch on the daily routine (about 15 minutes, once)
1. **Gmail API client** (Google Cloud Console, signed in as fonenovaltd@gmail.com):
   1. Create a project, e.g. "fonenova-expenses".
   2. APIs and Services > Library > enable **Gmail API**.
   3. OAuth consent screen: External, app name "Fone Nova expenses", status **Testing**, add test user fonenovaltd@gmail.com.
   4. Credentials > Create credentials > OAuth client ID > **Desktop app**. Download the JSON.
   5. Save it as `C:\Users\fonen\fonenova-expenses\secrets\credentials.json`.
2. Sign in once (opens the browser, grants read + send-to-self):
   `C:\Users\fonen\fonenova-expenses\.venv\Scripts\python.exe -m fonenova.cli gmail-auth` (run from the repo folder).
   Note: in "Testing" status Google expires the refresh token after 7 days. Either re-run gmail-auth weekly, or publish the app (OAuth consent screen > Publish; unverified is fine for your own account) so the token lasts.
3. Register the scheduled task (21:30 daily, catches up after the PC was off):
   `powershell -ExecutionPolicy Bypass -File C:\Users\fonen\fonenova-expenses\routine\register-task.ps1`
4. Keep Excel closed in the evening. If the tracker is open, the run logs nothing and tells you.
5. The PC must be on and logged in at some point each day (OneDrive must be syncing).

Notifications: a Windows toast plus an email to fonenovaltd@gmail.com, only when something is logged, needs you, fails, or a deadline is near. Silence otherwise. Every run appends one line to `docs/run-log.md`.

## B. Long-term: Xero receipt capture + Revolut feed (recommended)
**Recommendation: move day-to-day expenses into Xero from 1 Nov 2026 (start of the next VAT period), keep Excel only for May to Oct.** Ranked:

1. **Xero Expenses/Hubdoc capture + Revolut Business bank feed (pick this).** Every card transaction arrives from the feed; you snap or forward the receipt; Xero OCR reads vendor, date, total and VAT; you (or a rule) code it; reconciliation matches it to the bank line. VAT return is produced by Xero and can be filed via MTD directly. Removes: the spreadsheet, formula ranges, Wahidullah's half-typed rows, the OneDrive sync problems, and the daily script's tracker writes.
   - Hidden costs: you need a Xero plan that includes Expenses (Standard or above; check your current plan, Expenses is a per-user add-on on some plans). Coding rules take an hour or two to set up. Someone still has to reconcile weekly (10 to 15 minutes).
   - Risk: the margin scheme and Mobile One reverse-charge purchases must be set up correctly in Xero's VAT settings by the accountant, or Xero's VAT return will be wrong. Get the accountant to set the VAT scheme before the first Xero-filed return.
2. **Keep this Python routine as the bridge** until 7 Nov (it already works) and for any receipts that only arrive by email.
3. Dext or AutoEntry in front of Xero: better OCR, extra monthly cost. Not needed at your volume (about 60 to 80 receipts a month).

### What you need to do yourself for Xero
1. Confirm the Revolut Business GBP feed in Xero is live and current (Accounting > Bank accounts). Add the EUR account feed too.
2. Ask the accountant to: set the VAT scheme and rates (standard, zero, exempt, no VAT, reverse charge, margin scheme), and create expense accounts matching how the sheet categorises things (motor/EV charging, travel, subsistence, office rent, software, phone, postage/shipping, bank fees, rent).
3. Install the **Xero Me** app on your phone and Wahidullah's; set it to "Expenses" capture. Forward email receipts to your Xero receipts inbox address (Xero > Business > Expenses or Hubdoc email).
4. Add bank rules for the regulars (Tesla, Tesco, Lidl, Translink, Greater Anglia, HQ-IWG, Anthropic, Xero, Google Workspace) so they code automatically with the right VAT.
5. From 1 Nov: stop adding rows to the Sept-Dec tracker. I will then switch the daily routine to read Xero (connector or API) and only alert you about bank lines with no receipt attached.
