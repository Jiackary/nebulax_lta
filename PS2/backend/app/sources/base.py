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
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import httpx

from ..config import FIXTURES, SGT, USE_FIXTURES

UA = "PS2-SmartCommuterCompanion/0.1 (LTA NebulaX hackathon)"


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
    """One upstream endpoint, cached."""

    def __init__(self, name: str, ttl: float, fetch: Callable[[httpx.AsyncClient], Any]):
        self.name = name
        self.ttl = ttl
        self._fetch = fetch
        self._entry: _Entry | None = None
        self._lock = asyncio.Lock()

    @property
    def fixture_path(self) -> Path:
        return FIXTURES / f"{self.name}.json"

    def _record(self, value: Any, observed: datetime) -> None:
        FIXTURES.mkdir(parents=True, exist_ok=True)
        self.fixture_path.write_text(json.dumps(
            {"recorded_at": observed.astimezone(SGT).isoformat(timespec="seconds"),
             "source": self.name, "payload": value},
            indent=1))

    def _from_fixture(self) -> Fetched | None:
        if not self.fixture_path.exists():
            return None
        blob = json.loads(self.fixture_path.read_text())
        return Fetched(blob["payload"], datetime.fromisoformat(blob["recorded_at"]),
                       stale=True, origin="fixture")

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
            try:
                value = await self._fetch(client)
                observed = datetime.now(SGT)
                self._entry = _Entry(value, time.monotonic(), observed)
                self._record(value, observed)
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
