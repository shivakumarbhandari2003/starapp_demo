# StarApp — instructions for Claude Code

**Before doing anything, read `memory/README.md`, then `memory/AI_AGENT_PLAYBOOK.md`.** The `memory/` folder holds the full project context
(architecture, flowcharts, business rules, logic, database, work done so far, runbook). Read the file matching your task before editing code.

Non-negotiables (details in `memory/RULES_AND_CRITERIA.md`):
- Run tests **only** with `python tests/run_tests.py` (isolated DB copy). Never run unittest/pytest directly — suites wipe the DB they point at.
- Never `INSERT OR REPLACE` into tables with cascade children; use `INSERT … ON CONFLICT DO UPDATE`.
- The server must enforce every rule (UI hiding is not security). New org-wide actions go in `StarAppController._GUARDIAN_ONLY_ACTIONS`.
- Reviewer_Band > Badge_Band · 50-mark rubric · pass = badge `passing_percentage` (default 70) · attempts append-only · finalised attempts immutable.
- After changing `starapp/*.py` run `python scripts/pack_py.py` (rebuilds the offline bundle).
- Don't commit unintended changes to the tracked binary `data/starapp.db` (`git status data/` must be clean).
- After changing anything in `css/` or `js/`, bump the `?v=` query string in `index.html` + `sw.js` (the server caches versioned assets for 24 h, so browsers otherwise keep showing old styles) and the matching asserts in the tests.
- Log every meaningful change in `memory/WORK_DONE_AND_STATUS.md` §6 (date · area · previous logic · new logic · reason) and update the affected `memory/` file.
