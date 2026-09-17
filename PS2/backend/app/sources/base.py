"""Upstream fetch with TTL cache, fixture recording, and stale-serving.

Three rules, from backend plan §6:

1. TTL matches the endpoint's real refresh rate. Polling faster buys nothing.
2. An adapter never fails a request because upstream is down. It degrades to
   the last good value and says how old it is — `observed_at` and `stale` are
   part of the contract, not decoration (API contract §1 rule 4).
3. Every successful response is written to `data/fixtures/`, so the demo runs
   with no network and a judge can see exactly what we received.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import httpx

from ..config import FIXTURES, RECORD_FIXTURES, SGT, USE_FIXTURES

UA = "PS2-SmartCommuterCompanion/0.1 (LTA NebulaX hackathon)"

log = logging.getLogger("ps2.sources")


def _default_recordable(value: Any) -> bool:
    """Reject the shapes that are not worth committing over a good fixture.

    An empty list or a null payload is a real response, but it is not one the
    offline demo should be pinned to.
    """
    if value is None:
        return False
    if isinstance(value, (list, dict, str)) and len(value) == 0:
        return False
    if isinstance(value, dict) and value.get("data") is None and "code" in value:
        return False                              # {"code": 24, "data": null}
    return True


@dataclass
class Fetched:
    """A payload plus the honesty fields the UI needs."""
    data: Any
    observed_at: datetime
    stale: bool = False
    origin: str = "live"          # live | fixture | stale
    error: str | None = None

    @property
    def observed_iso(self) -> str:
        return self.observed_at.astimezone(SGT).isoformat(timespec="seconds")


@dataclass
class _Entry:
    value: Any
    at: float
    observed: datetime


class Source:
    """One upstream endpoint, cached.

    `is_recordable` decides whether a response is worth committing as a fixture.
    It exists because BusArrival returns `[]` outside service hours (T17), and
    one live run after midnight used to overwrite a good 10-service fixture with
    an empty one — after which the offline demo said "Not running now" forever
    (F12).
    """

    def __init__(self, name: str, ttl: float, fetch: Callable[[httpx.AsyncClient], Any],
                 is_recordable: Callable[[Any], bool] | None = None):
        self.name = name
        self.ttl = ttl
        self._fetch = fetch
        self._is_recordable = is_recordable or _default_recordable
        self._entry: _Entry | None = None
        self._lock = asyncio.Lock()

    @property
    def fixture_path(self) -> Path:
        return FIXTURES / f"{self.name}.json"

    def _record(self, value: Any, observed: datetime) -> None:
        """Write the fixture atomically. Never called from inside the fetch's
        `try`: a read-only filesystem used to turn a good 200 into `origin:
        "stale"`, and a half-written file turned the fallback into a 500.
        """
        if not RECORD_FIXTURES:
            return
        if not self._is_recordable(value):
            log.debug("%s: response not recordable, keeping the committed fixture",
                      self.name)
            return
        try:
            FIXTURES.mkdir(parents=True, exist_ok=True)
            blob = json.dumps(
                {"recorded_at": observed.astimezone(SGT).isoformat(timespec="seconds"),
                 "source": self.name, "payload": value}, indent=1)
            tmp = self.fixture_path.with_suffix(".json.tmp")
            tmp.write_text(blob)
            os.replace(tmp, self.fixture_path)
        except OSError as exc:
            log.warning("%s: could not record fixture: %s", self.name, exc)

    def _from_fixture(self) -> Fetched | None:
        if not self.fixture_path.exists():
            return None
        try:
            blob = json.loads(self.fixture_path.read_text())
            return Fetched(blob["payload"], datetime.fromisoformat(blob["recorded_at"]),
                           stale=True, origin="fixture")
        except (OSError, ValueError, KeyError) as exc:
            # A truncated or hand-edited fixture must not become a 500.
            log.warning("%s: unreadable fixture: %s", self.name, exc)
            return None

    async def get(self, client: httpx.AsyncClient | None = None) -> Fetched:
        now = time.monotonic()
        if self._entry and now - self._entry.at < self.ttl:
            return Fetched(self._entry.value, self._entry.observed)

        if USE_FIXTURES:
            fx = self._from_fixture()
            if fx:
                return fx

        async with self._lock:
            if self._entry and time.monotonic() - self._entry.at < self.ttl:
                return Fetched(self._entry.value, self._entry.observed)
            owned = client is None
            client = client or httpx.AsyncClient(timeout=20, headers={"User-Agent": UA})
            fresh = None
            try:
                value = await self._fetch(client)
                observed = datetime.now(SGT)
                self._entry = _Entry(value, time.monotonic(), observed)
                fresh = (value, observed)
                return Fetched(value, observed)
            except Exception as exc:                      # upstream down or slow
                if self._entry:                           # last good value in memory
                    return Fetched(self._entry.value, self._entry.observed,
                                   stale=True, origin="stale", error=str(exc))
                fx = self._from_fixture()                 # last good value on disk
                if fx:
                    fx.error = str(exc)
                    return fx
                raise
            finally:
                if owned:
                    await client.aclose()
                if fresh is not None:
                    # Outside the try: a failed write must not downgrade a good
                    # fetch to "stale" (F12).
                    self._record(*fresh)
