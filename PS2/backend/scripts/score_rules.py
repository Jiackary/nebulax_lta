#!/usr/bin/env python3
"""Score the rule-based parsers on every held example (D13).

D13 chose rules over a model and owes a measurement for that choice. This prints
n/N for both parsers and exits non-zero on any failure, so it can gate a commit.

    python scripts/score_rules.py

The examples live in `data/handchecked/` and are shipped with the repo, so a
judge can read every case and re-run this without paying for anything.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.disruption import TEST_RE, parse_delay      # noqa: E402
from app.services.lifts import (annotate_for_route, blocked_exits,   # noqa: E402
                                match_row, parse_exits)

HAND = Path(__file__).resolve().parent.parent / "data" / "handchecked"


def score_lift_desc() -> tuple[int, int, list[str]]:
    blob = json.loads((HAND / "lift_desc_examples.json").read_text())
    failures, passed = [], 0
    print("LiftDesc exit parser")
    print(f"{'':3} {'station':8} {'parsed':10} {'resolution':13} {'expected':13} "
          f"{'blocked':12} result")
    for ex in blob["examples"]:
        exits, _prefix = parse_exits(ex["lift_desc"])
        row = match_row({"StationCode": ex["station_code"], "LiftDesc": ex["lift_desc"],
                         "LiftID": ex["lift_id"], "Line": ""})
        ok = (exits == ex["expect_exits"]
              and row["resolution"] == ex["expect_resolution"])

        # The route outcome, not just the parse. Scoring only `parsed_exits` and
        # `resolution` is why #7 passed while the planner still walked her into
        # the second blocked door (F02).
        blocked = ""
        if "expect_blocked" in ex:
            got, _ = blocked_exits(annotate_for_route([dict(row)]))
            got = {k: sorted(v) for k, v in got.items()}
            want = {k: sorted(v) for k, v in ex["expect_blocked"].items()}
            blocked = ",".join(f"{k}:{'/'.join(v)}" for k, v in sorted(got.items())) or "-"
            if got != want:
                ok = False
                failures.append(f"#{ex['id']} {ex['lift_desc'][:40]}: "
                                f"blocked {got}, want {want}")
        passed += ok
        if not ok and exits == ex["expect_exits"] \
                and row["resolution"] == ex["expect_resolution"]:
            pass                      # already recorded as a blocked-exit failure
        elif not ok:
            failures.append(f"#{ex['id']} {ex['lift_desc'][:52]}: "
                            f"got {exits}/{row['resolution']}, "
                            f"want {ex['expect_exits']}/{ex['expect_resolution']}")
        print(f"{ex['id']:>3} {ex['station_code']:8} {str(exits):10} {row['resolution']:13} "
              f"{ex['expect_resolution']:13} {blocked:12} {'ok' if ok else 'FAIL'}")
    return passed, len(blob["examples"]), failures


def score_messages() -> tuple[int, int, list[str]]:
    blob = json.loads((HAND / "message_examples.json").read_text())
    failures, passed = [], 0
    print("\nDelay-minute parser")
    print(f"{'':3} {'delay':>6} {'expected':>9} {'test?':>6} result")
    for ex in blob["examples"]:
        delay, _basis = parse_delay(ex["content"])
        is_test = bool(TEST_RE.match(ex["content"]))
        ok = delay == ex["expect_delay_min"] and is_test == ex["expect_is_test"]
        passed += ok
        if not ok:
            failures.append(f"#{ex['id']}: got delay={delay} test={is_test}, "
                            f"want delay={ex['expect_delay_min']} test={ex['expect_is_test']}")
        print(f"{ex['id']:>3} {str(delay):>6} {str(ex['expect_delay_min']):>9} "
              f"{str(is_test):>6} {'ok' if ok else 'FAIL'}")
    return passed, len(blob["examples"]), failures


def main() -> None:
    lp, lt, lf = score_lift_desc()
    mp, mt, mf = score_messages()
    print("\n" + "=" * 62)
    print(f"LiftDesc exit parser   {lp}/{lt}")
    print(f"Delay-minute parser    {mp}/{mt}")
    print(f"Total                  {lp + mp}/{lt + mt}")
    live = sum(1 for e in json.loads((HAND / 'lift_desc_examples.json').read_text())["examples"]
               if e.get("live"))
    print(f"\n{live} of the {lt} LiftDesc rows are captured live from the feed; the rest cover "
          f"format variants\nnamed in trap T20. No Telegram notices are included — "
          f"PS2_README.md:L207 says to ask first.")
    for f in lf + mf:
        print(f"  FAIL {f}")
    sys.exit(1 if (lf or mf) else 0)


if __name__ == "__main__":
    main()
