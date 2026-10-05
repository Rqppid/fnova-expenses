# Fone Nova expenses: Phase 1 report + Phase 2 build plan

## Context
Taking over expense tracking from Cowork. Goal: replace the fragile connector/manual Excel upkeep with local Python tooling on this PC (add_row, audit, file_receipt, verify), then an unattended daily routine, then a VAT return pack before 7 Nov 2026. Phase 1 was read-only; nothing has been written to the trackers, receipts or any repo yet.

---

## Phase 1 report (read-only, 5 Oct 2026)

### Current state: Sept-Dec tracker matches section 4 exactly
- File 80,267 bytes, mtime 16:08:44 UTC 5 Oct (matches handoff).
- Data rows 5 to 70. Total row 71 `=SUM(I5:I70)`, Net Total row 72 `=I71-SUM(Q5:Q70)`.
- All 8 Sheet1 SUMIFS (B5:C8) end at `$70`; B9:D9 are SUMs of those.
- Recomputed: **8,951.59 gross / 423.06 VAT / 8,528.53 net**. Sept 8,003.75 / 412.68; Oct 947.84 / 10.38.
- Every row 5 to 70: numeric Amount, `Receipt:Yes`, valid DD.MM.YY date, U/V/W helpers exactly as specified.
- Last saved by **openpyxl 3.1.5**, not Excel: inline strings, no calcChain, `fullCalcOnLoad=1`, so no cached values. Features present: 4+2 merged ranges, 1 data validation on Sheet2, page setup. A future openpyxl write is therefore low-risk (diff still planned).

### V18 (May to Sept)
- Saved by Excel Online. Data rows 5 to 313, Total 314, Net 315. Totals **34,370.55 gross / 1,911.59 VAT / 32,458.96 net**; cached Sheet1 values agree.

### Discrepancies found (not fixed)
**Sept-Dec tracker**
1. **Probable double count across trackers: Tesco Express 01.09.26 £5.50** is both V18 row 313 and Sept-Dec row 5. Both trackers feed the same 7 Nov return, so it is counted twice. Sept-Dec row 5 is also the only row with **no Remarks**.
2. **Row 29 HQ-IWG £2,160 / £360 VAT (Inv 7920-712) is backed only by `HQ-IWG-Service-15.09.26.txt`**, a transcription, not a VAT invoice. It is the largest reclaim in the tracker. HMRC needs the actual invoice for input VAT. Get the PDF from IWG.
3. Other rows backed only by transcriptions or saved pages: Anthropic row 24 (.txt, £3.00 VAT), Beryl rows 19, 25 and 30 (.txt, £0.92 VAT total), Translink row 70 (.html plus `_files`).
4. W column will show "Check VAT amount" on 5 rows: 31 and 66 (Lidl split-rate, expected), **8 and 47** (SPAR energy top-ups, £0.16 and £0.30 VAT on about £51; the 5% domestic fuel rate would give about £2.43), **38** (JustPark £0.08 on £4.10, probably VAT on the booking fee only). Rows 8, 47 and 38 need the accountant's eye.
5. Out of date order: rows 61 (26.09) and 62 (16.09) sit after 30.09 rows. Cosmetic, since SUMIFS keys on the U date.
6. Row 42 Wahidullah wage £3,009.80 (and V18 WAGES-PAID rows) also sit in Xero payroll. No VAT effect, but there is a risk of double-counting in the accounts. Tell the accountant.

**Sept-Dec receipts tree** (root is clean: vendor folders only)
- Every row 5 to 70 has a matching file. Files with no row: DHL 28.09.26 £30.43 and HQ-IWG 7920-756 £2,160 (both open items, correctly unlogged); Flat-Rent 03.08.26 invoice/transfer (August, V18 period, not this tracker).
- 17 exact-duplicate copies: the 12 known old originals, plus 5 `Scan from ...` leftovers in Boots, Parkdeck-Chairs, Restaurant-Takeaway, Stansted Express and Tesco (29.09).
- Junk: 3 zero-byte files (2 in Gas-Electricity-Top Ups, 1 EasyJet WhatsApp image); `Desktop - OneDrive.url` (61 KB); 58-file EasyJet saved-page folder; 14-file Translink `_files` folder.
- Naming variants (left as-is per convention): Tesco Express-23.09.26, Tesco Store-26.09.26, Tesla Charge-25.09.26, Happy Yemen-Restuarant, Erbil Restaurant & Cafe, FALLONE'S-Pizza (Fallone's row 21 also has a second, different-size file in Restaurant-Takeaway). EasyJet row 9 has no `EasyJet-03.09.26` file, only a boarding pass and a WhatsApp image.

**V18**
- **The receipts root is NOT clean**, contrary to the handoff: `revatinvoices.zip` (58 KB, 9 May) and an older `VATReturn_Automated_v18_delivered.xlsx` (64 KB, 4 Sept) are loose there. They are not receipts. Leave or move to an archive folder.
- **3 half-finished rows with no Amount: 214, 221 and 234 (club24, 07.08, 10.08, 13.08).** Club24 files exist for 26.07, 11.08 and 14.08 (£2.50-ish fitness charges). These are likely Wahidullah-typed and dated by debit, not receipt.
- 21 rows have no Remarks (101, 115, 145, 153, 166, 171, 214, 221, 233, 234, 246, 271, 273, 288, 291, 293 to 295, 297 to 301, 313). Rows 20 and 21 use the date `16.5.26` (parses OK).
- File-to-row by date: 35 files have no row on their filename date, and 30 row-dates have no file. This is mostly naming noise (`10-06-2026 21.26`, debit date vs receipt date). Worth a look: HQ invoices 7920-592 (01.06) and 7920-561 (11.06) against a single June HQ row (r82, 20.06, £2,160), so possibly one IWG payment is unlogged. A proper match needs amount-aware audit() (Phase 2). The `a1` folder (176 files, 3 zero-byte) was excluded as known junk.
- Per the V18 convention, flag only, no writes.

### Environment blockers
- **Python is not installed** (only the Microsoft Store stub). git 2.55 and winget are available.
- Gmail MCP connector failed to connect this session. This is irrelevant for Phase 3, which uses the Gmail API directly.

---

## Phase 2 plan (after approval)

### Step 0: Safety first
1. Timestamped backups of both trackers to `VAT RETURNS\_backups\2026-10-05_HHMMSS\` (OneDrive-synced, so the copies also exist off-machine). Copy, verify SHA-256 matches the source.
2. Install Python 3.12 user-scope: `winget install -e --id Python.Python.3.12 --scope user`. Create a venv with openpyxl, pdfplumber, pytest (Gmail libs come in Phase 3).

### Step 1: Repo
- **Repo at `C:\Users\fonen\fonenova-expenses\`, outside OneDrive.** A `.git` folder inside a OneDrive-synced folder gets corrupted by placeholder/sync behaviour, which is the same failure class that bit Cowork. The trackers stay where they are; `config.toml` points at `VAT RETURNS`. Claude Code sessions start in the repo and read and write the VAT RETURNS paths directly.
- `CLAUDE.md` = context sections 1 and 3 plus the standing decisions and the user's working rules. `docs/context.md` = full context file. `docs/handoff.md` = expenses-chat-handoff.md. `docs/run-log.md` (append-only).

### Step 2: Modules (`fonenova/`)
- `layout.py`: one `Layout` per tracker (Sept-Dec helpers U/V/W; V18 helpers AB/AC/AD, Total/Net in both I and Q). Path, sheet names, first data row 5.
- `tracker.py`
  - `find_total_row(ws)`: scan column D for `Total :`. Net Total must be the next row, else raise.
  - `add_row(path, date, vendor, desc, amount, ref, vat_flag, vat_amount, remarks)`: **avoids `ws.insert_rows`**, because openpyxl does not shift formulas, validations or merges. Instead it writes the new data row at the current Total row index and rewrites Total and Net Total one row lower. It copies cell styles and row height from the last data row and from the old Total/Net rows, writes U/V/W from formula templates, extends any data-validation `sqref` that covers column ranges, and regex-rewrites the 8 Sheet1 SUMIFS (`Sheet2!$I$5:$I$n`, `$Q`, `$U`). It asserts exactly 8 were changed. Refuses if a `~$` Excel lock file exists (Excel open). Backup before, verify after, all in one call.
  - `complete_row(path, r, ...)`: fix a half-finished row in place ("£12.50" text to 12.5, add helpers, Remarks). Explicit call only.
- `verify.py`, `verify(path, expected_last_row, expected_gross, expected_vat)`: re-open from disk, check Total and Net Total positions and formulas, every row's helpers, all 8 SUMIFS end at the last row, and totals recomputed in Python (no cached values exist). Also re-checks file size and SHA-256 changed, against OneDrive silent revert.
- `audit.py`: repeatable Phase 1 report (markdown) for both trackers. Rows: numeric amount, Remarks, helpers, date format, VAT-Yes has Q, W-flag prediction, range coverage, cross-tracker duplicates (date + amount). Files: index both receipt trees with SHA-256. Match rows to files by filename cited in Remarks, then by vendor token + date, then by date + amount. Report orphan files, rows without files, exact duplicates, zero-byte files, loose roots and transcription-only evidence (.txt/.html).
- `filing.py`, `file_receipt(src, vendor, date, tracker, descriptor=None)`: build `Vendor-DD.MM.YY.ext` (descriptor inserted for same-day clashes), create the vendor folder if new, `os.replace` (move, same volume). Refuse to overwrite. If the target already exists with an identical hash, report a duplicate and leave the source alone. Never deletes.
- `xlsx_diff.py`: unzip before and after, compare the part list, per-sheet merges, data validations, conditional formats, column widths, page setup, defined names, style count and every cell value/formula. Prints a feature-loss report.
- `cli.py`: `audit`, `add`, `complete`, `file`, `verify`, `backup`, `diff` subcommands.

### Step 3: Tests (`tests/`, pytest, always on a temp copy of the backup, never the live file)
- add_row: totals rise by the amount, Total/Net shift by one, helpers correct, 8 SUMIFS extended, validation extended, works when Total isn't at row 71.
- verify catches a missing helper, a short SUMIFS range, a text amount.
- audit flags: a synthetic half-finished row, the known row 5 Remarks gap, the cross-tracker £5.50 duplicate.
- file_receipt: naming, new-folder creation, no overwrite, duplicate detection, the source is gone after a move.
- V18 layout reads 313 rows and 34,370.55 / 1,911.59.

### Step 4: First write and diff
1. Run add_row on a **temp copy** of the live file, then xlsx_diff it against the original. Report any lost feature.
2. First live write, only with approval: resolve discrepancy 1 (see below). Run diff + verify + audit.

### Default decisions (I will apply these unless you say otherwise)
- **£5.50 duplicate: delete Sept-Dec row 5** (no Remarks, likely hand-typed; V18's row predates it). Totals become 8,946.09 / 423.06 / 8,523.03. This needs a `delete_row` mirror of add_row. Backup first.
- Don't touch V18 (flag-only). Report the club24 rows to you.
- Delete nothing. A cleanup list (17 duplicates, 3 zero-byte files, 2 saved-page folders, the .url) comes back to you for a yes.

### What you need to do yourself (lead time, start now)
1. Get the PDF of HQ-IWG invoice 7920-712 (Sept, £360 VAT) from the IWG portal.
2. For Phase 3: create a Google Cloud project, enable the Gmail API, set the OAuth consent screen to "Testing" with fonenovaltd@gmail.com as a test user, create a Desktop OAuth client, and save `credentials.json` into the repo's `secrets\` folder (git-ignored). You then do one browser sign-in when I first run it.
3. Close Excel before any run that writes.

## Verification
- `pytest` green.
- `python -m fonenova.cli audit` reproduces the Phase 1 findings above.
- After the first live write: verify() passes and xlsx_diff shows no feature loss. You open the file in Excel once to confirm the totals display 8,946.09 / 423.06 / 8,523.03 and Sheet1 Sept = 7,998.25.
