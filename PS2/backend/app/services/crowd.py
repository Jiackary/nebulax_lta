"""Station crowding as one badge per station (D9).

Scope note, deliberately narrow: this is shown, and it changes nothing about her
route. Crowding is measured per *station*, not per train (§6 limitation 9), and
for a passenger who cannot stand comfortably the useful signal would be the
carriage — which no feed in DataMall exposes. Covering the visualisation
requirement (PS2_README.md:L266) is the honest reason it is here.
"""
from __future__ import annotations

from .. import data

LEVELS = {
    "l": ("low", "Not crowded", "ok"),
    "m": ("moderate", "Getting busy", "info"),
    "h": ("high", "Crowded", "warn"),
}
UNKNOWN = ("unknown", "No crowd reading", "info")


def badge(row: dict, stale: bool = False) -> dict:
    level, label, severity = LEVELS.get((row.get("CrowdLevel") or "").lower(), UNKNOWN)
    station = data.station_by_code().get(row.get("Station", ""))
    return {
        "station_code": row.get("Station"),
        "station_name": station["name"] if station else row.get("Station"),
        "level": level,
        "label": label,
        "severity": severity,
        "window": [row.get("StartTime"), row.get("EndTime")],
        # `source` stays live|simulated (contract §1). Whether the data is
        # current is a separate flag, so a recorded fixture stops reading as
        # live (contract rule 4, F22).
        "source": "live",
        "stale": stale,
    }


def for_stations(rows: list[dict], codes: set[str], stale: bool = False) -> list[dict]:
    return [badge(r, stale) for r in rows if r.get("Station") in codes]
