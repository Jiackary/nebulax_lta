"""F17 — snapping must use the components of the step-free graph, not of the
graph with stairs.

The build records one main component per area, computed with staircases in
place. Remove them and Bedok's main component is 105 disconnected pieces, so
the nearest node to an origin is often on an island nothing can be reached
from. The planner then answered "no step-free walking route to a usable
entrance" for a coordinate a few tens of metres from the real network — a
refusal that reads as "we can't get you there" when we can.

From `.claude/repro/rev/r5.py`.
"""
from __future__ import annotations

from datetime import datetime

import networkx as nx
import pytest

from app import data
from app.config import HOME_DEFAULT, SGT
from app.services import planner, walking

APPOINTMENT = datetime(2026, 9, 19, 10, 30, tzinfo=SGT)

# From the finding: snaps 34 m onto a 47-node island while sitting 42 m from the
# step-free network that actually reaches an entrance.
STRANDED = [103.937, 1.3197]


@pytest.fixture(scope="module")
def wg():
    return data.walk_graph()


@pytest.mark.parametrize("area", ["bedok", "outram"])
def test_step_free_candidates_are_one_connected_piece(wg, area):
    """The property the old code assumed and did not have."""
    sub = wg.step_free.subgraph(wg.candidates(area, True))

    assert nx.number_connected_components(sub) == 1


def test_bedok_step_free_candidates_are_the_largest_piece(wg):
    """Guard against the fix throwing away the network instead of the islands."""
    assert len(wg.candidates("bedok", True)) == 12077


def test_an_origin_beside_the_network_gets_a_route(wg):
    """Before the fix this raised "no step-free walking route to a usable entrance"."""
    plan = planner.plan_trip({"label": "Home", "coord": STRANDED}, APPOINTMENT)

    assert plan["summary"]["duration_min"] > 0


def test_that_origin_no_longer_snaps_to_an_island(wg):
    node, snapped = walking._snap(wg, STRANDED, "bedok", True)

    assert node in set(wg.candidates("bedok", True))
    assert snapped <= planner.MAX_ORIGIN_SNAP_M


def test_an_origin_far_from_the_network_is_still_refused():
    """The fix must not turn a genuine miss into a route from 300 m away."""
    far = [103.9426, 1.3292]                      # inside the bbox, 162 m off the network

    with pytest.raises(RuntimeError, match="outside the supported"):
        planner.plan_trip({"label": "Home", "coord": far}, APPOINTMENT)


def test_the_default_home_plan_is_unchanged(wg):
    """Her committed default must route exactly as before the fix."""
    plan = planner.plan_trip(HOME_DEFAULT, APPOINTMENT)

    walk = next(leg for leg in plan["legs"] if leg["mode"] == "walk")
    assert walk["step_free"] == "yes"
    assert plan["summary"]["step_free"] == "yes"
