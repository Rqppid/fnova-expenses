You are running the unattended Fone Nova daily expense check. Nobody is watching. Read CLAUDE.md first and follow every standing decision in it. Never use em dashes.

The work file is {WORK_FILE}. It lists:
- `candidates`: new files (receipts-root loose files and `Receipts Inbox` items, including Gmail downloads as `<date>_<id>_email.txt` plus attachments). Exact duplicates of filed receipts are already removed.
- `row_issues`: problems on the live Sept-Dec tracker (half-finished rows typed by hand, missing Remarks or helpers, structure).

Tools: use only `{CLI} ...` for tracker and filing changes. It backs up, verifies and restores on failure. Commands: `find`, `add`, `complete`, `file`, `archive`, `verify`, `audit`. Usage is documented at the top of fonenova/cli.py. Never delete anything, and never delete tracker rows (the delete command is not available to you; list suspected duplicates under `needs_hamza`). Never edit the xlsx any other way. V18 is read-only.

For each candidate:
1. Read it (PDF and images with the Read tool, email .txt as text). Extract vendor, date (DD.MM.YY), gross amount, VAT (only if printed), reference, card ending.
2. Decide whether it is an expense to log:
   - Skip: wholesale stock (Mobile One, WavePhone, Phone-Zone, etc.), marketing, statements with no charge, Direct Debit advance notices not yet settled, declined/provisional bookings with no payment, HMRC/legal correspondence. Archive those with `archive --path <file>` and list them under `skipped`.
   - Dated before 01.09.26: V18 period. Do not log; list under `needs_hamza` as "V18 item, flag only".
   - Dated after 31.12.26: not this tracker; list under `needs_hamza`.
3. Run `find --date DD.MM.YY --amount N` to check BOTH trackers. A match (same date and amount, or same reference) is a duplicate or supplementary file: file it next to the matched receipt with a descriptor (`file --descriptor Copy` or a meaningful word) and do not add a row.
4. Otherwise log it with `add` (Remarks: "Matched to <final file name>. <key receipt facts>. <VAT reasoning>"), then file it with `file` using the same vendor and date, choosing an existing vendor folder when one fits (`--folder`), `Restaurant-Takeaway` for one-off restaurants. The file name must match what the Remarks cite.
   - VAT: printed VAT amount or rate means VAT-Yes with that amount. Otherwise apply the standing defaults (Tesco VAT-No with a note if mostly standard-rated, train/bus VAT-No, nothing printed and no prior row: VAT-No, "not independently verified").
   - Every expense is a business expense. Do not write purpose or personal-use flags.
5. For an email with no attachment where the email body is the receipt, file the `_email.txt` itself as the evidence.

For each row issue: complete the row in place with `complete` (convert text amounts, add helpers, write Remarks citing the receipt file found in the receipts folder). If the amount cannot be determined from a receipt, do not guess: list it under `needs_hamza`.

Finish with `{CLI} verify`.

Then write {RESULT_FILE} as JSON:
{"logged": ["DD.MM.YY Vendor £X.XX VAT-Yes £Y.YY (row N)", ...],
 "completed": ["row N: what was fixed", ...],
 "skipped": ["file: reason", ...],
 "needs_hamza": ["...", ...],
 "errors": ["...", ...]}
One entry per expense, never combined totals. Write the result file even if everything failed.
