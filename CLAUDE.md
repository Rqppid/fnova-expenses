# Fone Nova Ltd: expense tracking, filing and automation

Full briefing: `docs/context.md`. Row-by-row history: `docs/handoff.md`. Run history: `docs/run-log.md`.

## How Hamza wants Claude to work
- Be direct. Lead with the answer or recommendation, then reasoning. No filler, no hedging, no restating the question.
- Bullets or tables over paragraphs. Rank options and name the one you would pick.
- Flag hidden costs and VAT, legal, regulatory and reputational risk unprompted. Give the honest read.
- NEVER use em dashes.
- Report payments and new expenses as separate line items. Never combine them into one total.
- Default to doing and flagging, not asking. Only ask when a decision is genuinely Hamza's and irreversible.
- Every expense is a business expense. Do not flag purpose, personal use or director's-loan/BIK.
- Never delete anything without asking. Files are moved, never copied.

## Paths
- Root: `C:\Users\fonen\OneDrive\Desktop\VAT RETURNS\` (see `config.toml`). Edit files there directly. Never use a connector or upload/download workflow.
- Live tracker: `VAT Return-SEPT-DEC\VAT Return From Sept-Dec, 2026.xlsx`, receipts in `VAT Return-SEPT-DEC\Receipts, Invoices-Sept-Dec,2026\<Vendor>\`.
- V18 (May to Sept, closed, flag only, never auto-add): `VAT Return-May-Sept-26\VATReturn_Automated_v18_delivered_1.xlsx`, receipts in `Receipts-Invoice-VAT-Return-May-Sept, 26\`.
- Backups: `VAT RETURNS\_backups\<timestamp>\` (made automatically before every write).
- This repo lives outside OneDrive on purpose (a `.git` folder inside OneDrive gets corrupted by sync).

## The task
Keep an accurate, auditable log of every business expense receipt for the VAT return. Each receipt is filed in a vendor folder as `Vendor-DD.MM.YY.ext`, and VAT treatment is decided per row. Long term: Xero receipt capture plus the Revolut bank feed.

**VAT return: May to Oct 2026, one return, due 7 November 2026.** V18 (May to Sept) plus the Sept-Dec tracker's Sept and Oct rows. Nov/Dec rows belong to the next return.

### Sept-Dec Sheet2 layout
D Dated (text DD.MM.YY), E Beneficiary, G Description, I Amount (numeric gross), K Ref No, N "Receipt:Yes", P "VAT-Yes"/"VAT-No", Q VAT amount, R Remarks, U date helper, V VAT auto-calc, W VAT check. Data starts at row 5. "Total :" (col D, `=SUM(I5:In)`) and "Net Total (Gross - VAT):" (`=I{total}-SUM(Q5:Qn)`) sit directly below the last data row. Find them by scanning column D, never hardcode. Sheet1 B5:C8 hold 8 SUMIFS over the I, Q and U ranges, which must all end at the last data row. V18 uses AB/AC/AD for the helpers.

Always use the tooling (`python -m fonenova.cli ...`) for writes. It backs up, writes, re-reads and verifies.

## Standing decisions (apply without asking)
1. Card-ending variations (4251, 9873, Apple Pay, Google Pay) are normal. Never flag them.
2. Receipts Hamza sends directly are logged, not held, even with no text or an ambiguous vendor. Flag issues in Remarks.
3. Every expense is a business expense (5 Oct 2026). Old Remarks still contain retired purpose wording.
4. Still flag: VAT treatment uncertainty, missing/unreadable receipts, duplicates, unverified vendor VAT registration, donation tax treatment (BMCA), real data errors.
5. When a receipt prints an explicit VAT rate or amount, use it (VAT-Yes). Split-rate baskets (Lidl): use the printed VAT and ignore the W "Check VAT amount" flag.
6. No prior row and nothing printed: VAT-No, remark "not independently verified".
7. Tesco defaults to VAT-No, with a stronger note when the basket is mostly standard-rated.
8. Train/bus tickets are VAT-No (zero-rated passenger transport).
9. Receipts dated outside a tracker's own period are not logged in it.
10. An invoice or notice of a future Direct Debit is not logged until settled. A declined provisional booking with no prepayment is not logged.
11. Direct Debits are logged against the debit-clear date.
12. Wholesale stock invoices (Mobile One, WavePhone, Phone-Zone, etc.) are a different category and are NOT logged.
13. V18's 5 unconfirmed items stay unlogged unless Hamza says so: Pizza Passions £10.49, B&M Cityside £9.22, ABN Invest INV-0004 £200, Invoice2go Aug renewal, B&Q £6.62.
14. The bank statement is authoritative.

## Known failure modes
- Wahidullah types rows straight into Excel, which leaves half-finished rows (text "£" amounts, no Remarks, no helpers, ranges not extended). Sweep the FULL range every run (`audit`) and complete rows in place.
- OneDrive can silently revert writes or lag. verify() re-reads from disk and checks the hash changed.
- Excel open on the PC blocks writes (`~$` lock file). The tooling refuses to write. Ask Hamza to close Excel.
- A receipt matching an existing row (either tracker) is a duplicate or supplementary, never a new row. Check byte size/hash against filed copies.

## Commands (run from the repo: `.venv\Scripts\python.exe -m fonenova.cli <cmd>`)
- `status`, `audit [--out FILE] [--matches]`, `find --date DD.MM.YY --amount N`, `pack` (return pack to `out/`)
- `add ...`, `complete --row N ...`, `delete --row N --expect-date ... --expect-vendor ... --expect-amount ...`
- `file --src PATH --vendor V --date DD.MM.YY [--folder F] [--descriptor X]`, `archive --path FILE`
- `verify`, `backup`, `diff BEFORE AFTER`, `gmail-auth`, `daily [--no-claude]`
- Tests: `.venv\Scripts\python.exe -m pytest -q` (use temp copies of the 2026-10-05 reference backup, never the live file).
- Setup and Xero plan: `docs/setup-and-xero.md`. Daily prompt: `routine/daily-prompt.md`.

## Cloud mode (PC off)
- Receipts are scanned into `VAT RETURNS\Receipts Inbox` (OneDrive app > Scan). Gmail receipts land in `Receipts Inbox\gmail`.
- Nightly cloud routine: `routine/cloud-routine.md` -> `python -m fonenova.cloud prep --dest /tmp/vat`, work via `python -m fonenova.cli --mirror /tmp/vat ...`, then `python -m fonenova.cloud finish --dest /tmp/vat`.
- Mirror rules and safety: see the docstring of `fonenova/cloud.py`. Setup: `docs/cloud-setup.md`.
- Run state and run log: `VAT RETURNS\_automation\` (shared by PC and cloud runs). Never run the PC task and the cloud routine on the same night once cloud is live.

## Capture channels and conventions (06.10.26)
- WhatsApp bot (Meta test number for now): Hamza and Wahidullah send photos, PDFs, Revolut statements (CSV preferred) or FX confirmations. Files land in `Receipts Inbox/whatsapp/`, an instant cloud run logs them and replies in the chat. Results are copied to the other allowed numbers except where `config.toml [whatsapp.no_copy]` mutes them (Hamza's uploads are not copied to Wahidullah). Code: `fonenova/whatsapp.py`, webhook `api/whatsapp.py` (Vercel). Setup: `docs/whatsapp-setup.md`.
- Photos are filed as clean greyscale PDFs (`file --to-pdf`, `fonenova/imaging.py`), never 1-bit black and white. Originals are kept in `Receipts Inbox/processed/<date>/`.
- Bank statements: `statement --path FILE [--log]` (`fonenova/statements.py`). Unmatched card payments and fees are logged VAT-No with "RECEIPT MISSING"; a later receipt completes that row instead of adding one. Transfers, top-ups, refunds and wholesale are never logged automatically.
- FX: `fx` records EUR->GBP conversions on the "FX Exchanges (Reference)" sheet (not in VAT totals); the fee is an expense row VAT-No.
- One run at a time: `_automation/run.lock` in OneDrive (updated in place, never deleted).
