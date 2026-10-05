# Fonenova Ltd VAT Return, Handoff (rolling changelog, exported 5 Oct 2026)

Source: claude.ai "Expenses" project, `claude/expenses-chat-handoff.md` (last edited 2 Oct, 21st update), plus the later addenda `daily-check-3oct-run.md`, `daily-check-4oct-run.md`, `daily-check-4oct-evening-run.md`, `daily-check-5oct-run.md`, `claude_zapier-cloud-access-update.md` and `standing-decision-all-expenses-business.md`. Newest information first. The "Addenda after the 21st update" section at the top supersedes anything older that conflicts.

Note: standing decision of 5 Oct 2026: EVERY expense is a business expense. Do not flag "no business purpose", personal use, or director's-loan/BIK. Old Remarks text and flags below that mention these are historical.

---

## Addenda after the 21st update (3 to 5 Oct)

### 5 Oct 2026 (three runs)
- Run 1 (scheduled 10:25 UTC): VAT RETURNS folder not connected, nothing logged.
- Run 2 and 3 (user present, folder connected ~16:08 UTC): two emailed receipts logged.
- **Row 69: Greater Anglia (Stansted Express), 05.10.26, £37.00, VAT-No.** Advance Return Stansted Airport to Tottenham Hale, travel 08.10.26, card ending 9873, ref GCFL19R9. Email states no VAT on train tickets. Receipt already filed by user as `Stansted Express Train-Bus Service\Stansted Express Tickets-05.10.26.pdf`.
- **Row 70: Translink (Ulsterbus), 05.10.26, £13.50, VAT-No** (VAT not stated, passenger transport). Airport Express 300 return, 08.10.26 17:48 out, 12.10.26 22:20 back, order TRN-1947958848. Receipt filed by user as `Translink Bus-B Int Airport\Translink Bus Return Tickets to Belfast Int Airport-05.10.26.html` (saved web page plus `_files` folder; should be replaced with a PDF).
- Total now row 71 `=SUM(I5:I70)`, Net Total row 72 `=I71-SUM(Q5:Q70)`, all 8 Sheet1 SUMIFS end at `$70`. Committed once, re-staged, content re-read, persisted (mtime 1791216524254, 80,267 bytes).
- **Totals: £8,951.59 gross / £423.06 VAT / £8,528.53 net.**
- Receipts roots of both trackers: vendor folders only, no loose files. V18 unchanged (mtime 1790438395000, 313 rows).
- Gmail informational: HMRC EORI team confirmed GB516452304000 and XI516452304000 both being reinstated, no new numbers, go-live date pending (REQ0487686). HMRC digital support QUQD-9785-BXOK still investigating the online EORI error. WavePhone and Mobile One Trade replied confirming VIES impact; Mobile One revised wholesale invoice and WavePhone revised invoice 2026042 (wholesale, not logged). Google Workspace Business Starter billing set up 4 Oct (no charge seen yet).
- Only rows 60 to 70 and Sheet1 ranges were inspected this run, not every older row.

### 4 Oct evening (device re-run)
- The PC copy of the tracker already had rows 64 to 67 (the earlier "cloud missing rows" finding was OneDrive cloud lag). Rows 64 to 67 verified with Remarks, U/V/W helpers, SUMIFS to $67.
- **Row 68: Tesco Express, 04.10.26, £6.00, VAT-No.** Belfast University Rd Express, 19:24, Store 4453, Checkout 209, Mastercard Debit ...4251, Auth 095299, barcode 3IWE-1BZ4-105E-U7EE. Subtotal 8.85 less savings 2.85. Zero-rated food basket. Loose scan `Scan from 2026-10-04 07_40_31 PM.pdf` filed as `Tesco\Tesco-04.10.26.pdf`.
- Totals then: £8,901.09 gross / £423.06 VAT / £8,478.03 net.

### 4 Oct (scheduled, 14:09 UTC, via Zapier cloud access)
- The cloud copy of the Sept-Dec tracker was missing rows 64 to 67 (PC-side writes had not synced; later found to be cloud lag). Zapier returned "task limit reached for the current billing period" on the first write, so no cloud writes were made.
- Expected totals once rows 64 to 67 present: £8,895.09 / £423.06 / £8,472.03.

### 3 Oct
- **Row 67: Tesco Express, 02.10.26, £3.39, VAT-No.** Found as loose scan `Scan from 2026-10-02 07_28_30 PM.pdf`. Belfast University Rd Express, 02/10/2026 19:23, Store 4453, Checkout 209, Mastercard Debit ...4251, barcode 3IWE-1BZ4-105E-NDNK. Nutella donut 2-pack, cheese twist, Walkers crisps; £6.60 less £3.21 promotions and £0.50 price reduction, total £3.39. VAT-No per Tesco default but items likely standard-rated (VAT understated by up to about £0.56, same caveat as rows 45/46/53). Filed as `Tesco\Tesco-02.10.26.pdf`.
- Totals then £8,895.09 / £423.06 / £8,472.03. EORI reinstatement escalated by HMRC as REQ0487686 (2 Oct); Wahidullah sent the email-risk confirmation 2 Oct 19:13.

### 1 Oct, Zapier cloud access set up (see section "Access methods" below)
- Zapier OneDrive app connected as fonenovaltd@gmail.com (personal Microsoft account). Proven to list folders, rename/move files, read cell ranges, insert rows and PATCH formulas via Microsoft Graph. Cannot read receipt PDF/image content.
- The 17th update's PC-side write (rows 62 and 63) had NOT reached the cloud and was redone: row 62 DHL Express 16.09.26 £93.84 VAT-No; row 63 Property People Belfast Ltd 01.10.26 £775.00 VAT-No; row 61 Remarks updated to "company card via Apple Pay, confirmed by Hamza 30.09.26".
- Totals then: £8,778.75 / £412.68 / £8,366.07 (Sept £8,003.75, Oct £775.00).

---

## 2 Oct (21st update): file-naming sweep, 12 files fixed, no tracker changes
Recursive listing of the whole Sept-Dec receipts tree (~90 files) checked against `Vendor-DD.MM.YY.ext`. Most folders conformed. 12 files were copied under correct names and verified by size match after a fresh `device_list_dir`:
- `BMCA-Charity\Transaction-Statement-25.09.26.pdf` to `BMCA-Charity-25.09.26.pdf` (row 51, £50).
- `DHL-Express\GB09_1005227269_FoneNova Ltd_Payment advice.PDF` to `DHL-Express-16.09.26-PaymentAdvice.pdf` (row 62, £93.84).
- `DHL-Express\DHL-Express-BFSR011352661.pdf` to `DHL-Express-28.09.26-Invoice-BFSR011352661.pdf` (not yet logged, £30.43).
- `Tesco\Tesco Express-20.09.2026.jpeg` to `Tesco-20.09.26.jpeg` (row 44, £9.70).
- `Flat Deposit+Rents\TransferConfirmation-Flat Rent-01.09.26.pdf` to `Flat-Rent-01.09.26-TransferConfirmation.pdf` (row 7).
- `Flat Deposit+Rents\Flat Rent-Invoice-PP23400-20261001-01.10.26.pdf` to `Flat-Rent-01.10.26-Invoice-PP23400.pdf` (row 63).
- `Flat Deposit+Rents\TransferConfirmation-Flat Rent-01.10.26.pdf` to `Flat-Rent-01.10.26-TransferConfirmation.pdf` (row 63).
- `Flat Deposit+Rents\Invoice-PP22862-20260803.pdf` to `Flat-Rent-03.08.26-Invoice-PP22862.pdf` (Aug, predates this tracker).
- `Flat Deposit+Rents\RENT+DEPOSIT- TransferConfirmation (03-08-26).pdf` to `Flat-Rent-03.08.26-TransferConfirmation.pdf`.
- `Flat Deposit+Rents\Payment received.msg` to `Flat-Rent-01.10.26-PaymentReceived.msg` (PayProp/Property People confirmation "we received 775.00 for Cliftonpark Avenue, 148, 2 on 01 Oct '26"; supplementary to row 63).
- `HQ-IWG-Service\HQ-Invoice_#7920-756-01.10.26.pdf` to `HQ-IWG-Service-01.10.26-Invoice-7920-756.pdf` (not yet logged, £2,160).
- `Tesla\Tesla EV Charge-2026-09-16 at 15.25.00.jpeg` to `Tesla-16.09.26-EVCharge.jpeg` (row 26, £12.42).

The 12 old wrongly named originals still sit alongside the new ones (no delete capability). Names to delete, one per folder above: `Transaction-Statement-25.09.26.pdf`, `GB09_1005227269_FoneNova Ltd_Payment advice.PDF`, `DHL-Express-BFSR011352661.pdf`, `Tesco Express-20.09.2026.jpeg`, `TransferConfirmation-Flat Rent-01.09.26.pdf`, `Flat Rent-Invoice-PP23400-20261001-01.10.26.pdf`, `TransferConfirmation-Flat Rent-01.10.26.pdf`, `Invoice-PP22862-20260803.pdf`, `RENT+DEPOSIT- TransferConfirmation (03-08-26).pdf`, `Payment received.msg`, `HQ-Invoice_#7920-756-01.10.26.pdf`, `Tesla EV Charge-2026-09-16 at 15.25.00.jpeg`.

Non-receipt clutter to delete: `Chingford-Mount-Dental\Desktop - OneDrive.url`; the ~40-file saved-webpage folder `EsyJet-Flights\easyJet booking reference_ KD9GKD2 - fonenovaltd@gmail.com - Gmail_files\`.

Left as-is (minor stylistic variants with vendor and date): `Tesco Express-23.09.26.jpeg`, `Tesco Store-26.09.26.jpeg`, `Istanbul Market-06.09.26.pdf` vs `Istanbul-Market-16.09.26.pdf`, `Asda-BathSheets-16.09.26.pdf`, `Asda-Dehumidifier-16.09.26.pdf`, `Beryl-13.09.26-evening.txt`, the two `Belfast Int Airpor(t) Parking-28262339-1_...-03.09.26.pdf` files, and the copy-not-move leftovers in Boots, Parkdeck-Chairs, Stansted Express, Tesco, Restaurant-Takeaway.

## 2 Oct (20th update): row 66 Lidl £60.74, VAT-Yes £5.22
Loose scan `Scan from 2026-10-02 03_39_29 PM.pdf`. Lidl Boucher Rd, Belfast (GB304775894), 02/10/2026 14:44:07, Mastercard ...9873, Auth 662516, TRN-ID NI041903121619275261. Receipt prints a two-band VAT summary: A 0%-rate gross £29.44 (VAT £0.00), C 20%-rate gross £31.30 (VAT £5.22), same as row 31. Column W will show "Check VAT amount" because the auto-calc assumes the whole gross is VAT-inclusive at 20%; the £5.22 in Q is correct, ignore the W flag. Filed as `Lidl-02.10.26.pdf`. Totals then £8,891.70 / £423.06 / £8,468.64. Commit silently reverted on first attempt, forced retry persisted. User deleted the 3 loose root files afterwards.

## 2 Oct (19th update): row 65 Tesla Motors Limited £30.93, VAT-Yes £5.16
Tesla Motors Limited, 109 Devonshire Road, London W4 2AN, Tax ID GB782418216, receipt CRGB0000486372, 02/10/2026 14:10:29, Charging Location Boucher Rd 8-8a Belfast BT12 6HR, 47.589 kWh at 0.65 GBP/kWh, card ending 9873. VAT £5.16 printed. Filed as `Tesla-02.10.26.png`. Commit silently reverted first attempt; forced retry fixed. Same sweep showed the two root files (`20260930_110832210_iOS.pdf`, `Scan from 2026-09-30 03_26_09 PM.pdf`) were duplicates of rows 61 and 60.

## 1 Oct (18th update): row 64 Tesco Express £21.28, VAT-No
Photo sent in chat. Belfast University Rd Express, VAT No. GB220430231, 01/10/2026 17:07, Store 4453, Checkout 002, Mastercard Debit ...9873, Auth 614995. All fresh/zero-rated grocery basket. Filed `Tesco-01.10.26.png`.

## 1 Oct (17th update): VAT number reinstated; new EORI problem; rows 62 and 63
- Wahidullah's 1 Oct email to HMRC's EORI team states "My VAT No:516452304 has been recently reinstated." Not independently verified against an official HMRC letter. This lines up with the 30 Sept reply to Mobile One Trade ("Yes, I confirm") turning out accurate.
- Old EORI XI516452304000 was invalid; HMRC told Wahidullah to reapply; online application kept erroring; EORI team asked him to confirm the email-risk acceptance (done 2 Oct). Later (5 Oct) HMRC confirmed reinstatement of both GB and XI numbers.
- **Row 62: DHL Express, 16.09.26, £93.84, VAT-No.** Direct Debit payment advice for invoice BFSR011237115 (dated 24.08.26, V18 period); logged against the 16.09.26 debit-clear date (same convention as Toyota Finance row 15). Economy Select EU/doc service; DHL's other invoice prints Code Z (zero-rated). First DHL entry in this tracker: ask Hamza whether DHL is wholesale-stock freight (different category) or general business shipping.
- **Row 63: Property People Belfast Ltd, 01.10.26, £775.00, VAT-No.** October rent for 2, 148 Cliftonpark Ave, invoice PP23400, payment ref EGZ1317, paid via Revolut Business Faster Payment on 1 Oct. Same as row 7.
- Not logged, watch: HQ-IWG invoice #7920-756, £2,160 (£1,800 + £360 VAT), due 15 Oct, Nov office period, billed to card ending 9873, no payment confirmation seen. DHL invoice BFSR011352661, £30.43, dated 28.09.26, DD due about 12 Oct.
- Row 61 Remarks fixed (company card via Apple Pay). Account-name mismatch ("quay"/quayexec@gmail.com) still open, not blocking.

## 30 Sept (15th update): earlier writes never persisted; rows 58 to 61 fixed
On staging the tracker, mtime was 11:07:30 UTC, earlier than the 12th to 14th updates' receipt renames. Row 58 (Sheesh Grill/Flipdish £12.50) and 59 (Tesco toothbrush £3.35) lacked Remarks and U/W helpers; rows 60 (Tesco sushi £5.20) and 61 (Lime £3.31) were missing entirely. Likely a silent OneDrive sync revert. Fixed and re-verified: Total row 62, Net Total row 63, 8 SUMIFS to $61. Totals then £7,909.91 / £412.68 / £7,497.23. **Process change: compare the on-disk mtime against receipt rename timestamps at the start of each run.**
- Row 60: Tesco Express 30.09.26 £5.20 VAT-No (Oishii smoked salmon and prawn sushi 240g, auth 004385, barcode 3IWE-1BZ4-105E-H1Z0).
- Row 61: Lime Technology Limited 26.09.26 £3.31 VAT-Yes £0.55 (VAT 20% printed, doc GB-2026-09-0070897696, Apple Pay, tax ID GB306424039). Account name "quay"/quayexec@gmail.com. Paid on the company card via Apple Pay (confirmed 30 Sept).
- Row 58: Flipdish DineIn, 29.09.26, £12.50, VAT-No: 5 x Coca-Cola 330ml at £2.50, Mastercard ...4251, auth masked; venue later entered directly as "Sheesh Grill". Dine-in is normally standard-rated catering so VAT-No likely understates VAT. Filed `Restaurant-Takeaway\Flipdish-DineIn-29.09.26.pdf`.
- Row 59: Tesco Express 29.09.26 £3.35 VAT-No, single Colgate Max White toothbrush; toothbrushes are standard-rated, so reclassify to VAT-Standard at return time (VAT understated by £0.56).

## 30 Sept (12th and 13th updates): HMRC cancellation and VIES
- A wholesale partner (Mobile One Trade B.V.) checked Fonenova's VAT number on VIES on 30 Sept and found it invalid; reply "Yes, I confirm." was sent at 14:08.
- HMRC VAT cancellation case: via MP Claire Hanna's office (ref CE/4669015/2026). HMRC responded 28 Sept in a PDF attachment ("CE4669015 MCT.pdf") the Gmail connector could not read. By 1 Oct the number was reported reinstated.
- Revolut sent a "we need more information from you" KYC reminder (30 Sept 00:11).
- Folder access had to be re-requested for `OneDrive\Desktop\VAT RETURNS` each session.

## 29 Sept (11th update): row 57 Greater Anglia £22.00, 28.09.26
Tottenham Hale issuing office, 28/09/2026 18:36:36, card ending 4251, Merchant Id ****10551, Terminal xxxx1384, Auth 7A65H1. Row was found half-finished (typed directly by Wahidullah). Net Total formula had been missed. Filed `Greater-Anglia-28.09.26.pdf`. Totals then £7,885.55 / £412.13 / £7,473.42.

## 28 Sept (9th update): row 56 Tesco Express £14.09, VAT-No
Belfast University Rd Express, 28/09/2026 14:08, Store 4453, Checkout 003, Mastercard Debit ...9873, auth 151154. Subtotal £18.57 less £4.48 savings. Basket includes standard-rated items (Sprite Zero, sushi meal-deal item). Filed `Tesco-28.09.26.png`. Totals then £7,863.55 / £412.13 / £7,451.42.

## Rows 1 to 55 and 23 to 28 Sept history
Condensed in the original handoff to keep it readable. Not reproduced here. Notable rows: 7 flat rent £775.20 (Sept); 8 and 47 SPAR/energy top-ups; 9, 10, 17, 27, 28, 37, 38, 40 travel/parking; 13 and 36 Istanbul Market; 15 Toyota Financial Services £424.65 (Direct Debit); 16, 26, 50 Tesla charges; 18 Invisalign £198 (company card confirmed 27 Sept); 29 HQ-IWG card payment; 31 Lidl 16.09.26 (split-rate); 33, 44 to 46, 53 Tesco rows; 51 BMCA-Charity £50 donation (settled); 52 Erbil Restaurant & Cafe (no VAT number printed); 54 Lebara Voucher; 55 Parkdeck Chairs Ltd.

---

## VAT filing period (resolved 27 Sept 2026)
Q3+Q4 combined: May to October 2026 (6 months), filed as one return, due **7 November 2026**. V18 (May to Sept) plus the Sept-Dec tracker's Sept and Oct rows make up this return. Nov/Dec rows belong to the next return. Given the cancellation and reinstatement history, review with the accountant before filing.

## V18 (May to Sept working tracker), current state
Data through row 313 (last: Forest Service, 25.08.26), unchanged. 5 possible new/unlogged V18 expenses deliberately left unlogged: Pizza Passions £10.49, B&M Cityside £9.22, ABN Invest INV-0004 £200, Invoice2go Aug renewal, B&Q £6.62 (30.08.26 masonry nails, filed in `B&Q-30.08.26\` but not logged per the user's 27 Sept instruction). Only add if the user explicitly says so.

## Compliance and watch flags (numbering from the original handoff; items retired by the 5 Oct standing decision marked)
1. Personal rent from company account (row 7, row 63): RETIRED by 5 Oct decision; still worth accountant sign-off.
2. SPAR/energy top-ups (rows 8, 47): no address given.
3. Travel/parking cluster with no stated purpose (rows 9, 10, 17, 27, 28, 37, 38, 40, 55, 57, 69, 70): RETIRED as a flag by 5 Oct decision.
4. Istanbul Market Belfast (rows 13, 36): VAT treatment not independently verified.
5. Toyota Financial Services (row 15, £424.65): vehicle/business use unconfirmed.
6. Tesla Motors (rows 16, 26, 50, 65): vehicle use unconfirmed.
9 to 21. Forest Service car park, V18 unlogged items, Invoice2go renewal, Asda dehumidifier, Sainsbury's snacks, Deerah Lebanese Cafe, City Car Wash registration mismatch, Belfast Airport/car-wash/FX-fee pattern: open, unchanged.
22. Recurring half-finished-row pattern caused by Wahidullah typing directly. Keep doing full sweeps every visit.
23, 25. Tesco crisps/tissues rows (45, 46, 53): standard-rated items inside VAT-No baskets.
30. Wholesale iPhone-stock trading invoices (Gmail) are a different category, not logged here.
32. BMCA-Charity donation tax treatment still needs accountant input.
34. Erbil Restaurant & Cafe (row 52): no VAT number printed.
35, 36. Lebara (row 54), Parkdeck Chairs (row 55): purpose flags RETIRED by 5 Oct decision.
38. B&Q receipt deliberately not logged (see V18).
39. Xero (UK) Ltd £84.00: only the 28 Sept forward-notice seen. Check Revolut statement; log as a new row once settled.
40. Regus Signature Campus Canary Wharf, booking 173655735: no charge or receipt yet.
44. National Car Parks Limited account sign-up: no charge yet.
45. Row 58 (Sheesh Grill): dine-in, VAT-No likely understates VAT.
46. Row 59 (Tesco toothbrush): reclassify to VAT-Standard at return time.
47. HMRC VAT cancellation case: resolved by reinstatement per Wahidullah's 1 Oct email; confirm an official HMRC letter exists.
48. Revolut KYC "more information" request (30 Sept).
49. Lime row 61: only the "quay"/quayexec@gmail.com account-name point remains open.
50. VIES invalid number: largely resolved (reinstated).
51. Process risk: tracker writes silently failing to persist. Always re-read after commit.
52. HQ-IWG invoice #7920-756 £2,160 due 15 Oct, not yet confirmed paid.
53. DHL invoice BFSR011352661 £30.43, DD due about 12 Oct, not yet collected.
54. DHL category question (stock freight vs general shipping).
55. EORI: GB and XI reinstatement confirmed 5 Oct, go-live date pending.
57, 58. Row 65 and 66 commit reverts; Lidl row 66 W-column flag is to be ignored.

## Still broken or unreviewed
Two 0-byte files in `Gas-Electricity-Top Ups`; one 0-byte EsyJet WhatsApp image; `finalHMRCdraft\` folder missing; Q1 2026 tracker unreviewed; V18 `a1` duplicates/junk; 4 other V18 items flagged 14 Sept still not added.

## Access methods and known technical issues
- **Device bridge** (`mcp__remote-devices__*`): stage, edit, commit, re-stage and verify. No `device_bash`, no delete capability. `device_commit_files` requires the staged file under `/mnt/user-data/outputs/`. Folder access is session-scoped. Commits can silently revert on the first attempt (seen 19th and 20th updates): re-stage and re-read; retry with `force:true` if needed. `device_stage_files` can fail "file is hardlinked" right after a commit (OneDrive placeholder), retry after checking mtime and size. "open_in_another_app" means Excel has the file open. The device can disconnect mid-session with no warning.
- **Zapier OneDrive (cloud, set up 1 Oct)**: reads via `onedrive_make_api_get_request` (use `execute_zapier_read_action`), writes via `onedrive_make_api_mutating_request` (use `execute_zapier_write_action`). Workbook base `https://graph.microsoft.com/v1.0/me/drive/root:/Desktop/VAT RETURNS/VAT Return-SEPT-DEC/VAT Return From Sept-Dec, 2026.xlsx:/workbook`. Insert rows with `POST .../range(address='62:63')/insert` body `{"shift":"Down"}`; PATCH `.../range(address='A62:W63')` body `{"formulas":[[...]]}`. Receipts folder item ID `D5AA8630B2ED2032!s7741549e63bf4460991c10fec413399e`. Avoid backslashes in JSON Remarks text. Cannot read receipt PDF/image content. Hit "task limit reached for the current billing period" on 4 Oct.
- Gmail connector reads body text, cannot download attachments.
- No Microsoft 365 work account exists (personal OneDrive), so the Claude M365 connector cannot be used.
- Scheduled cloud runs cannot self-grant device folder access.

## Standing rules (all applied throughout)
Bank statement is authoritative; never combine payments into one line item; new receipts renamed AND filed into a vendor subfolder in the same pass; every row has helper formulas, a Remarks note, correct chronological placement, all Sheet1 SUMIFS ranges (I, Q and U), and numeric Amount/VAT; check the FULL row range every visit; insert new rows directly before the Total row; receipts dated outside a tracker's own period are not logged into that tracker; never guess a figure only visible in an unreadable attachment, flag and ask; verify every write with a genuine content re-read; compare tracker mtime to renamed-receipt timestamps at the start of each run; any expense on a company card is logged as an ordinary row; card-ending variations are never flagged (including Apple Pay/Google Pay); receipts the user sends directly are logged without hold, even with no text; when the user clarifies a logged row, update its Remarks; small travel-incidental purchases are logged directly; routine food/snack purchases logged without a personal-use flag; check both Gmail AND the receipts folder roots every time; a receipt matching an already-logged row is a duplicate or supplementary, never a new row; V18 keeps "flag new items but don't auto-add"; when a row is half-finished from another session's or Wahidullah's edit, complete it in place; wholesale stock invoices are a different category and are not logged; charitable donations are VAT-No/out-of-scope but flagged for their own tax treatment; a provisional booking declined with no prepayment is not logged; an invoice or notice announcing a future Direct Debit is not logged until settled; when vendor/venue is unclear but amount/date/card are clear, log directly and note the ambiguity in Remarks; a single-item receipt for a known standard-rated product gets the vendor's usual VAT-No default with a stronger explicit flag; when a receipt prints an explicit VAT rate or amount, use it (VAT-Yes); a loose receipt with no context (different account or payment method) is flagged and held, but if the user then sends it directly, log it and keep the mismatch in Remarks; EVERY expense is a business expense (5 Oct 2026).
