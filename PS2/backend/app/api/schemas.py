"""Response models, so `/openapi.json` describes what comes back as well as
what goes in.

Written for the frontend. Before this, all 16 endpoints were untyped on the way
out: a screen could generate request types from the schema but had to hand-write
every response shape from `PS2_API_CONTRACT.md` prose — prose that §10 records
drifting from the code more than once.

Two rules these models follow, both about not breaking a working API:

**They are built from the payloads, not from the contract.** Every field here
was read off a live response (`tests/data/api_surface.json` is that capture, and
`tests/test_response_models.py` asserts the two still agree). A model written
from the prose would have quietly deleted whatever the prose forgot.

**They add nothing and remove nothing.** `extra="allow"` keeps any field a route
grows before its model catches up, and the routes pass
`response_model_exclude_unset=True` so an optional field that a particular code
path does not set stays absent rather than appearing as `null`. Between them, a
model that is wrong makes the schema incomplete — it cannot corrupt the
response. That matters here because several payloads are genuinely
heterogeneous: a walk leg has no `line`, a taxi option has no `arrival_at`, and
`null` is a meaningful value elsewhere (`tiles.tile_pack_url`, an
unresolved `lift_alerts[].exit_code`).

Where a payload varies by kind, it is a discriminated union on `mode`, so the
frontend narrows on that field and gets exactly the right keys.
"""
from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

Coord = list[float]


class Schema(BaseModel):
    """Permissive by construction — see the module docstring."""
    model_config = ConfigDict(extra="allow", populate_by_name=True)


# --- the error envelope (contract §1) ---------------------------------------

class ErrorBody(Schema):
    code: str = Field(description="Machine-readable; the §1 enum.")
    message: str = Field(description="Shown to the user as written.")
    retryable: bool = Field(description="Whether the same call may succeed later.")


class ErrorResponse(Schema):
    error: ErrorBody


#: Every route answers failures in the §1 envelope, so say so once.
ERROR_RESPONSES: dict[int | str, dict] = {
    "4XX": {"model": ErrorResponse, "description": "The §1 error envelope."},
    "5XX": {"model": ErrorResponse, "description": "The §1 error envelope."},
}


class DeletedTrip(Schema):
    deleted: bool
    note: str


# --- service metadata -------------------------------------------------------

class HealthCredentials(Schema):
    lta_account_key: bool
    onemap_token: bool


class Health(Schema):
    ok: bool
    graph_built_at: str
    stations: int
    credentials: HealthCredentials = Field(
        description="Whether each credential is present — never its value.")
    fixtures_only: bool = Field(
        description="True when the server is serving recorded upstream responses.")


class AttributionLink(Schema):
    text: str
    url: str


class OsmAttribution(AttributionLink):
    licence: str


class Attribution(Schema):
    strings: list[str] = Field(description="Ready to display, in order.")
    osm: OsmAttribution
    lta: AttributionLink
    weather: AttributionLink


class Destination(Schema):
    id: str
    label: str
    block: str
    coord: Coord


class Destinations(Schema):
    destinations: list[Destination]


class Place(Schema):
    label: str
    address: str
    postal: str | None = Field(default=None, description="Null when OneMap says NIL.")
    coord: Coord


class PlaceSearch(Schema):
    results: list[Place]
    source: str | None = Field(default=None, description="Absent for an empty query.")


# --- the plan (contract §3) -------------------------------------------------

class LegPoint(Schema):
    name: str
    coord: Coord
    station_code: str | None = None
    exit_code: str | None = Field(
        default=None, description='Rendered form, e.g. "Exit 6".')


class LineString(Schema):
    type: Literal["LineString"]
    coordinates: list[Coord] = Field(description="[lon, lat] pairs, in walking order.")


class AccessPoint(Schema):
    exit_code: str
    status: Literal["yes", "no", "unknown"] = Field(
        description="What OSM knows about that door. `unknown` is not `no` (§6 limitation 5).")


class LegAccess(Schema):
    board_at: AccessPoint
    alight_at: AccessPoint


class LineRef(Schema):
    code: str
    name: str
    colour: str


class WalkLeg(Schema):
    leg_id: str
    mode: Literal["walk"]
    from_: LegPoint = Field(alias="from")
    to: LegPoint
    duration_min: int
    distance_m: int
    covered_m: int
    instruction: str
    step_free: Literal["yes", "no", "unknown"]
    surface_warnings: list[str]
    geometry: LineString


class RailLeg(Schema):
    leg_id: str
    mode: Literal["rail"]
    from_: LegPoint = Field(alias="from")
    to: LegPoint
    line: LineRef
    duration_min: int | None
    headway_min: float | None = Field(
        description="Measured at the hour she boards, not the appointment's (F27).")
    instruction: str
    step_free: Literal["yes", "no", "unknown"]
    access: LegAccess
    geometry: LineString


Leg = Annotated[Union[WalkLeg, RailLeg], Field(discriminator="mode")]


class PlanSummary(Schema):
    leave_by: str
    leave_by_label: str
    arrival_window: list[str] = Field(description="[earliest, latest] ISO-8601.")
    arrival_label: str
    appointment_label: str
    buffer_min: int
    duration_min: int
    range_min: list[int] = Field(description="[fast, slow] minutes.")
    timing_basis: str = Field(description="Why the number is what it is, in a sentence.")
    step_free: Literal["yes", "no", "unknown"]
    sheltered_pct: int
    walk_distance_m: int


class MapFeatureProperties(Schema):
    leg_id: str
    mode: str


class MapFeature(Schema):
    type: Literal["Feature"]
    properties: MapFeatureProperties
    geometry: LineString


class FeatureCollection(Schema):
    type: Literal["FeatureCollection"]
    features: list[MapFeature]


class TripMap(Schema):
    bbox: list[float] = Field(description="[west, south, east, north].")
    geometry: FeatureCollection


class TripPlan(Schema):
    trip_id: str
    appointment_at: str
    summary: PlanSummary
    legs: list[Leg]
    map: TripMap
    attribution: list[str]


# --- the live overlay (contract §4) -----------------------------------------

Severity = Literal["ok", "info", "warn", "critical"]


class OverallAction(Schema):
    kind: str
    label: str


class Overall(Schema):
    severity: Severity
    headline: str
    detail: str
    action: OverallAction | None = None


class LiftAlert(Schema):
    station_code: str
    station_name: str
    station_id: str | None
    line: str | None
    exit_code: str | None = Field(
        description="First blocked exit, or null when the description named none.")
    blocked_exit_refs: list[str] = Field(
        description="Every exit the outage takes out. Read this, not `exit_code`, "
                    "to decide where she may walk (F02).")
    lift_id: str | None
    lift_desc: str = Field(description="Upstream text, unedited.")
    resolution: str = Field(description="How confidently the description was matched.")
    parsed_exits: list[str]
    line_prefix: str | None
    severity: Severity
    label: str
    detail: str
    affects_route: bool
    source: Literal["live", "simulated"]
    observed_at: str
    stale: bool
    simulated_note: str | None = Field(
        default=None, description="Present only on simulated rows; must be displayed.")


class Disruption(Schema):
    line: str | None
    severity: Severity
    headline: str
    detail: str
    delay_min: int | None
    delay_basis: str | None
    affected_stations: list[str]
    on_her_route: bool
    free_bus_available: bool
    free_bus_islandwide: bool
    source: Literal["live", "simulated"]
    observed_at: str
    stale: bool
    simulated_note: str | None = None


class Crowd(Schema):
    # Straight from the upstream row with no defaults, so a sparse reading
    # gives nulls rather than an absent block. Typing them as required would
    # turn a cosmetic gap in one badge into a 500 for the whole status call.
    station_code: str | None
    station_name: str | None
    level: str
    label: str
    severity: Severity
    window: list[str | None] = Field(
        description="[start, end] of the 10-minute bucket; null when the row omits them.")
    source: Literal["live", "simulated"]
    stale: bool
    observed_at: str


class WeatherArea(Schema):
    name: str | None = Field(
        description="Null when the nowcast carried no areas — an upstream outage.")
    for_: str = Field(alias="for", description="Which end of the trip this area covers.")
    distance_km: float | None = Field(
        description="Null when no area could be placed — the distance is then unbounded.")
    forecast: str | None


class Weather(Schema):
    rain_expected: bool
    areas: list[WeatherArea]
    label: str
    severity: Severity
    affects_route: bool
    source: Literal["live", "simulated"]
    stale: bool
    observed_at: str


class Checks(Schema):
    last_checked_at: str
    next_check_at: str | None
    label: str


class RouteStatus(Schema):
    trip_id: str
    overall: Overall
    lift_alerts: list[LiftAlert]
    disruption: Disruption | None = Field(
        description="Null on a quiet day — there is no advisory to report.")
    crowd: list[Crowd]
    weather: Weather | None = Field(
        description="Null when the nowcast could not be read at all; the rest of "
                    "the overlay is still served.")
    checks: Checks
    rerouted: bool = Field(
        description="The stored plan was rebuilt because an outage blocked a door it used.")
    replan_failed: bool = Field(
        description="Every step-free entrance is out and no route could be built.")
    stale: bool
    observed_at: str


# --- alternatives (contract §5) ---------------------------------------------

class OriginalOption(Schema):
    label: str
    duration_min: int | None
    arrival_at: str | None
    viable: bool
    step_free: Literal["yes", "no", "unknown"]
    note: str


class BusInfo(Schema):
    service_no: str
    board_stop: str
    board_stop_code: str
    alight_stop: str
    alight_stop_code: str
    stops: int | None
    distance_km: float | None
    walk_min: int | None
    ride_min: int | None
    eta_min: int | None
    eta_is_scheduled: bool | None
    load: str | None
    load_label: str | None
    wheelchair_accessible: bool | None = Field(
        description="Null when LTA does not say; drives `step_free` on the option.")
    not_running: bool | None
    first_bus: str | None
    last_bus: str | None
    observed_at: str | None
    stale: bool | None


class TaxiStand(Schema):
    name: str | None
    coord: Coord
    distance_m: int | None
    barrier_free: bool | None
    fare_estimate: str | None
    anchor: str = Field(description="Which end of the journey the stand is measured from.")


class OptionBase(Schema):
    option_id: str
    label: str
    why: str
    delta_min: int | None
    step_free: Literal["yes", "no", "unknown"]
    severity: Severity
    timing_basis: str
    legs: list[Any]
    rank: int


class RailOption(OptionBase):
    mode: Literal["rail"]
    leave_by: str | None = None
    leave_by_label: str | None = None
    arrival_at: str | None = None
    duration_min: int | None = None
    viable: bool | None = Field(
        default=None, description="False when the suggested departure has already passed.")


class BusOption(OptionBase):
    mode: Literal["bus"]
    duration_min: int | None = None
    bus: BusInfo


class TaxiOption(OptionBase):
    mode: Literal["taxi"]
    duration_min: int | None = None
    taxi_stand: TaxiStand


Option = Annotated[Union[RailOption, BusOption, TaxiOption], Field(discriminator="mode")]


class NotOffered(Schema):
    label: str
    why_not: str
    note: str | None = None


class Alternatives(Schema):
    trip_id: str
    disruption: Disruption | None
    original: OriginalOption
    options: list[Option]
    not_offered: list[NotOffered]


# --- the offline bundle (contract §6) ---------------------------------------

class Tiles(Schema):
    style_url: str | None
    tile_pack_url: str | None
    attribution: str
    zoom_range: list[int]
    unavailable_reason: str | None = Field(
        description="Why there is no tile pack, so the screen can say so.")


class OfflinePlan(TripPlan):
    """The stored plan as the bundle carries it: no `trip_id`, plus replan state."""
    trip_id: str | None = None
    rerouted: bool | None = None
    replan_failed: bool | None = None
    blocked_signature: str | None = None


class OfflineBundle(Schema):
    trip_id: str
    generated_at: str
    plan: OfflinePlan
    status_snapshot: RouteStatus | None = Field(
        default=None, description="Null when status could not be read; see `warnings`.")
    steps_plain: list[str] = Field(description="The route in words, for no-map use.")
    tiles: Tiles
    warnings: list[str] = Field(
        description="Never serves written steps without either a snapshot or a warning.")
    offline_notice: str
    attribution: list[str]


# --- the demo switches (contract §8) ----------------------------------------

class ScenarioFlagsOut(Schema):
    lift_outage_outram: bool
    ewl_disruption: bool


class ScenarioState(Schema):
    enabled: bool = Field(description="The master switch. `_on()` reads this and the flag.")
    scenarios: ScenarioFlagsOut
    note: str


# --- push (contract §7) -----------------------------------------------------

class PushKey(Schema):
    public_key: str


class Subscribed(Schema):
    subscribed: bool
    checks: list[str] = Field(description="The checks this subscription will receive.")


class Unsubscribed(Schema):
    unsubscribed: bool
    subscriptions_removed: int
    trips_removed: int
    note: str


class PushResult(Schema):
    endpoint: str = Field(description="Truncated; never the full endpoint.")
    sent: bool
    error: str | None = Field(
        default=None,
        description="A code (`PUSH_FAILED`, `ENDPOINT_NOT_ALLOWED`, `ENDPOINT_GONE`, "
                    "`PUSH_NOT_CONFIGURED`), never the upstream body (F03).")


class PushPayload(Schema):
    title: str
    body: str
    trip_id: str
    severity: Severity
    url: str
    digest: str | None = None
    sent_at: str | None = None
    source: str | None = None
    simulated_note: str | None = None


class PushTest(Schema):
    sent: bool
    subscriptions: int
    results: list[PushResult]
    payload: PushPayload = Field(
        description="What would have been sent, so it is readable without a paired device.")
    note: str | None = None
