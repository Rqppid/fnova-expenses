Fone Nova expense check (cloud; nightly, and instantly after a WhatsApp upload). Nobody is watching; do not ask questions. Never use em dashes.

1. Setup (the machine's `pip` and `python` can point at different Python versions, so always use a
   fresh virtual environment and its python):
   `python3 -m venv /tmp/venv && /tmp/venv/bin/python -m pip install -q -r requirements.txt`
   Use `/tmp/venv/bin/python` for EVERY python command below.
2. Prepare: `/tmp/venv/bin/python -m fonenova.cloud prep --dest /tmp/vat`
   It mirrors the OneDrive "VAT RETURNS" folder to /tmp/vat, fetches receipt emails into the
   Receipts Inbox and prints JSON with `work_needed`, `work_file`, `result_file` and `cli`.
   If prep fails (sign-in or network), stop and report the error; there is nothing to push.
   If it prints `"busy": true`, another run is in progress and will run again afterwards: stop
   here and do NOT run finish.
3. If `work_needed` is true: read routine/daily-prompt.md and follow it exactly, with
   {WORK_FILE} = work_file, {RESULT_FILE} = result_file and {CLI} = the printed `cli` value
   (always pass `--mirror /tmp/vat`; never run the CLI without it).
   Receipts in the mirror are placeholders except the Receipts Inbox and loose root files, which
   are real. Do not try to open filed receipts; `find` and the Remarks are enough.
   If `work_needed` is false, skip this step.
4. Finish (always, even if step 3 failed): `/tmp/venv/bin/python -m fonenova.cloud finish --dest /tmp/vat`
   It records the run, pushes changes back to OneDrive (the tracker only if nobody edited it
   meanwhile) and emails Hamza only when something needs him.
5. Print the finish output as your final message.
