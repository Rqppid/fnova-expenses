# Run log

## 2026-10-05
- Phase 1 orientation done (read-only). Backups: VAT RETURNS/_backups/2026-10-05_205132 (SHA-256 verified).
- Python 3.12.10 installed; repo scaffolded; audit() working. No tracker writes.
- 2026-10-05 22:11 daily: gmail {'error': 'No valid Gmail token. Run: python -m fonenova.cli gmail-auth'}, 0 new candidate(s), 0 duplicate(s), 1 tracker issue(s), no claude run, 1 alert(s)
- 2026-10-05 22:20 Phase 2-4 built: CLI, audit, filing, verify, diff (no feature loss), pack (May-Oct £43,316.64 / VAT £2,334.65), daily routine (dry run OK, Gmail not yet authorised). Live tracker NOT modified: deletion of duplicate row 5 blocked by permission policy, awaiting Hamza.
- 2026-10-05 22:17 Sept-Dec row 5 (Tesco 01.09.26 £5.50, duplicate of V18 r313) deleted via cli delete (run by Hamza). Backup _backups/2026-10-05_221719_delete. Verified: rows to 69, £8,946.09 / £423.06 / £8,523.03, no feature loss.
- 2026-10-05 22:24 daily: gmail {'error': 'No valid Gmail token. Run: python -m fonenova.cli gmail-auth'}, 0 new candidate(s), 0 duplicate(s), 0 tracker issue(s), no claude run, 0 alert(s)
- 2026-10-05 22:25 Cleanup: 13 exact-duplicate receipts moved to VAT RETURNS/_duplicates-review/septdec (not deleted). Remarks citations updated to current file names on rows 15,16,17,22,25,37,38,43,50,61,62 (backup 2026-10-05_222346_remarks). Daily task registered (21:30). Accountant questions drafted in Gmail (not sent).
- 2026-10-05 Filed HQ-IWG VAT invoice 7920-712 as HQ-IWG-Service/HQ-IWG-Service-01.09.26-Invoice-7920-712.pdf (copied: original in Downloads was open in another program); row 28 Remarks now cite it. Invoice 7920-756 sent by Hamza is identical to the copy already filed (pending until the 15 Oct payment).
- 2026-10-06 22:25 Cloud routine trig_01G32dURdhpkujQ3cfFcpE68 verified (supervised run cse_01FnBUKpRMkmBoZWuQCUHLrj: signed in, mirrored 499 files, no work, pushed state, lock released) and ENABLED nightly 20:30 UTC. PC task "FoneNova Daily Expense Check" DISABLED (kept as backup: Enable-ScheduledTask to restore). PC run 21:30 had triaged 24 Gmail items correctly (0 expenses, 2 supporting copies filed).
