"""Shared test isolation for process-wide module state.

`amplifier_module_tool_computer_use._announcement_decisions` (the one-
disclosure-decision-per-physical-channel cache added to fix the double-
announce defect - see `tests/test_announcement_dedup.py`) is deliberately
process-lifetime state, exactly like `shared_transport._registry`
(`tests/test_shared_transport.py` already clears that one the same way).
Without this, one test's fake backend "consuming" a channel key leaks into
every later test that happens to construct a fake with the same `.name` -
most of the existing announcement tests use `_FakeRemoteBackend("macos")`,
which all hash to the same channel key by design (that IS the behavior
under test), so isolation between test functions has to be enforced here,
not left to chance.

`_remote_latency_warned` (bug-hunt defect B: the remote-latency safety
notice deduped once-per-physical-channel, mirroring `_announcement_decisions`
above) has the exact same shape and the exact same leak risk - cleared here
for the same reason, not left to unique-per-test host names like
`_channel_ledgers`/`_channel_band_state` (see `test_retarget.py`), because
several of its own tests deliberately reuse the same host across test
functions to prove the "still warns once for a fresh channel" case.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modules" / "tool-computer-use"))

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_announcement_decisions():
    import amplifier_module_tool_computer_use as cu

    cu._announcement_decisions.clear()
    cu._remote_latency_warned.clear()
    yield
    cu._announcement_decisions.clear()
    cu._remote_latency_warned.clear()
