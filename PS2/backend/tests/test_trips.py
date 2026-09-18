from datetime import datetime, timedelta, timezone

import pytest

from app.api.trips import TripRequest
from app.services import planner


def test_naive_appointment_is_interpreted_as_singapore_time():
    request = TripRequest(appointment_at=datetime(2026, 9, 19, 10, 30))

    assert request.appointment_at.utcoffset() == timedelta(hours=8)
    assert request.appointment_at.hour == 10


def test_aware_appointment_is_normalized_to_singapore_time():
    request = TripRequest(
        appointment_at=datetime(2026, 9, 19, 2, 30, tzinfo=timezone.utc)
    )

    assert request.appointment_at.utcoffset() == timedelta(hours=8)
    assert request.appointment_at.hour == 10


@pytest.mark.parametrize(
    "coord",
    [
        [103.8198, 1.3521],  # outside the committed Bedok corridor
        [103.9231, 1.3181],  # inside the bbox but too far from its walk graph
    ],
)
def test_planner_rejects_origins_the_walk_graph_cannot_represent(coord):
    with pytest.raises(RuntimeError, match="supported Bedok walking area"):
        planner.plan_trip(
            {"label": "Unsupported origin", "coord": coord},
            datetime(2026, 9, 19, 10, 30, tzinfo=planner.SGT),
        )
