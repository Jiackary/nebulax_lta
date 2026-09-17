"""PS2 Smart Commuter Companion — backend.

One persona (Mdm Lim), one journey (Bedok → Singapore General Hospital), built
to the decisions in PS2_DECISION_RECORD.md. See PS2_API_CONTRACT.md for what
each endpoint serves and PS2_BACKEND_PLAN.md §9 for build status.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import data, jobs, store
from .config import ATTRIBUTION, LTA_ACCOUNT_KEY, ONEMAP_TOKEN, USE_FIXTURES

log = logging.getLogger("ps2.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.init()
    data.walk_graph()          # load the graph once, not on first request
    scheduler = jobs.start()   # 20:00 / 07:00 checks and the 03:00 sweep (D3)
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title="PS2 Smart Commuter Companion",
    description=__doc__,
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

@app.exception_handler(StarletteHTTPException)
async def _http_error(request: Request, exc: StarletteHTTPException):
    """Serve the error shape the contract specifies, not FastAPI's `detail` wrapper.

    Registered for Starlette's HTTPException, not FastAPI's: routing raises the
    Starlette one, so unknown routes and wrong methods used to escape this and
    return a bare `{"detail": "Not Found"}` (F21).
    """
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(
        exc.status_code, "INVALID_REQUEST")
    return JSONResponse(status_code=exc.status_code, content={
        "error": {"code": code, "message": str(exc.detail), "retryable": False}})


@app.exception_handler(RequestValidationError)
async def _validation_error(request: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    where = ".".join(str(x) for x in first.get("loc", [])[1:]) or "request"
    return JSONResponse(status_code=422, content={
        "error": {"code": "INVALID_REQUEST",
                  "message": f"{where}: {first.get('msg', 'invalid request')}",
                  "retryable": False}})


from .api import alternatives, offline, push, status, trips  # noqa: E402

app.include_router(trips.router, prefix="/api")
app.include_router(status.router, prefix="/api")
app.include_router(alternatives.router, prefix="/api")
app.include_router(push.router, prefix="/api")
app.include_router(offline.router, prefix="/api")


@app.get("/api/health")
def health():
    wg = data.walk_graph()
    return {
        "ok": True,
        "graph_built_at": wg.built_at,
        "stations": len(data.stations()),
        "credentials": {
            "lta_account_key": bool(LTA_ACCOUNT_KEY),
            "onemap_token": bool(ONEMAP_TOKEN),
        },
        "fixtures_only": USE_FIXTURES,
    }


@app.get("/api/attribution")
def attribution():
    """Required wherever the map or anything derived from it is shown.

    Omitting OSM attribution is a licence breach, not a style point
    (PS2_README.md:L290).
    """
    return {
        "strings": ATTRIBUTION,
        "osm": {"text": "© OpenStreetMap contributors",
                "url": "https://www.openstreetmap.org/copyright",
                "licence": "ODbL 1.0"},
        "lta": {"text": "Contains information from LTA DataMall",
                "url": "https://datamall.lta.gov.sg"},
        "weather": {"text": "Weather data from data.gov.sg",
                    "url": "https://data.gov.sg"},
    }


@app.exception_handler(Exception)
async def _unhandled_error(request: Request, exc: Exception):
    """Anything that escapes a route still answers in the contract's shape (F21).

    Without this, an uncaught exception returned a text/plain 500 that no client
    parsing `error.code` could read.
    """
    log.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={
        "error": {"code": "INTERNAL_ERROR",
                  "message": "Something went wrong on our side.",
                  "retryable": True}})
