# PS2 backend — Smart Commuter Companion

One persona, one journey: **Mdm Lim**, travelling **Bedok (EW5) → Singapore General
Hospital** for a fortnightly appointment, step-free, with a lift-outage warning the
evening before.

Why this persona and what was decided: [`../PS2_DECISION_RECORD.md`](../PS2_DECISION_RECORD.md).
How it is built: [`../PS2_BACKEND_PLAN.md`](../PS2_BACKEND_PLAN.md).
What it serves: [`../PS2_API_CONTRACT.md`](../PS2_API_CONTRACT.md) — and `/docs` once running.

## Prerequisites

- Python 3.11+
- A free LTA DataMall `AccountKey` — register at <https://datamall.lta.gov.sg>
- A free OneMap API token — register at <https://www.onemap.gov.sg/apidocs/>
  (used for address search only; the walking routes are computed here)

## Run it

```bash
cd PS2
cp .env.example .env          # then paste your two keys into it
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt

cd backend
../backend/.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

Open <http://localhost:8000/docs>. `GET /api/health` shows whether each credential
was found.

`.env` is gitignored and must stay that way — a committed credential caps the score.

## Try the journey

```bash
# 1. plan her trip
curl -s -X POST localhost:8000/api/trips -H 'content-type: application/json' \
  -d '{"appointment_at":"2026-09-19T10:30:00+08:00"}'

# 2. live overlay: lifts, disruption, crowding, rain
curl -s localhost:8000/api/trips/<trip_id>/status

# 3. turn on the labelled demo scenario, then look again
curl -s -X POST localhost:8000/api/scenario -H 'content-type: application/json' \
  -d '{"lift_outage_outram":true,"ewl_disruption":true}'
curl -s localhost:8000/api/trips/<trip_id>/status
curl -s localhost:8000/api/trips/<trip_id>/alternatives

# 4. the warning she would receive, without waiting for 20:00
curl -s -X POST localhost:8000/api/push/test
```

With the scenario on, her plan re-routes from Outram Park Exit 6 to Exit 7 and she is
told to leave earlier. **Every simulated object carries `source: "simulated"` and a
`simulated_note` that the UI must display.** The four real lift outages stay `live`
in the same array.

## Rebuilding the committed data

`backend/data/derived/` is checked in, so the app runs without any of this. To rebuild:

```bash
cd PS2 && set -a && . ./.env && set +a
backend/.venv/bin/python backend/scripts/build_data.py --all
```

`--fetch` pulls GTFS, `TrainStationExit`, `CoveredLinkWay`, `BusRoutes`/`BusStops` and
two cached Overpass extracts into `backend/data/cache/` (gitignored). `--build` derives
the artefacts and prints a measurement for every figure it produces. Overpass is queried
**twice, and cached** — the brief forbids looping on the public instance.

## The numbers we claim, and how to reproduce them

```bash
cd backend
../backend/.venv/bin/python scripts/score_rules.py       # parser accuracy, 16/16
../backend/.venv/bin/python scripts/verify_stepfree.py   # the step-free claim (D11)
```

| Claim | Where it comes from |
|---|---|
| Train ride is a fixed 30.67 min, no spread across all 698 EW5→EW16 trips | `build_data.py --build`, printed each run |
| Headway 2.5 min at 08h weekday, 5.0 off-peak at Bedok | same |
| Lift-outage exit join: 2 of 4 live rows | `score_rules.py`, decision record §3.2 |
| Parser accuracy 16/16 on held examples | `score_rules.py`; examples in `data/handchecked/` |
| Step-free route costs 13 m over the unrestricted one | `verify_stepfree.py` |

## Running with no network

Every successful upstream fetch records a fixture under `backend/data/fixtures/`.

```bash
PS2_USE_FIXTURES=1 ../backend/.venv/bin/python -m uvicorn app.main:app --port 8000
```

The app then serves entirely from recorded data, flagged `stale` with the time it was
observed. It also falls back to this automatically if an upstream dies.

## Attribution

Required wherever the map or anything derived from it is shown — omitting it is a
licence breach, not a style point. `GET /api/attribution` serves the strings.

- © OpenStreetMap contributors (ODbL 1.0)
- Contains information from LTA DataMall
- Weather data from data.gov.sg
