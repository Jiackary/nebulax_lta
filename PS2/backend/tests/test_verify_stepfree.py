"""F13 — `verify_stepfree.py` must not be able to PASS without checking anything.

Its output is a claim that goes into WRITEUP.md, so the failure mode that matters
is not a wrong FAIL but a PASS that verified nothing. Each test here is one of the
three ways it used to do that, taken from `.claude/repro/srcrev/r_verify.py`.
"""
from __future__ import annotations

import asyncio
import copy
import importlib.util
from pathlib import Path

import pytest

from app import data
from app.config import HOME_DEFAULT, SGT

_SPEC = importlib.util.spec_from_file_location(
    "verify_stepfree", Path(__file__).resolve().parent.parent / "scripts" / "verify_stepfree.py")
verify_stepfree = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(verify_stepfree)

PASS, FAIL = verify_stepfree.PASS, verify_stepfree.FAIL


@pytest.fixture(scope="module")
def plan():
    from datetime import timedelta
    from app.services import planner
    appointment = (planner.datetime.now(SGT).replace(second=0, microsecond=0)
                   + timedelta(days=1, hours=10))
    return planner.plan_trip(HOME_DEFAULT, appointment)


def _walk_leg(plan):
    return next(leg for leg in plan["legs"] if leg["mode"] == "walk")


def test_real_plan_still_passes(plan):
    """The guard against over-tightening: the committed plan must still verify."""
    assert verify_stepfree.check_no_steps(plan)[0] == PASS
    assert asyncio.run(verify_stepfree.check_entrances(plan))[0] == PASS


def test_nudged_coordinates_fail_instead_of_being_skipped(plan):
    """A pair that resolves to no graph edge is unchecked, so it must not PASS.

    Before the fix a real staircase edge FAILed on exact coordinates but PASSed
    when nudged by 1 cm, because unresolved pairs hit `continue`.
    """
    nudged = copy.deepcopy(plan)
    leg = _walk_leg(nudged)
    leg["geometry"]["coordinates"] = [[lon + 0.0000001, lat]
                                      for lon, lat in leg["geometry"]["coordinates"]]

    verdict, notes = verify_stepfree.check_no_steps(nudged)

    assert verdict == FAIL
    assert any("UNRESOLVED" in n for n in notes)


def test_resolved_edge_counts_are_reported(plan):
    """A reader must be able to see how much was actually checked."""
    _, notes = verify_stepfree.check_no_steps(plan)

    assert any("17/17 edges resolved" in n for n in notes)
    assert any("27/27 edges resolved" in n for n in notes)


def test_plan_with_no_walk_legs_fails(plan):
    stripped = copy.deepcopy(plan)
    stripped["legs"] = [leg for leg in stripped["legs"] if leg["mode"] != "walk"]

    assert verify_stepfree.check_no_steps(stripped)[0] == FAIL


def test_plan_with_no_identifiable_entrances_fails(plan):
    """Stripping station_code/exit_code used to yield ('PASS', []) — a vacuous pass."""
    stripped = copy.deepcopy(plan)
    for leg in stripped["legs"]:
        for end in ("from", "to"):
            if leg.get(end):
                leg[end].pop("station_code", None)
                leg[end].pop("exit_code", None)

    verdict, notes = asyncio.run(verify_stepfree.check_entrances(stripped))

    assert verdict == FAIL
    assert any("verified nothing" in n for n in notes)


def test_untagged_entrance_with_no_nearby_lift_fails(plan, monkeypatch):
    """`ok = tag == "yes" or not lift_out` passed any untagged door with no outage."""
    wg = data.walk_graph()
    untagged = {ref: {**e, "wheelchair": None, "coord": [103.0, 1.0]}
                for ref, e in wg.entrances_for("outram").items()}
    monkeypatch.setattr(wg, "entrances_for",
                        lambda area: untagged if area == "outram" else {})

    verdict, notes = asyncio.run(verify_stepfree.check_entrances(plan))

    assert verdict == FAIL
    assert any("accessibility unknown" in n for n in notes)


def test_tagged_wheelchair_no_fails(plan, monkeypatch):
    wg = data.walk_graph()
    tagged_no = {ref: {**e, "wheelchair": "no"}
                 for ref, e in wg.entrances_for("outram").items()}
    monkeypatch.setattr(wg, "entrances_for",
                        lambda area: tagged_no if area == "outram" else {})

    verdict, notes = asyncio.run(verify_stepfree.check_entrances(plan))

    assert verdict == FAIL
    assert any("wheelchair=no" in n for n in notes)
