"""Bug-hunt defect B: the remote-latency safety notice
(`_build_coexistence_guard`, `__init__.py`) printed TWICE for one real
session - once when the root session's own `mount()` built its guard against
`remote-ssh:macos`, and again when the delegated `computer-use:computer-operator`
sub-agent's `mount()` built its OWN guard against the SAME physical machine.

The notice describes a property of the BACKEND/CHANNEL (its measured
transport latency), not of any one session, so two mounts against the same
target logging it twice is noise that dilutes a real safety warning - not a
second, distinct fact. It must still fire (this is safety-relevant, never
silenced - see docs/designs/coexistence.md §5.7), just once per physical
channel per process, mirroring the exact mechanism `_announcement_decisions`
already uses to solve "more than one mount() in this process, one physical
channel" for session-start disclosure (see that dict's own docstring).

No real SSH, no real display server - a fake `Backend`-shaped stand-in with
just enough surface (`is_remote`, `user_host`, `presence_idle_ms`,
`presence_platform`) for `_build_coexistence_guard` to exercise its real
decision logic, same no-real-backend approach as
`test_coexistence_guard_windows_remote.py`.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modules" / "tool-computer-use"))

from amplifier_module_tool_computer_use import _build_coexistence_guard


class _FakeRemoteBackend:
    """Stands in for `RemoteBackend`: `is_remote = True`, a composite `name`
    (never a `GUARD_MS` key by design), `presence_platform` resolving to the
    real remote platform, and `user_host` - the actual `user@host` string
    `_channel_identity` keys on so two DIFFERENT hosts of the same platform
    are never conflated (see that function's own docstring)."""

    is_remote = True

    def __init__(self, remote_platform: str, user_host: str) -> None:
        self.name = f"remote-ssh:{remote_platform}"
        self.presence_platform = remote_platform
        self.user_host = user_host

    def presence_idle_ms(self) -> float:
        return 999_999.0


def _remote_latency_records(records) -> list:
    return [r for r in records if "is remote - every presence sample" in r.message]


def test_remote_latency_warning_fires_once_across_two_mounts_of_the_same_channel(
    caplog,
):
    """The exact reported shape: a root session's mount() and a delegated
    child's mount() against the SAME `user@host` - two SEPARATE `Backend`
    instances (each mount() constructs its own), same physical channel.
    Must warn once between them, not once each."""
    caplog.set_level(logging.WARNING, logger="amplifier_module_tool_computer_use")

    root_backend = _FakeRemoteBackend("macos", "brkrabac@brians-macbook-pro-os")
    child_backend = _FakeRemoteBackend("macos", "brkrabac@brians-macbook-pro-os")

    guard1 = _build_coexistence_guard(root_backend, {})
    guard2 = _build_coexistence_guard(child_backend, {})

    assert guard1 is not None
    assert guard2 is not None
    hits = _remote_latency_records(caplog.records)
    assert len(hits) == 1, (
        f"expected exactly one remote-latency warning across two mounts of "
        f"the same channel, got {len(hits)}: {[r.message for r in hits]}"
    )


def test_remote_latency_warning_still_fires_at_all_for_a_fresh_channel(caplog):
    """Never silenced (§5.7 of docs/designs/coexistence.md): a genuinely NEW
    physical channel (different `user_host`) must still get its own warning -
    proves the fix dedups per-channel, not process-wide-forever."""
    caplog.set_level(logging.WARNING, logger="amplifier_module_tool_computer_use")

    backend = _FakeRemoteBackend("macos", "brkrabac@some-other-mac")
    guard = _build_coexistence_guard(backend, {})

    assert guard is not None
    hits = _remote_latency_records(caplog.records)
    assert len(hits) == 1


def test_remote_latency_warning_dedups_independently_per_channel(caplog):
    """Two DIFFERENT physical channels each get their own warning - the dedup
    key is `_channel_identity` (per physical machine), not a single global
    once-ever flag."""
    caplog.set_level(logging.WARNING, logger="amplifier_module_tool_computer_use")

    mac = _FakeRemoteBackend("macos", "brkrabac@brians-macbook-pro-os")
    windows = _FakeRemoteBackend("windows-wsl2", "brkrabac@alienware-r13")

    _build_coexistence_guard(mac, {})
    _build_coexistence_guard(windows, {})
    # A second mount against the FIRST channel again - still must not re-warn.
    _build_coexistence_guard(
        _FakeRemoteBackend("macos", "brkrabac@brians-macbook-pro-os"), {}
    )

    hits = _remote_latency_records(caplog.records)
    assert len(hits) == 2, (
        f"expected one warning per distinct channel (2 channels), got "
        f"{len(hits)}: {[r.message for r in hits]}"
    )
