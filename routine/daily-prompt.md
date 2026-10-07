You are running the unattended Fone Nova expense check. Nobody is watching; do not ask questions. Read CLAUDE.md first and follow every standing decision in it. Never use em dashes.

The work file is {WORK_FILE}. It lists:
- `candidates`: new files in the Receipts Inbox (scans, `gmail/` downloads, `whatsapp/` uploads) and loose files at the receipts roots. Exact duplicates of filed receipts are already removed.
- `row_issues`: problems on the live Sept-Dec tracker (half-finished rows typed by hand, missing Remarks or helpers, structure).

Tools: use only `{CLI} ...` for tracker and filing changes. It backs up, verifies and restores on failure. Commands: `find`, `add`, `complete`, `file`, `statement`, `fx`, `archive`, `verify`, `status`. Usage is at the top of fonenova/cli.py. Never delete anything and never delete tracker rows (list suspected duplicates under `needs_hamza`). Never edit the xlsx any other way. V18 is read-only.

WhatsApp files are named `<YYYYMMDD-HHMM>_<Sender>_<msgid>_<name>`. A `..._note.txt` with the same prefix (or a separate note from the same sender within a few minutes) is context typed by the sender (vendor, booking ref, "same" for a second photo of one receipt): use it, then archive it.

Classify each candidate and handle it:

A. Receipt or invoice (photo, PDF, email):
1. Read the ORIGINAL file (Read tool for photos/PDFs; email .txt as text). Extract vendor, date (DD.MM.YY), gross, printed VAT, reference, card ending.
2. Skip and `archive --path <file>` (list under `skipped`): wholesale stock (Mobile One, WavePhone, Phone-Zone, etc.), marketing, statements with no charge, Direct Debit advance notices not yet settled, declined/provisional bookings with no payment, HMRC/legal correspondence.
3. Dated before 01.09.26: V18, flag only (`needs_hamza`). After 31.12.26: `needs_hamza`.
4. `find --date DD.MM.YY --amount N`. If a row matches:
   - it says "RECEIPT MISSING" (logged from a bank statement): file the receipt (step 5) and `complete --row N` with the printed VAT (VAT-Yes if printed) and new Remarks citing the filed PDF;
   - otherwise it is a duplicate or supporting copy: file it with `--descriptor Copy` (or a meaningful word) and add no row.
5. File it: `file --src <file> [<second photo> ...] --to-pdf --vendor "<Vendor>" --date DD.MM.YY [--folder <existing folder>]`. Photos become one clean greyscale PDF named `<Vendor>-DD.MM.YY.pdf`; the original goes to Receipts Inbox/processed. Pick an existing vendor folder when one fits; one-off restaurants go to `Restaurant-Takeaway`. Note the printed destination file name.
6. Log it with `add` (VAT from the receipt; Remarks: "Matched to <PDF file name>. <key facts: store, time, card ending, auth>. <VAT reasoning>").
   - VAT: printed VAT amount or rate means VAT-Yes with that amount. Otherwise the standing defaults (Tesco VAT-No with a note if mostly standard-rated, train/bus/flights VAT-No, nothing printed and no prior row: VAT-No, "not independently verified").
   - Every expense is a business expense. No purpose or personal-use flags.
7. An email whose body is the receipt (no attachment): file the `_email.txt` itself (no --to-pdf).

B. Revolut bank statement (CSV export, or PDF): for CSV run `statement --path <file>` first (dry run), check the output makes sense, then `statement --path <file> --log`. It logs unmatched card payments and fees VAT-No with "RECEIPT MISSING", records FX exchanges on the FX sheet and their fees as rows, and never logs transfers, top-ups, refunds or wholesale. Put every "RECEIPT MISSING" line it logged under `missing_receipts`, and its "for Hamza to review" lines under `needs_hamza`. File the statement: `file --src <file> --folder Bank-Statements --vendor Revolut-Statement --date <last date in it>`. For a PDF statement, read it and do the same by hand with `find` and `add` (VAT-No, "From Revolut statement <file>. RECEIPT MISSING ...").

C. FX confirmation (Revolut EUR to GBP exchange, PDF or screenshot): PDF: `fx --pdf <file>`; screenshot: read it and run `fx --date DD.MM.YY --eur N --gbp N --rate N --fee N`. It records the conversion on the FX sheet and logs the fee (VAT-No) unless that fee is already a row. File it in `Revolut-FX-Fees` with `--to-pdf` for screenshots.

For each row issue: complete the row in place with `complete` (convert text amounts, add helpers, write Remarks citing the receipt file). If the amount cannot be determined from a receipt, do not guess: `needs_hamza`.

What counts as `needs_hamza` (these make the email say "action needed", so keep it to real blockers):
an amount or date you cannot read, a suspected duplicate you did not resolve, an item outside the
tracker period, a statement line listed for review, or anything you could not file or log.
NOT `needs_hamza`: VAT decided by a standing default (Tesco VAT-No, travel VAT-No, "nothing printed:
VAT-No, not independently verified", energy top-ups with no VAT printed, etc.). Write that reasoning
in the row's Remarks only; the accountant reviews VAT treatment from the Remarks and the return pack.

Finish with `{CLI} verify`.

Then write {RESULT_FILE} as JSON:
{"logged": ["DD.MM.YY Vendor £X.XX VAT-Yes £Y.YY (row N), filed as Folder/File.pdf", ...],
 "completed": ["row N: what was fixed", ...],
 "skipped": ["file: reason", ...],
 "missing_receipts": ["DD.MM.YY Vendor £X.XX (row N)", ...],
 "needs_hamza": ["...", ...],
 "errors": ["...", ...],
 "whatsapp_replies": [{"to": "<Sender from the file name>", "text": "Logged: Tesco Express 06.10.26 £6.00 VAT-No (row 71), filed as Tesco/Tesco-Express-06.10.26.pdf"}, ...]}
One entry per expense, never combined totals. Add one `whatsapp_replies` entry per WhatsApp file you handled (logged, duplicate, skipped with the reason, or what you need from them). Write the result file even if everything failed.
