# Repro scripts for the PR #1 review findings

Throwaway scripts written while reviewing PR #1 and while re-verifying the review. They are
the evidence behind every "Reproduced" line in `.claude/pr1-review-findings.md`. Keep them
until the findings are closed; they are the cheapest way to prove a fix actually worked.

## How to run

All of them expect to run **from `PS2/backend`** (several do `sys.path.insert(0, os.getcwd())`),
against fixtures, with a throwaway DB:

```bash
cd PS2/backend
PS2_USE_FIXTURES=1 PS2_DB=/tmp/ps2repro.sqlite3 PYTHONPATH=. \
  <venv>/bin/python ../../.claude/repro/verify/v.py
```

`vr/A/t1.py`, `t2.py`, `t3.py` take the backend path as `sys.argv[1]` instead.

There is no `.env`, so nothing here uses live credentials. Network calls are faked with
`httpx.MockTransport` or a local `http.server`. Scripts that write fixtures redirect
`app.config.FIXTURES` to a temp dir — **keep that** if you edit them, or they will dirty the
repo (that behaviour is finding F12).

## What is where

| Path | Written by | Covers |
|---|---|---|
| `verify/v.py` | main session spot-check | F01, F02 (lift false negatives), F04 (delete-all), F09 (scenario in push), F22 (fixture labelled live) |
| `verify/v6.py`, `v7.py` | main session spot-check | F08 — Outram entrances mixing in Chinatown/Cantonment exits |
| `r3/repro1.py`–`repro3.py` | lifts/disruption reviewer | F01, F02, F06, F07, F10, F26, plus the alternatives findings F23–F25 |
| `rev/r1.py`–`r6.py` | planner/trips reviewer | F08 (entrances), F11 and F17 (step-free claims, snapping), F15 (validation), F16 (address search), F27 (timing), F30 (trip IDs) |
| `srcrev/r_base.py`, `r_bus.py`, `r_prov.py`, `r_build.py`, `r_verify.py` | sources reviewer | F12 and F29 (fixture recording, cache lock), F22/F23 (`r_prov`, `r_bus`: provenance and bus ETA), F13 (`r_verify`: vacuous PASS), F32/F34 (`r_build`: build scripts) |
| `push_repro.py`, `http_repro.py`, `http_repro_tc.py` | push reviewer | F03 (SSRF), F04, F05, F14, F18 (duplicate pushes, 410 cleanup), F19 (check windows), F20 (retention) |
| `docrev/run1.py`, `run2.py` | docs reviewer | the docs-vs-code section of the review summary |
| `vr/A/*` | verifier A | re-verification of the push/jobs/store comments |
| `vr/B/*` | verifier B | re-verification of the lifts/status/alternatives comments |
| `vr/C/*` | verifier C | re-verification of the planner/timing/trips comments |
| `vr/D/*` | verifier D | re-verification of the sources/scripts comments and the summary's minor section |
| `vr/E/measure.py` | verifier E | re-measurement of the plan's stage 3/4 numbers (696 m vs 707 m, reroute deltas) |

**Not repro scripts:** `verify/build_review.py` and `verify/edits.py` are the tooling that
posted the review and patched the 25 corrected comments. They contain absolute paths from the
session that produced them and are kept only as a record of what was posted.

## A note on the finding IDs

An earlier draft of this file (and of `../handover.md`) carried several wrong IDs — the
vacuous-PASS finding was called F31, the build scripts F32/F33, and the provenance script
F13. Every ID in the table above has since been checked against the comment text in
`../pr1-review-findings.md`, which is what was fetched from GitHub, and against what each
script actually exercises. That file is authoritative if anything here ever disagrees again.

## Caveat

These were written to *demonstrate bugs*, not as a test suite: they print rather than assert,
and some depend on the committed fixtures' contents and on today's date. When a finding is
fixed, port its check into `PS2/backend/tests/` as a real regression test rather than relying
on the script.
