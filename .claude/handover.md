# Handover — reconcile the PR #1 review, then verify (2026-09-18)

## Goal

Work through every finding in the review on PR #1 (`ps2-backend` → `main`), fix or
consciously decline each one, and prove the result with commands rather than assertion.
No code has been changed yet: the previous session only reviewed.

## Status

- PR: https://github.com/Jiackary/nebulax_lta/pull/1 — branch `ps2-backend`, head `6405e32`.
- A review is posted: 34 inline comments + a summary body
  (https://github.com/Jiackary/nebulax_lta/pull/1#pullrequestreview-5239015959).
- **Every claim was then independently re-verified** by five adversarial agents. 25 of the
  34 comments were edited in place with corrections; 9 were confirmed as posted. The text
  now on GitHub is the corrected text. Nothing is known to be wrong in it.
- Working tree is clean except an untracked `.DS_Store` (plus this `.claude/` folder).
- An earlier review round by `jephoton` (4 findings) was already addressed in `6405e32`.
  Those fixes hold, with two caveats captured in F17/F18 below.

## Next steps

1. Read `.claude/pr1-review-findings.md` — the full text of all 34 comments, indexed
   `F01`–`F34` with severity, location and the reproduction notes. This is the work list.
2. Agree a scope cut with the user before coding. Suggested order:
   - **P0 (2):** F01, F02 — lift-outage false negatives. These are route-safety bugs for a
     step-free persona and should not merge as they are.
   - **P1 (11):** F03–F13.
   - **P2 (17) / P3 (4):** batch or defer; several are doc-only.
3. Fix in small commits, one theme per commit, each naming the finding IDs it closes.
4. For anything declined, reply on that GitHub comment saying why, so the thread is closed
   rather than silently ignored.
5. Verify (see **Verification** below) and post a short follow-up comment on the PR
   summarising what was fixed, what was declined, and the verification output.

## Key decisions & constraints

- **Do not relitigate the review.** Its claims were re-verified and the wording corrected.
  If a fix seems unnecessary, check the comment's reproduction steps before disputing it.
- **`PS2_BACKEND_PLAN.md` §9 rule:** whoever implements a stage updates its row in the same
  commit as the code. Several findings are doc rows that have drifted from the code.
- **The rubric caps the score** for (a) a committed credential, (b) mocked data presented as
  live. F09 and F22 sit directly on (b).
- **Erring direction matters:** for this persona, a false "your route is clear" is far worse
  than a false warning. F01, F02 and F11 are all in that dangerous direction.
- **Two suggested fixes in the review were themselves corrected.** Use the current text:
  - F08: match entrances by station *name*; do **not** use a 250 m nearest-station radius,
    which would drop Outram Exit 6 (276 m), her default exit.
  - F22: do **not** add new `source` values; contract §1 limits `source` to
    `live · simulated`. Add a per-block `stale` flag instead (contract rule 4).
- The user asked for review only so far. **Get approval before pushing or merging anything.**

## Gotchas / learnings

- **Run everything offline:** `PS2_USE_FIXTURES=1` and `PS2_DB=<tmp>/x.sqlite3`, from
  `PS2/backend`, with `PYTHONPATH=.`. There is no `.env`, so no live credentials.
- **Fixtures are rewritten at runtime** (`app/sources/base.py:_record`), which dirties the
  git tree during tests. Monkeypatch `Source._record` to a no-op, or point
  `app.config.FIXTURES` at a temp dir. This is finding F12 itself.
- `PS2_USE_FIXTURES=1` is **not** a hard offline switch: a missing fixture still falls
  through to the network, and `app/sources/onemap.py` ignores the flag entirely.
- The repo venv at `PS2/backend/.venv` does not exist. Create one (`python3 -m venv`) or
  reuse a scratch venv; deps are `requirements.txt` + `requirements-dev.txt`. The previous
  session used Python 3.14 successfully even though the plan says 3.11.
- `data/derived/stepfree_graph.json` is 4.9 MB and its `built_at` changes on every rebuild,
  so avoid re-running `scripts/build_data.py` unless a finding requires it (it also needs
  live credentials).
- Trip IDs are 4 characters; `POST /api/trips` returns one and most endpoints need only it.
- `gh` CLI is authenticated and can post/patch review comments:
  `gh api -X PATCH repos/Jiackary/nebulax_lta/pulls/comments/<id> --input -`.

## Important files

- `.claude/pr1-review-findings.md` — **the work list.** All 34 comments in full, indexed.
- `.claude/repro/` — 47 scripts that reproduce the findings, plus `README.md` mapping each
  script to the findings it covers. Run them from `PS2/backend`; see that README. They are
  the evidence behind every "Reproduced" line, and the fastest way to confirm a fix.
- `PS2/PS2_BACKEND_PLAN.md` — §2 issues I1–I17, §9 build-status table (several stale rows).
- `PS2/PS2_API_CONTRACT.md` — §10 records known drift; findings add more.
- `PS2/PS2_DECISION_RECORD.md` — D1–D14, §8 privacy commitments (F20, F31 touch these).
- `PS2/PS2_INDEX.md` — provenance map; its header still says "No implementation started".
- `PS2/backend/app/` — the code under review; `tests/` has 9 passing tests.

## Verification

Baseline before changes (all currently pass):

```bash
cd PS2/backend
PS2_USE_FIXTURES=1 PS2_DB=/tmp/ps2v.sqlite3 <venv>/bin/python -m pytest -q     # 9 passed
PS2_USE_FIXTURES=1 <venv>/bin/python scripts/score_rules.py                     # 16/16
PS2_USE_FIXTURES=1 <venv>/bin/python scripts/verify_stepfree.py                 # PASS
git status --short                                                              # only .DS_Store
```

Per-finding verification, since the existing suite does not cover the bugs:

- **Add a regression test per fixed finding.** The current tests stub `send_push` (and
  `was_sent`/`mark_sent` in the scheduled-check tests), so they would not have caught most
  of these. `score_rules.py` never calls `assess()`, `affects_route` or `blocked_exits`.
- **Re-run the matching script in `.claude/repro/`** before and after each fix — its output
  before the fix should match the "Reproduced" line in the comment. Smoke-tested from the new
  location: `verify/v.py` still prints the F01/F02 output verbatim. Those scripts print rather
  than assert, so port each check into `PS2/backend/tests/` once the fix lands.
- Re-run the reproduction in each comment and confirm the behaviour changed. Examples:
  - **F02:** `LiftDesc: "Exits 5/6 Street level - Concourse"` at EW16 must block Exit 6, not
    just Exit 5 (default plan alights at Exit 6).
  - **F01:** `"Exit6 Street level - Concourse"` at EW16 must not say "Your route does not
    use it."
  - **F07:** arm the Outram scenario, `GET /status`, disarm it — the stored plan must return
    to Exit 6.
  - **F04:** `DELETE /api/push/subscribe` with no `endpoint` must not delete other trips.
- **Note that `verify_stepfree.py` can pass vacuously (F13).** Until that is fixed, its PASS
  is not evidence. Fix it first if you want it to back any claim.
- Finish with the full baseline above plus the new tests, and paste the real output into the
  PR follow-up comment. Do not claim a fix without the command output.
