# Fone Nova Ltd: Expense Tracking, Filing and Automation. Context Export

Exported 5 Oct 2026 from Claude (Cowork) memory plus the "Expenses" project docs. Use this as the starting CLAUDE.md or context file for Claude Code. It is a condensed but complete record of what Claude knew. Verbatim project docs (long rolling changelog) are still in the claude.ai "Expenses" project under `claude/`.

---

## 1. How the owner wants Claude to behave (standing preferences)

- Be direct. No filler, no hedging, no restating the question. Lead with the answer or recommendation, then reasoning.
- Bullets or tables over paragraphs when comparing options. Rank options and name the one you would pick.
- Default lens: profitability, risk, time/effort cost, downside. Flag hidden costs, legal/regulatory and reputational risk unprompted. Give the honest read, not the agreeable one.
- NEVER use em dashes.
- When reporting payments or amounts, never combine several into one total. List each as a separate line item.
- Too much back-and-forth frustrates him (said plainly 27 Sept). Default to logging and flagging, not pausing to ask.

## 2. Who and what

- User: Hamza Ismati. Runs the day-to-day of Fone Nova Ltd (B2B phone/electronics wholesale, Belfast, NI). Lives at 148 Cliftonpark Avenue, Belfast.
- Official director: his father Wahidullah Ismati (Companies House and HMRC correspondence is signed by him). Hamza is NOT a director or shareholder. Both are on the payroll.
- Company: Fonenova Ltd, reg NI737184. Registered office Unit 7A-7B Weavers Court, Weavers Business Park, Belfast BT12 5GH. VAT XI516452304 (also GB516452304000 / XI EORI XI516452304000). Email fonenovaltd@gmail.com (Gmail main, Outlook sub).
- Business: buys phones from Mobile One Trade B.V. (NL, EUR, reverse-charge invoicing), sells to WavePhone B.V. (92% of sales), TradeWise SIA, EU Telecoms BL EOOD, others, using the UK VAT margin scheme. Sells in EUR. Revenue only started May 2026. Running on a loan (~£10k, take with a pinch of salt) covering office rent, home rent and other expenses.
- Tools: OneDrive (personal Microsoft account, main storage), Gmail, Excel, Xero (accounting and payroll, Revolut Business GBP bank feed), Revolut Business, Invoice2Go (sales invoices), Zapier, Vercel (fonenova.com, Next.js/shadcn).
- VAT status: registration was cancelled by HMRC (effective 1 May 2026, found invalid on VIES 22 July). Reinstated late Sept 2026 (Wahidullah's own email to HMRC EORI team 1 Oct says so; not independently confirmed by an official HMRC letter seen by Claude). EORI (GB and XI) reinstatement confirmed by HMRC EORI team 5 Oct, REQ0487686, no new numbers, go-live date pending. HMRC digital support case QUQD-9785-BXOK investigating the online EORI application error. MP Claire Hanna (SDLP) escalated the original case (ref CE/4669015/2026).
- Other live business threads (context only, not expenses): Back Market B2C launch (trading name "Quay Phone" under the same Ltd, marketplaces only, no own website checkout), Winterburn's/EU Telecoms deal (flow Winterburn's to Mobile One to FoneNova to Eu Telecoms, EUR, 4-week runway, trial first), Mobile Menders (stalled, Mobile One cannot supply), Somalia dropship deal via Suleiman Abdulahi (landed-price quote, ship direct), Apollo lead list (16 rows ready), GSM exchange applications (gsmExchange reapply Jan 2027).

## 3. THE TASK: expense tracking, filing, automation

### Goal
Keep an accurate, auditable log of every business expense receipt for the VAT return, filed in vendor folders with a consistent naming convention, with VAT treatment decided per row. Long term goal (decided 2 Sept): move day-to-day receipt capture onto Xero (receipt capture app plus bank feed) so Excel upkeep stops. Going forward only, no migration of the old Excel trackers.

### VAT return period
Q3+Q4 combined: May to October 2026 (6 months), one return, **due 7 November 2026**. V18 (May to Sept) plus the Sept-Dec tracker's Sept and Oct rows make up this return. Nov/Dec rows belong to the next return.

### Files and locations (Hamza's PC, `fonenova`, Windows)
Root: `C:\Users\fonen\OneDrive\Desktop\VAT RETURNS\`
- `VAT Return-SEPT-DEC\VAT Return From Sept-Dec, 2026.xlsx` : the LIVE tracker. Sheets: `Sheet1` (summary, SUMIFS in B5:C8, 4 months x I/Q/U ranges), `Sheet2` (expense log), `FX Exchanges (Reference)`.
- `VAT Return-SEPT-DEC\Receipts, Invoices-Sept-Dec,2026\` : vendor subfolders (Tesco, Tesla, Lidl, Lime, DHL-Express, Flat Deposit+Rents, HQ-IWG-Service, Stansted Express Train-Bus Service, Translink Bus-B Int Airport, Restaurant-Takeaway, Various Receipts, and about 20 more).
- `VAT Return-May-Sept-26\VATReturn_Automated_v18_delivered_1.xlsx` : V18, May to Sept, effectively closed. Receipts in `Receipts-Invoice-VAT-Return-May-Sept, 26\`. Different column layout (helpers in AB/AC/AD). 313 data rows. Convention: flag new items, do not auto-add.
- `VAT RETURN-Feb-Apr,26- Q1 2026\` : Q1 tracker, never reviewed.

### Sheet2 column layout (Sept-Dec tracker)
D Dated (text DD.MM.YY), E Beneficiary, G Description, I Amount (numeric, gross), K Ref No, N "Receipt:Yes", P VAT flag ("VAT-Yes" or "VAT-No"), Q VAT amount, R Remarks, U date-parse helper, V VAT auto-calc, W VAT check. Data starts row 5. A "Total :" row (col D, SUM of I) and a "Net Total (Gross - VAT):" row (=Total - SUM(Q)) sit directly below the last data row. Find them by scanning column D, never hardcode.
Helper formulas (row r):
- U: `=IFERROR(DATE(2000+VALUE(RIGHT(Dr,2)),VALUE(MID(Dr,4,2)),VALUE(LEFT(Dr,2))),0)`
- V: `=IF(Pr="VAT-Yes",ROUND(Ir/6,2),IF(Pr="VAT-No",0,""))`
- W: `=IF(Pr="VAT-Yes",IF(ABS(Qr-Vr)<0.02,"OK","Check VAT amount"),IF(OR(Pr="VAT-No",Pr=""),"","Check VAT flag"))`
Sheet1 SUMIFS (8 of them): `=SUMIFS(Sheet2!$I$5:$I$N,Sheet2!$U$5:$U$N,">="&DATE(y,m,1),Sheet2!$U$5:$U$N,"<"&DATE(y,m+1,1))` for I, and the same with Q. All three ranges (I, Q, U) must be extended to the last data row whenever a row is added.

### Naming and filing convention
`Vendor-DD.MM.YY.ext` (2-digit year), moved into a vendor subfolder inside that tracker's own receipts folder; create the subfolder for a new vendor. One-off restaurants/takeaways share `Restaurant-Takeaway\`. Same-day duplicates get a descriptor (`Asda-BathSheets-16.09.26.pdf`). If Hamza or Wahidullah already filed it sensibly, leave it. The old "file-and-rename" step copied rather than moved the original, so loose originals at the receipts root are usually harmless duplicates (check byte size against the filed copy before treating as new).

### Daily routine (what the scheduled "Fone Nova daily expense check" does)
1. Read handoff doc for current rows, totals, open flags.
2. Full two-way reconciliation: every tracker row has a correctly named receipt, a numeric Amount, correct VAT treatment, Remarks citing the matched file, U/V/W helpers, and is inside Total/Net Total and all 8 Sheet1 ranges; every receipt file has a row. Check the FULL row range, not just recent rows.
3. New receipts from three sources: receipts folders (vendor folders AND loose roots of both trackers), Gmail (fonenovaltd@gmail.com, receipt/invoice/order/confirmation emails; the Gmail connector reads body text but cannot download attachments), and anything Hamza sends in chat.
4. Check each candidate against both trackers before treating it as new. A receipt matching an existing row is a duplicate or supplementary, never a new row.
5. Log new rows immediately above the Total row, complete half-finished rows in place, extend formulas and ranges, rename and file the receipt.
6. Verify every write with a genuine content re-read, not just size or mtime.
7. Update the handoff doc. Report concisely, new expenses as separate line items.

### Standing decisions (apply without asking)
1. Card-ending variations (4251 vs 9873 etc.) are normal. Never flag them, including Apple Pay or Google Pay on the company card.
2. Receipts Hamza sends directly are logged, not held for confirmation, even with no text or an ambiguous vendor. Flag VAT or data issues in Remarks but log the row.
3. **EVERY expense is a business expense (decided 5 Oct 2026).** Do not flag "no business purpose", "looks personal" or director's-loan/BIK. This retires the old travel/parking no-purpose cluster flag (rows 9, 10, 17, 27, 28, 37, 38, 40, 55, 57, 69, 70) and the personal-rent flags (rows 7, 63). Older Remarks still contain that wording; Hamza was offered a one-pass cleanup of the Remarks column (recommended, since the accountant will read it).
4. Still flag non-purpose issues: VAT treatment uncertainty, missing/unreadable receipts, duplicates, unverified vendor VAT registration, donation tax treatment (BMCA-Charity row 51), real data errors.
5. When a receipt prints an explicit VAT rate or amount, use it (VAT-Yes) rather than the vendor default. Split-rate baskets (Lidl rows 31, 66): use the printed VAT figure, and ignore the W-column "Check VAT amount" flag.
6. No prior row and nothing printed: default VAT-No, remark "not independently verified".
7. Tesco defaults to VAT-No (mostly zero-rated grocery), with a stronger note when a basket is mostly standard-rated (toothbrush row 59, crisps/tissues rows 45/46/53/67).
8. Train/bus tickets: VAT-No (zero-rated passenger transport).
9. Receipts dated outside a tracker's own period are not logged in it.
10. An invoice or notice announcing a future Direct Debit is NOT logged until the charge is confirmed settled. A declined provisional booking with no prepayment is not logged.
11. Direct Debit payments are logged against the debit-clear date (e.g. DHL row 62, Toyota row 15).
12. Wholesale stock purchase/sale invoices (Mobile One, WavePhone, etc.) are a different category, NOT logged in this tracker.
13. V18's 5 unconfirmed items stay unlogged unless Hamza says so: Pizza Passions £10.49, B&M Cityside £9.22, ABN Invest INV-0004 £200, Invoice2go Aug renewal, B&Q £6.62 (30.08.26, deliberately not logged).
14. Bank statement is authoritative.

### Known failure modes (important for automation)
- **Wahidullah types rows directly into the Excel file**, producing half-finished rows (Amount as text with a "£", no Remarks, no helpers, ranges not extended). Happened 10+ times. Expect it every visit; always sweep the full range and complete in place.
- **PC-side writes silently fail to sync to OneDrive** (seen 15th update, 17th update, and 1 to 4 Oct: rows 64 to 67 never reached the cloud copy; later the PC copy turned out to be correct and it was cloud lag). Commits via the device bridge sometimes revert on first attempt; always re-stage and re-read, retry with force if needed.
- Excel open on the PC blocks staging ("open_in_another_app") and can cause conflict copies. Ask Hamza to close it before edits.
- `device_stage_files` can fail "file is hardlinked" right after a commit (OneDrive placeholder). Check mtime and size via list_dir, retry.
- Zapier hit "task limit reached for the current billing period" on 4 Oct, so cloud writes via Zapier were blocked.
- Device folder access is session-scoped. Unattended scheduled runs cannot self-grant it (5 Oct run could not check folders at all). The VAT RETURNS folder must already be connected, or use a cloud path.
- Gmail connector cannot read attachments; Zapier cannot read receipt PDF/image content either. Receipt contents come from Hamza sending the file, a device-linked read, or (long term) Xero OCR.
- No Microsoft 365 work account exists (OneDrive is personal), so the Claude M365 connector cannot be used.

### Access methods tried
1. Device bridge (`mcp__remote-devices__*`): stage, edit with openpyxl, commit, re-stage and verify. Works, but needs PC on, folder granted, and has the sync issues above. No `device_bash`, no delete capability.
2. Zapier OneDrive (personal account, connected 1 Oct): Microsoft Graph via `onedrive_make_api_get_request` (reads) and `onedrive_make_api_mutating_request` (writes). Proven: list folders, rename/move files, read cell ranges, insert rows (`POST .../range(address='62:63')/insert` body `{"shift":"Down"}`), PATCH formulas/values. Workbook base: `https://graph.microsoft.com/v1.0/me/drive/root:/Desktop/VAT RETURNS/VAT Return-SEPT-DEC/VAT Return From Sept-Dec, 2026.xlsx:/workbook`. Receipts folder item ID `D5AA8630B2ED2032!s7741549e63bf4460991c10fec413399e`. Avoid backslashes in JSON Remarks text. Limited by Zapier task quota.
3. Xero connector (Fonenova Ltd): read-only here. 32 bills, all Mobile One, none of the day-to-day expenses.

## 4. Current state (as of 5 Oct 2026, ~16:10 UTC)

Sept-Dec tracker, verified by re-read after commit (mtime 1791216524254, 80,267 bytes):
- Data through **row 70**. Total row 71 `=SUM(I5:I70)`, Net Total row 72 `=I71-SUM(Q5:Q70)`, all 8 Sheet1 SUMIFS end at `$70`.
- **Totals: £8,951.59 gross / £423.06 VAT / £8,528.53 net.**
- Receipts roots of both trackers are clean (vendor folders only, no loose files). V18 unchanged at 313 rows.

Recent rows (all logged with Remarks, helpers, ranges):

| Row | Date | Vendor | Amount | VAT |
|---|---|---|---|---|
| 62 | 16.09.26 | DHL Express (DD advice, inv BFSR011237115) | £93.84 | No |
| 63 | 01.10.26 | Property People Belfast Ltd (Oct rent, 148 Cliftonpark Ave) | £775.00 | No |
| 64 | 01.10.26 | Tesco Express | £21.28 | No |
| 65 | 02.10.26 | Tesla Motors Limited (Supercharger) | £30.93 | Yes, £5.16 |
| 66 | 02.10.26 | Lidl (split-rate) | £60.74 | Yes, £5.22 |
| 67 | 02.10.26 | Tesco Express | £3.39 | No |
| 68 | 04.10.26 | Tesco Express | £6.00 | No |
| 69 | 05.10.26 | Greater Anglia (Stansted Express) ref GCFL19R9, travel 8 Oct | £37.00 | No |
| 70 | 05.10.26 | Translink Airport Express 300, TRN-1947958848, 8 and 12 Oct | £13.50 | No |

Earlier history (rows 1 to 61) is summarised in the project handoff doc; notable rows: 7 flat rent £775.20 (Sept), 15 Toyota Financial Services £424.65, 16/26/50/65 Tesla charges, 18 Invisalign £198 (company card confirmed), 29 HQ-IWG office card payment, 51 BMCA-Charity £50 donation (settled), 52 Erbil Restaurant (no VAT number printed), 54 Lebara, 55 Parkdeck Chairs, 58 Flipdish/Sheesh Grill £12.50, 59 Tesco toothbrush £3.35 (should be VAT-Standard, accountant to reclassify), 60 Tesco sushi £5.20, 61 Lime £3.31 VAT £0.55.

## 5. Open items (watch list)

- **7 Nov 2026: VAT return due.** Proactively surface final reconciliation as it approaches.
- HQ-IWG invoice #7920-756, £2,160 (£1,800 + £360 VAT), due 15 Oct, Nov office period. Log once a card-transaction confirmation arrives (same pattern as row 29).
- DHL Express invoice BFSR011352661, £30.43, dated 28.09.26, DD due about 12 Oct. Log against the actual debit date once collected. Question for Hamza: stock freight (wholesale category) or general business shipping?
- Xero (UK) Ltd £84.00 subscription: only the 28 Sept forward-notice seen. Check Revolut statement, log once settled.
- Google Workspace Business Starter: billing details added 4 Oct, no charge seen yet.
- Regus Signature Campus Canary Wharf booking 173655735, National Car Parks account: no charge/receipt yet.
- Revolut KYC "we need more information" request (30 Sept) and a team-member invite authorisation (2 Oct).
- EORI go-live date pending (REQ0487686). HMRC digital support QUQD-9785-BXOK open.
- Retire/clean old "no business purpose" and personal-rent wording in Remarks (offered 5 Oct).
- Clutter to delete (Claude cannot delete): the 12 old wrongly-named originals listed in the handoff (21st update), `Chingford-Mount-Dental\Desktop - OneDrive.url`, the ~40-file saved-webpage folder under `EsyJet-Flights`, the new Translink `.html` saved page plus `_files` folder (replace with a PDF), 3 zero-byte files (2 in Gas-Electricity-Top Ups, 1 EsyJet WhatsApp image).
- `finalHMRCdraft\` folder missing; Q1 2026 tracker never reviewed; V18 `a1` folder has duplicates/junk.
- Hamza's lines to confirm: whether Mobile One invoicing (Dutch reverse-charge) fits the margin-scheme resale model needs professional VAT review; MTIC (carousel fraud) due diligence on counterparties; BMCA donation tax treatment with the accountant; vehicle ownership for the Toyota finance and 4 Tesla charges.

## 6. Advice for moving this to Claude Code

1. **Fix the data layer first, it is the root cause of most pain.** The recurring failures are Excel being hand-edited by a second person, OneDrive sync lag, and PC-must-be-on. Best option: run Claude Code ON the fonenova PC, with the OneDrive folder as the working directory. Then it reads and writes the xlsx and files directly (no stage/commit, no connector sessions, no Zapier quota). Ask Hamza to close Excel before runs.
2. **Replace the Excel formula-maintenance chore with a script.** Write one Python module (openpyxl) with `add_row(date, vendor, desc, amount, ref, vat_flag, vat_amount, remarks)` that finds the Total row by scanning column D, inserts above it, copies styles and helper formulas, rewrites Total/Net Total, and extends all 8 Sheet1 SUMIFS ranges (I, Q, U). Add `audit()` that checks every row for numeric Amount, Remarks, U/V/W helpers, range coverage, and a matching file in the receipts tree. This codifies the standing rules and removes the "half-finished row" class of errors. Keep a git repo for the scripts and a copy of the xlsx per run for rollback (openpyxl can drop some Excel features; diff before and after on first use).
3. **Make the single source of truth a plain CSV or SQLite log, with the xlsx generated from it.** Wahidullah typing into Excel will keep breaking things. Either lock the live tracker (read-only for him, he sends receipts via WhatsApp/email/Xero app instead) or add an audit step that detects hand edits.
4. **Receipt capture: the big win is Xero.** Decided 2 Sept, never completed. Ranked options: (1) Xero receipt capture app plus Revolut bank feed (already connected) with default expense categories and VAT rates matching the sheet, readable via the Xero API; (2) a Claude Code ingest script that reads new files in a drop folder, extracts text (pdfplumber, OCR with Tesseract or a vision call for photos), proposes the row, and files it. I would pick (1) for day-to-day plus (2) as a bridge for the VAT return period. Do not build a custom OCR pipeline as the long-term answer.
5. **Gmail receipts:** use the Gmail API directly (a script with a saved token) rather than the connector. It can download attachments, which the connector cannot. Search `newer_than:2d (receipt OR invoice OR order OR confirmation OR "payment")`, save PDF attachments to a drop folder, then run ingest. Exclude wholesale (Mobile One, WavePhone, Phone-Zone) senders.
6. **Scheduling:** cloud scheduled tasks cannot self-grant device folder access, so a run at 22:00 UTC that needs the PC folder will fail unattended. Run the scheduled job locally on the PC (Windows Task Scheduler calling Claude Code headless, or a Claude Code scheduled task) so the folder is always reachable. Send a push or email only when something needs him.
7. **Verification:** after any write, re-open the saved file and assert row count, Total formula, Sheet1 ranges and the expected totals. Re-run the audit. Do not trust a "success" message from a sync layer.
8. **Add a VAT-return pack generator before 7 Nov:** totals by month, VAT reclaimable list (rows with VAT-Yes), exceptions list (rows with VAT-Yes and W flag, no-VAT-number vendors, rows needing accountant input), and a receipt-completeness report. Hand that to the accountant.
9. **Risks to keep in front of Hamza (honest read):** the VAT-No default on mixed Tesco baskets understates reclaimable VAT (small, but it adds up); personal rent and flat deposit paid from the company account will draw accountant and HMRC attention regardless of the "all business" rule, so get written accountant sign-off on director's-loan or BIK treatment; the VAT number's recent cancellation and reinstatement means the 7 Nov return should be reviewed by the accountant, not just filed from the sheet; 12+ travel rows with no stated purpose are fine to log but the underlying trip purpose should be recorded somewhere in case of an enquiry.
10. **Project docs to bring over:** copy `claude/expenses-chat-handoff.md` (full row-by-row history) and `claude/expense-tracking-role-and-context.md` from the claude.ai Expenses project into the repo as `docs/`. This file is the condensed version; the handoff holds per-row Remarks rationale. Keep a `CLAUDE.md` in the repo root with sections 1, 3 and the standing decisions above.

## 7. Memory entries on file (verbatim categories, for completeness)

- Profile: Hamza Ismati, runs Fone Nova, Belfast; Claude Pro since Aug 2026.
- Preferences: separate line items for payments, no em dashes, direct/concise, name a preferred option.
- Bookkeeping rule on file: every expense paid on the company card is treated as a business expense; VAT determined from receipts. Expense standing rule on file (5 Oct): every expense is a business expense, log all receipts as ordinary business expenses.
- Project memory: Zapier cloud access to OneDrive set up 1 Oct as fonenovaltd@gmail.com (personal), details in `claude_zapier-cloud-access-update.md`.
- Topic files also exist for travel, education, and recent side explorations (clothing brand idea, FreeLLMAPI for Claude Code); not relevant to expense tracking.
