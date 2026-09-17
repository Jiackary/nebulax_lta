"""Rain changes her walking route; nothing else (D9).

Resolution is a named forecast area, not her street (§6 limitation 10). The
nearest area to SGH is "City" at about 1.7 km, and to her home "Bedok" at about
1.7 km — so the label names the area it actually read, rather than implying a
street-level forecast we do not have.
"""
from __future__ import annotations

from ..config import HOME_DEFAULT, SGH
from ..sources import weather


def assess(nowcast: dict, stale: bool = False,
           prefer_sheltered: bool = True) -> dict:
    home_area, home_km = weather.area_for(nowcast, HOME_DEFAULT["coord"][1],
                                          HOME_DEFAULT["coord"][0])
    sgh_area, sgh_km = weather.area_for(nowcast, SGH["coord"][1], SGH["coord"][0])
    home_fc = weather.forecast_for(nowcast, home_area)
    sgh_fc = weather.forecast_for(nowcast, sgh_area)
    wet_home, wet_sgh = weather.is_wet(home_fc), weather.is_wet(sgh_fc)
    rain = wet_home or wet_sgh

    if rain:
        where = " and ".join(a for a, w in ((home_area, wet_home), (sgh_area, wet_sgh)) if w)
        # The planner does not read the weather: shelter comes only from
        # `preferences.prefer_sheltered`. "We have kept your walk covered" was
        # therefore true only by accident, and false outright when that
        # preference is off (F28). Say which of the two is actually the case.
        label = (f"Rain forecast in {where} in the next 2 hours. Your walk is already "
                 f"routed under shelter wherever we could find it."
                 if prefer_sheltered else
                 f"Rain forecast in {where} in the next 2 hours. Your route is not "
                 f"weighted towards shelter — you can turn that on in your preferences.")
    else:
        label = f"No rain forecast for {home_area} or {sgh_area} in the next 2 hours"

    return {
        "rain_expected": rain,
        "areas": [
            {"name": home_area, "for": "home", "distance_km": home_km, "forecast": home_fc},
            {"name": sgh_area, "for": "hospital", "distance_km": sgh_km, "forecast": sgh_fc},
        ],
        "label": label,
        "severity": "info" if rain else "ok",
        "affects_route": rain,
        "source": "live",
        "stale": stale,
    }
