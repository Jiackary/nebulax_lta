"""Test setup: offline, throwaway DB, and never write to the committed fixtures.

`app.config` reads the environment at import time, so this has to run before any
`app.*` import — pytest loads conftest first, which is why these are set here
rather than in a fixture.

The `_record` no-op matters beyond tidiness: `Source.get` rewrites
`data/fixtures/*.json` on every successful fetch, so a test that reaches an
adapter would dirty the git tree with real recorded data (finding F12).
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="ps2-tests-"))

os.environ.setdefault("PS2_USE_FIXTURES", "1")
os.environ["PS2_DB"] = str(_TMP / "test.sqlite3")

import pytest  # noqa: E402

from app.sources.base import Source  # noqa: E402


@pytest.fixture(autouse=True)
def never_write_fixtures(monkeypatch):
    """No test may rewrite a committed fixture."""
    monkeypatch.setattr(Source, "_record", lambda self, value, observed: None)
