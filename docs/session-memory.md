# Session memory (handover for the next context window)

Written by memorycompactskill on 2026-10-07. Overwritten in full each time. Facts only.

## Current task
- Hamza asked: "create a skill ( call it something simple like memorycompactskill) so before the
  session compacts you get all the memory and data and put it into an md file so you dont
  hallucinate/ lose any focus or important details)".
- Done 07.10.26: skill at `C:\Users\fonen\.claude\skills\memorycompactskill\` (SKILL.md,
  snapshot.py, config.json), PreCompact + SessionStart(compact) hooks in
  `C:\Users\fonen\.claude\settings.json`, snapshot output `C:\Users\fonen\.claude\memorycompact\latest.md`.
- Next: nothing pending on this; wait for Hamza's next request.

## In-flight state
- This file (docs/session-memory.md) is not committed. No other uncommitted work known.
- Bot and cloud routine are live; nothing waiting on a deploy.

## User rules (Hamza Ismati, Fone Nova Ltd, Belfast phone wholesale; director is his father Wahidullah)
- Lead with the answer. Rank options and name a pick. Flag VAT, legal and reputational risk unprompted.
- NEVER use em dashes.
- Report expenses as separate line items, never combined totals.
- Default to doing and flagging, not asking. Ask only when the decision is his and irreversible.
- Every expense is a business expense: never flag purpose, personal use or director's loan.
- Do not delete anything without asking. Moves, never copies. V18 tracker is read-only (flag only).
- Unattended runs never delete tracker rows.
- Never echo, paste or enter secrets (tokens, app secret) anywhere; they live in git-ignored
  `secrets/` and in Vercel / Claude routine env. He pasted the WA token and app secret in chat
  earlier: rotation advised.
- He wants step-by-step instructions with direct links when he has to click something.

## Live system
- Repo `C:\Users\fonen\fonenova-expenses`, GitHub `Rqppid/fnova-expenses` (private), branch main.
  CLAUDE.md there has all conventions.
- Data root `C:\Users\fonen\OneDrive\Desktop\VAT RETURNS` (OneDrive base `Desktop/VAT RETURNS`).
  State and run log in `VAT RETURNS/_automation/`.
- Cloud routine `trig_01G32dURdhpkujQ3cfFcpE68`: nightly 20:30 UTC + API trigger
  (`https://api.anthropic.com/v1/claude_code/routines/{id}/fire`, headers
  `anthropic-version: 2023-06-01`, `anthropic-beta: experimental-cc-routine-2026-04-01`),
  debounce 180 s. Debug with RemoteTrigger list_runs / get_run_log.
- WhatsApp webhook `https://fonenova-intake.vercel.app/api/whatsapp` (Vercel team "quay").
  Meta test number +1 555 631 0829, phone_number_id 1293187523886245, WABA 931178819750215.
  Allowed senders: Hamza 447359818591, Wahidullah 447852402537, Company 447949922872.
  Results are copied to the other numbers, except Hamza's uploads are NOT copied to Wahidullah
  (config.toml [whatsapp.no_copy], since 09.10.26). Texts reply "Noted" and do not trigger runs.
- Microsoft Graph client id 5260e8c6-8f4e-4565-bf67-cb16aec78746; rotating refresh token in
  Google Drive appData `fonenova-cloud.json`. Google scopes gmail.readonly, gmail.send, drive.appdata.
- PC scheduled task "FoneNova Daily Expense Check" is DISABLED (backup only).
- Email to fonenovaltd@gmail.com only for alerts starting Needs / Error / Gmail / Excel /
  Receipt missing / VAT return due. Reminders 31 Oct and 5 Nov.

## Data state (Sept-Dec tracker, checked live 07.10.26)
- Rows 5-74, Total row 75: gross £9,092.39, VAT £428.08, net £8,664.31.
- V18 (May-Aug + 01.09): rows 5-313, gross £34,370.55, VAT £1,911.59.
- Latest rows:
  - Row 70: Ryanair 05.10.26 £52.49 VAT-No (KCZ6XR).
  - Row 71: Tesco Express 06.10.26 £19.17 VAT-No.
  - Row 72: Revolut FX fee 06.10.26 £24.52 VAT-No (EUR 6,000 to £5,062.76 on FX sheet).
    Ref reads "Revolut txn " with no id: the statement txn id was blank.
  - Row 73: Budget Energy 07.10.26 £20.00 VAT-No (energy usually 5% VAT; not printed).
  - Row 74: Tesla Supercharger 07.10.26 £30.12 VAT-Yes £5.02.
- VAT pack (May-Oct) last built: £43,316.64 gross / £2,334.65 VAT. Must be rebuilt.

## Decisions made
- Statement card payments with no receipt are logged VAT-No "RECEIPT MISSING"; transfers,
  top-ups, refunds, wholesale lines are only listed.
- Photos become greyscale PDFs (not 1-bit) so faded VAT lines stay legible.
- Test number now, own SIM after 7 Nov. Separate Vercel project for the webhook.
- Emails only when important; routine confirmations go to WhatsApp only.

## Known gotchas
- Never save the tracker with os.replace (breaks the OneDrive link): save in place via temp file
  + shutil.copyfile. Refuse if an Excel `~$` lock exists.
- openpyxl: never insert_rows; rewrite totals, regenerate U/V/W helpers, extend the 8 SUMIFS.
- Denied before, never retry: deleting tracker row 5, hidden `.fn-root` pointer file, uploading
  the tracker to OneDrive to overwrite the cloud copy.
- PowerShell: `rd` is Remove-Item; variable names are case-insensitive.
- No POSTs in Vercel logs means a Meta-side problem (account block on 7 Oct).
- Test number profile (name/photo) cannot be edited; save it as a contact with a photo instead.

## Open items and deadlines
- Before 31 Oct 2026: tighten V18 receipt matching, then rebuild the VAT return pack
  (`python -m fonenova.cli pack`).
- 7 Nov 2026: VAT return due; Hamza sends the pack with the Gmail accountant draft.
- Optional: `expense_update` WhatsApp template + `WA_COPY_TEMPLATE` env; own SIM after 7 Nov;
  delete `secrets/` and `_duplicates-review` (ask first); Vercel Pro decision (Hobby is
  non-commercial); row 72 txn id. (Ryanair KCZ6XR receipt is already filed: row 70.)
