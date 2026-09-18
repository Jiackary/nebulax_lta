"""F27 — the headway must come from the hour she boards, and the app must not
invent a train.

Three separate ways the timetable lookup was wrong:

  * it asked for the appointment's hour, about an hour after she boards;
  * missing hours fell back to the nearest hour that existed, so a query for
    03:00 was answered with the 01:00 figure and a line that shuts at midnight
    got a plan;
  * public holidays ran the weekday table.

The first under-estimates her wait, which breaks "plan against the slow end".
The second sends her to a shut station. From `.claude/repro/rev/r6.py`.
"""
from __future__ import annotations

from datetime import datetime

import pytest

from app import data
from app.config import HOME_DEFAULT, ORIGIN_STATION, SGT
from app.services import planner, timing
from app.services.planner import RAIL_DIRECTION, RAIL_ROUTE


def hw(when: datetime) -> float | None:
    return timing.headway_min(RAIL_ROUTE, ORIGIN_STATION, RAIL_DIRECTION, when)


def plan_at(when: datetime) -> dict:
    return planner.plan_trip(HOME_DEFAULT, when)


def rail_leg(plan: dict) -> dict:
    return next(leg for leg in plan["legs"] if leg["mode"] == "rail")


# --- the hour she boards, not the hour of her appointment -------------------

def test_the_two_hours_really_do_differ():
    """If this ever stops holding, the test below proves nothing."""
    assert hw(datetime(2026, 9, 21, 8, 40, tzinfo=SGT)) == 2.5     # appointment
    assert hw(datetime(2026, 9, 21, 7, 39, tzinfo=SGT)) == 5.0     # boarding


def test_the_plan_uses_the_boarding_hour():
    """A Monday 08:40 appointment boards around 07:39, when it is 5.0 not 2.5."""
    plan = plan_at(datetime(2026, 9, 21, 8, 40, tzinfo=SGT))

    assert rail_leg(plan)["headway_min"] == 5.0


def test_the_extra_wait_reaches_the_advice_she_reads():
    """The point of the fix, in the two numbers on her screen.

    A headway is only worth correcting if it changes what she is told. Pricing
    the wait at 5.0 rather than 2.5 moves the slow end out by the difference and
    leaves_by earlier to match: before the fix this plan said 07:32 and
    [44, 52], which is "plan against the slow end" being short by 2.5 min.
    """
    summary = plan_at(datetime(2026, 9, 21, 8, 40, tzinfo=SGT))["summary"]

    assert summary["leave_by"][11:16] == "07:30"
    assert summary["range_min"] == [44, 55]


def test_the_basis_sentence_no_longer_says_this_hour():
    plan = plan_at(datetime(2026, 9, 21, 8, 40, tzinfo=SGT))

    assert "every 5 min when she boards" in plan["summary"]["timing_basis"]


# --- no trains running ------------------------------------------------------

def test_no_nearest_hour_fallback():
    """03:00 used to answer with the 01:00 figure."""
    assert hw(datetime(2026, 9, 21, 3, 0, tzinfo=SGT)) is None


@pytest.mark.parametrize("hour,minute", [(1, 30), (3, 0), (5, 30)])
def test_an_appointment_with_no_service_is_refused(hour, minute):
    """01:30 used to return "leave 00:20"; 05:30 planned boarding in hour 4."""
    with pytest.raises(RuntimeError, match="not running"):
        plan_at(datetime(2026, 9, 21, hour, minute, tzinfo=SGT))


def test_the_first_trains_of_the_day_still_plan():
    """The guard against refusing real service: 06:30 boards in hour 5, which runs."""
    plan = plan_at(datetime(2026, 9, 21, 6, 30, tzinfo=SGT))

    assert rail_leg(plan)["headway_min"] == 5.0


def test_the_refusal_names_the_time_it_checked():
    with pytest.raises(RuntimeError, match=r"around 0\d:\d\d"):
        plan_at(datetime(2026, 9, 21, 1, 30, tzinfo=SGT))


def test_has_service_separates_no_trains_from_no_table():
    at_0300 = datetime(2026, 9, 21, 3, 0, tzinfo=SGT)
    at_1000 = datetime(2026, 9, 21, 10, 0, tzinfo=SGT)

    assert timing.has_service(RAIL_ROUTE, ORIGIN_STATION, RAIL_DIRECTION, at_0300) is False
    assert timing.has_service(RAIL_ROUTE, ORIGIN_STATION, RAIL_DIRECTION, at_1000) is True
    # No table at all is unknown, not "no service" — it must not refuse a plan.
    assert timing.has_service(RAIL_ROUTE, "EW999", RAIL_DIRECTION, at_1000) is None


# --- public holidays --------------------------------------------------------

def test_a_public_holiday_uses_the_sunday_table():
    christmas = datetime(2026, 12, 25, 9, 30, tzinfo=SGT)       # a Friday
    ordinary = datetime(2026, 12, 18, 9, 30, tzinfo=SGT)        # the Friday before

    assert timing.daytype_of(christmas) == "sunday_ph"
    assert timing.daytype_of(ordinary) == "weekday"


def test_the_holiday_headway_reaches_the_plan():
    holiday = rail_leg(plan_at(datetime(2026, 12, 25, 10, 30, tzinfo=SGT)))
    ordinary = rail_leg(plan_at(datetime(2026, 12, 18, 10, 30, tzinfo=SGT)))

    assert holiday["headway_min"] > ordinary["headway_min"]


def test_the_holiday_list_loads():
    holidays = data.public_holidays()

    assert "2026-12-25" in holidays
    assert "2026-12-18" not in holidays


def test_holiday_dates_are_well_formed():
    """A typo here silently reverts that date to the weekday table."""
    for iso in data.public_holidays():
        datetime.fromisoformat(iso)
