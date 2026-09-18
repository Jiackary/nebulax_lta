"""The response models must describe the API, not reshape it.

`response_model=` makes the model authoritative: FastAPI drops any field the
model does not declare. So the risk of typing the responses is that a model
written slightly wrong deletes a field the screen needs, silently, with every
test still green.

`data/api_surface.json` is the key map captured from the code *before* the
models existed. These tests assert the served payloads still match it exactly —
nothing dropped, nothing invented.

If a route legitimately gains or loses a field, regenerate the file:

    PYTHONPATH=.:tests python -c "import json,pathlib; from api_surface import capture; \\
        from app.main import app; \\
        pathlib.Path('tests/data/api_surface.json').write_text( \\
            json.dumps(capture(app), indent=1) + '\\n')"

and the diff is then the API change, up for review on its own.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from api_surface import capture
from app.main import app

GOLDEN = Path(__file__).parent / "data" / "api_surface.json"


@pytest.fixture(scope="module")
def served() -> dict[str, list[str]]:
    return capture(app)


@pytest.fixture(scope="module")
def golden() -> dict[str, list[str]]:
    return json.loads(GOLDEN.read_text())


def test_every_endpoint_is_still_covered(served, golden):
    assert sorted(served) == sorted(golden)


@pytest.mark.parametrize("endpoint", json.loads(GOLDEN.read_text()).keys())
def test_no_field_was_dropped_or_invented(served, golden, endpoint):
    """One case per endpoint, so a failure names the route and the field."""
    was, now = set(golden[endpoint]), set(served[endpoint])

    assert not (was - now), f"{endpoint} lost: {sorted(was - now)}"
    assert not (now - was), f"{endpoint} gained: {sorted(now - was)}"


def test_the_openapi_schema_types_every_response():
    """The point of the exercise: a frontend can generate response types."""
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        spec = c.get("/openapi.json").json()

    untyped = [
        f"{verb.upper()} {path}"
        for path, ops in spec["paths"].items()
        for verb, op in ops.items()
        if not op.get("responses", {}).get("200", {})
        .get("content", {}).get("application/json", {}).get("schema")
    ]

    assert untyped == []


def test_the_error_envelope_is_documented():
    """§1 says every failure uses one shape; the schema should say so too."""
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        spec = c.get("/openapi.json").json()

    trips = spec["paths"]["/api/trips"]["post"]["responses"]
    assert "4XX" in trips
    assert "Error" in json.dumps(trips["4XX"])


def test_a_walk_leg_is_not_given_rail_fields():
    """The discriminated union earns its place here.

    A single Leg model with everything optional would have hung `line: null`,
    `access: null` and `headway_min: null` on both walk legs.
    """
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        plan = c.post("/api/trips", json={"appointment_at": "2026-09-21T10:30:00"}).json()

    walk = next(leg for leg in plan["legs"] if leg["mode"] == "walk")
    rail = next(leg for leg in plan["legs"] if leg["mode"] == "rail")

    assert "line" not in walk and "access" not in walk and "headway_min" not in walk
    assert "surface_warnings" not in rail and "covered_m" not in rail
    assert rail["line"]["code"] == "EWL"
