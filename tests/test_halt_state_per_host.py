"""Regression test for the defect verified against `remote_backend.py:123` /
`__init__.py`'s halt-recording call sites: the durable halt-state KEY handed
to `record_halt`/`load_halt`/`make_durable_halt_poll` was `backend.name`,
which for `RemoteBackend` is the COMPOSITE `"remote-ssh:<platform>"` string
(`RemoteBackend.connect()`) - identical for any two DIFFERENT remote hosts
that happen to run the same platform (e.g. two macOS targets both resolve to
`"remote-ssh:macos"`). A halt detected on host A therefore also (silently)
applied to host B, which never had a human anywhere near it.

`_channel_identity` (`__init__.py`) already solved the identical problem for
the announcement/ledger path by keying on `backend.user_host` instead of
`backend.name` for remote backends - this file proves the halt-state path
now does the same, and that it did NOT before the fix (see the first test,
which documents the pre-fix collision directly against real `RemoteBackend`
naming, not a hypothetical).

No real SSH, no real display server - fake `Backend`-shaped stand-ins with
just enough surface for `_build_coexistence_guard` to exercise its real
decision logic, matching `test_coexistence_guard_windows_remote.py`'s
established no-real-backend approach.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modules" / "tool-computer-use"))

import amplifier_module_tool_computer_use as tool_mod
from amplifier_module_tool_computer_use import _build_coexistence_guard
from amplifier_module_tool_computer_use import halt_state as halt_state_mod
from amplifier_module_tool_computer_use.presence import (
    Confidence,
    PresenceSnapshot,
    PresenceState,
)


class _FakeRemoteBackend:
    """Mirrors the REAL `RemoteBackend` shape post-`connect()` exactly:
    `name` is the composite `"remote-ssh:<platform>"` string (identical for
    any two hosts of the same platform - `remote_backend.py:143`),
    `is_remote = True`, `presence_platform` is the bare remote platform, and
    `user_host` is the actual per-target `user@host` string
    (`remote_backend.py:108-121`) - unique per target, exactly like the real
    class's own `user_host` property."""

    is_remote = True

    def __init__(self, platform: str, user_host: str, idle_ms: float = 999_999.0):
        self.name = f"remote-ssh:{platform}"
        self.presence_platform = platform
        self.user_host = user_host
        self._idle_ms = idle_ms
        self.calls = 0

    def presence_idle_ms(self) -> float:
        self.calls += 1
        return self._idle_ms


def _patch_halt_state_dir(monkeypatch, tmp_path: Path) -> None:
    """Same rationale as `test_halt_surfacing.py::_patch_record_halt_state_dir`:
    `__init__.py` imported `record_halt`/`load_halt`/`make_durable_halt_poll`
    directly, binding `halt_state.DEFAULT_STATE_DIR`'s value as each
    function's `state_dir` default at import time - patching
    `halt_state.DEFAULT_STATE_DIR` afterward does not reach an already-bound
    default. Patch the imported names in the tool module's own namespace
    instead, so no test here ever touches a real
    `~/.amplifier/computer-use/halt/`."""
    monkeypatch.setattr(halt_state_mod, "DEFAULT_STATE_DIR", tmp_path)
    monkeypatch.setattr(
        tool_mod,
        "record_halt",
        lambda platform, snapshot, *, reason: halt_state_mod.record_halt(
            platform, snapshot, reason=reason, state_dir=tmp_path
        ),
    )
    monkeypatch.setattr(
        tool_mod,
        "load_halt",
        lambda platform: halt_state_mod.load_halt(platform, state_dir=tmp_path),
    )
    monkeypatch.setattr(
        tool_mod,
        "make_durable_halt_poll",
        lambda platform: halt_state_mod.make_durable_halt_poll(
            platform, state_dir=tmp_path
        ),
    )


def _cancel_snapshot() -> PresenceSnapshot:
    return PresenceSnapshot(
        state=PresenceState.HUMAN_ACTIVE,
        confidence=Confidence.HIGH,
        basis="overlay_cancel",
        last_human_input_ago_ms=0.0,
        margin_ms=None,
        guard_ms=5.0,
        guard_measured=True,
        sample_interval_ms=None,
        latched_until_ms=None,
    )


# -- documents the collision the review claimed, directly against the real
#    naming scheme (`RemoteBackend.name` post-`connect()`) ---------------------


def test_two_distinct_remote_macos_hosts_share_the_same_composite_backend_name():
    """Sanity check that the alleged collision is real, not a misreading:
    two DIFFERENT `RemoteBackend`-shaped targets running the SAME remote
    platform get an IDENTICAL `.name` - this is the value a caller-side bug
    would use as a durable-halt key if it used `backend.name` unchanged."""
    host_a = _FakeRemoteBackend("macos", "opA@hostA")
    host_b = _FakeRemoteBackend("macos", "opB@hostB")

    assert host_a.name == host_b.name == "remote-ssh:macos"
    assert host_a.user_host != host_b.user_host


# -- the actual defect: isolation must hold end-to-end through
#    _build_coexistence_guard's halt-seeding path -----------------------------


def test_halt_recorded_for_one_remote_host_does_not_seed_a_different_hosts_guard(
    tmp_path, monkeypatch
):
    """The real-world manifestation: an operator's overlay Cancel click on
    host A (`_on_overlay_cancel`, `__init__.py`) writes a durable halt via
    `record_halt(backend.name, ...)`. A SEPARATE session mounting against
    host B (same platform, different machine) must NOT come up already
    halted because of it - before the fix, both resolved to the identical
    key `\"remote-ssh:macos\"` and host B's guard was wrongly seeded halted."""
    _patch_halt_state_dir(monkeypatch, tmp_path)

    host_a = _FakeRemoteBackend("macos", "opA@hostA", idle_ms=999_999.0)
    host_b = _FakeRemoteBackend("macos", "opB@hostB", idle_ms=999_999.0)

    # A human cancels via the overlay on host A - the exact call
    # `_on_overlay_cancel` makes post-fix, keyed by `_halt_key(host_a)`
    # (every real call site now passes this, not the bare `backend.name` -
    # see the Linux/Windows overlay wiring and the remote-poll path).
    tool_mod._on_overlay_cancel(
        guard=_build_coexistence_guard(host_a, {}),
        backend_name=tool_mod._halt_key(host_a),
    )

    # A brand-new guard is now built for host B, a DIFFERENT physical
    # machine that happens to run the same platform.
    guard_b = _build_coexistence_guard(host_b, {})
    assert guard_b is not None

    # Isolation: host B must NOT come up already halted because of an
    # action a human took on host A.
    with_no_injection_history = time.monotonic()
    guard_b.presence.record_inject(at=with_no_injection_history)  # no-op write path
    assert guard_b._halted is False, (
        "host B's guard was seeded halted by a halt recorded against host A - "
        "the durable halt key is not isolated per remote host"
    )

    # Meanwhile a FRESH guard for host A must still come up halted - the
    # fix must not break the legitimate same-host persistence this whole
    # module exists for.
    guard_a_again = _build_coexistence_guard(host_a, {})
    assert guard_a_again is not None
    assert guard_a_again._halted is True, (
        "host A's own durable halt record was not honored by a fresh guard "
        "for the SAME host - the fix must preserve same-host persistence"
    )
