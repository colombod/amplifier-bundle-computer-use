"""Defect A/C fix (docs/designs/coexistence.md §6.0/§7.6, C1 acceptance item 6):

`coexistence.enabled: false` used to remove the ENTIRE coexistence layer -
the halt invariant, pause, target binding, and geometric exclusion - by
returning `None` from `_build_coexistence_guard`, at `logger.info`, with no
consumer anywhere. That directly contradicted §6.0 ("no configuration key
disables [the halt]") and made C1's acceptance item 6 ("the §6.0 halt
invariant cannot be disabled by any configuration key - verified by
attempting it") false.

`coexistence.announce: false` had the parallel, less severe problem:
disclosure alone could be silently declined, and because `_ensure_announced`
only fires on this session's FIRST REAL ACTION (not `mount()` - see that
method's own docstring for why), a declined disclosure surfaced only as an
ordinary-looking `ToolResult(success=False)` on whatever action happened to
run first - indistinguishable from any other recoverable tool error.

This file proves, for BOTH keys:

1. The guard (halt/pause/binding/exclusion) is now built UNCONDITIONALLY
   whenever a backend structurally supports presence detection - no config
   key can prevent that. This is the direct, executable proof for C1 item 6.
2. What legitimate effect the keys retain - declining disclosure only - is
   gated by real-time presence, refused loudly (not silently) when a human
   is already detected, and enforced AT MOUNT, not merely reachable through
   `_build_announcement`/`execute()`.

Every test in section 1 and the mount-time tests in section 3 FAIL against
the pre-fix code (`enabled: False` returned a `None` guard; there was no
mount-time disclosure refusal at all).
"""

from __future__ import annotations

import asyncio
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modules" / "tool-computer-use"))

import amplifier_module_tool_computer_use as cu
import pytest
from amplifier_core.testing import MockCoordinator
from amplifier_module_tool_computer_use.backend import BackendError, ScreenGeometry
from amplifier_module_tool_computer_use.coexistence_guard import (
    CoexistenceGuard,
    HaltedError,
)
from amplifier_module_tool_computer_use.presence import (
    IdleUnreadableError,
    PresenceMonitor,
)


class FakeClock:
    """Same shape as the fixture in test_coexistence_guard.py/test_halt_invariant.py."""

    def __init__(self, start_idle_ms: float = 999_999.0) -> None:
        self.now = 1000.0
        self.last_input_at = self.now - (start_idle_ms / 1000.0)

    def advance(self, seconds: float) -> None:
        self.now += seconds

    def touch(self) -> None:
        self.last_input_at = self.now

    def idle_ms(self) -> float:
        return (self.now - self.last_input_at) * 1000.0


class _FakeBackendWithPresence:
    """A minimal backend exposing `presence_idle_ms` on `linux-x11` so
    `_build_coexistence_guard` builds a real guard - just enough shape for
    `mount()` and one `screenshot` action, matching
    `tests/test_double_mount_defect.py`'s `_FakeLocalBackend`.
    """

    is_remote = False
    name = "linux-x11"

    def __init__(self, clock: FakeClock) -> None:
        self.clock = clock
        self.closed = False

    def presence_idle_ms(self) -> float:
        return self.clock.idle_ms()

    def type_text(self, text: str) -> None:
        """`ComputerTool.__init__` inspects this signature."""

    def screen_geometry(self) -> ScreenGeometry:
        return ScreenGeometry(width=1920, height=1080)

    def list_monitors(self):
        raise BackendError("no monitor enumeration on this fake")

    def capture_scaled(self, region, size, max_edge, max_pixels) -> str:
        return _tiny_png_b64()

    def get_clipboard(self) -> str:
        return ""

    def close(self) -> None:
        self.closed = True


def _tiny_png_b64() -> str:
    import base64

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (2, 2)).save(buf, format="PNG")
    return base64.standard_b64encode(buf.getvalue()).decode()


class _RecordingCoordinator(MockCoordinator):
    def __init__(self) -> None:
        super().__init__()
        self.tools_by_name: dict[str, object] = {}

    async def mount(self, mount_point, module, name=None):
        await super().mount(mount_point, module, name=name)
        if mount_point == "tools":
            self.tools_by_name[name or module.name] = module


# == 1. _build_coexistence_guard: the guard is now unconditional ============


@pytest.mark.parametrize("key", ["enabled", "announce"])
def test_config_key_no_longer_prevents_the_guard_from_being_built(key: str):
    """FAILS WITHOUT THE FIX: `_build_coexistence_guard` used to return
    `None` for `coexistence.enabled: false`, removing halt/pause/binding/
    exclusion outright. `announce` never controlled guard construction
    (sanity check, parametrized alongside `enabled` for symmetry)."""
    clock = FakeClock(start_idle_ms=999_999.0)
    backend = _FakeBackendWithPresence(clock)
    cfg = {"coexistence": {key: False}}

    guard = cu._build_coexistence_guard(backend, cfg)

    assert guard is not None, (
        f"coexistence.{key}: false must not prevent the coexistence guard "
        "(halt/pause/target-binding/exclusion) from being built - "
        "docs/designs/coexistence.md §6.0"
    )


@pytest.mark.parametrize("key", ["enabled", "announce"])
def test_halt_still_fires_with_the_key_set_false_this_is_c1_item_6(
    monkeypatch, key: str
):
    """The direct, executable proof for C1 acceptance item 6: "the §6.0 halt
    invariant cannot be disabled by any configuration key - verified by
    attempting it." FAILS WITHOUT THE FIX: pre-fix, `guard` was `None` and
    this whole test would error on `guard.before_event()`.

    `before_event()` calls `PresenceMonitor.sample()` with no explicit clock
    argument (`coexistence_guard.py`'s only call site), so in real use
    `sample()` falls back to real `time.monotonic()` for the reconciliation
    instant. `FakeClock` here only fakes `idle_source` (via
    `_FakeBackendWithPresence.presence_idle_ms`) - it never controlled the
    real clock `sample()` reconciles the injection timestamp against. On a
    host whose real `time.monotonic()` happens to read below `clock.now`'s
    ~1000.0 baseline (any process with under ~1000s of monotonic uptime,
    e.g. a freshly booted CI runner), the margin comparison silently
    inverts and the sample classifies as QUIET instead of HUMAN_ACTIVE, so
    `before_event()` never halts - reproduced by simulating a low-uptime
    `time.monotonic()` (see the investigation that found this).
    `test_coexistence_guard.py::test_human_detected_mid_session_halts_and_releases`
    already established the fix for driving this exact real-clock path
    deterministically: monkeypatch the `presence` module's own
    `time.monotonic` to read the same `FakeClock`, so `sample()`'s
    real-clock fallback and `record_inject`'s explicit `at=clock.now`
    reconcile against ONE clock regardless of the host's actual uptime.
    """
    import amplifier_module_tool_computer_use.presence as presence_module

    clock = FakeClock(start_idle_ms=999_999.0)
    monkeypatch.setattr(presence_module.time, "monotonic", lambda: clock.now)
    backend = _FakeBackendWithPresence(clock)
    cfg = {"coexistence": {key: False}}

    guard = cu._build_coexistence_guard(backend, cfg)
    assert guard is not None

    # Drive a genuine human detection: record our own injection, then an
    # independent human touch, exactly like test_halt_invariant.py.
    guard.presence.record_inject(at=clock.now)
    clock.advance(0.030)
    clock.touch()

    with pytest.raises(HaltedError):
        guard.before_event()
    assert guard.halted is True


def test_drive_anyway_is_still_the_only_start_permission_knob_enabled_is_not(key=None):
    """`enabled: false` must not become a second `drive_anyway` - it has no
    effect on `check_start_permission()` either, since it no longer touches
    the guard at all."""
    clock = FakeClock(start_idle_ms=999_999.0)
    backend = _FakeBackendWithPresence(clock)
    cfg = {"coexistence": {"enabled": False}}

    guard = cu._build_coexistence_guard(backend, cfg)
    assert guard is not None
    assert guard.drive_anyway is False


# == 2. _disclosure_decline_reason / _refuse_if_disclosure_declined_... =====


@pytest.mark.parametrize("key", ["announce", "enabled"])
def test_disclosure_decline_reason_detects_either_key(key: str):
    assert cu._disclosure_decline_reason({key: False}) == key


def test_disclosure_decline_reason_none_when_neither_key_set():
    assert cu._disclosure_decline_reason({}) is None
    assert cu._disclosure_decline_reason({"announce": True, "enabled": True}) is None


@pytest.mark.parametrize("key", ["announce", "enabled"])
def test_mount_time_check_refuses_when_human_present(key: str):
    """A first-ever sample with near-zero idle and no prior injection is
    HUMAN_ACTIVE by construction (presence.py's `_classify`, margin_ms=None
    branch) - see test_coexistence_guard.py's FakeClock fixture for the same
    reasoning."""
    clock = FakeClock(start_idle_ms=0.0)
    monitor = PresenceMonitor(idle_source=clock.idle_ms, platform="linux-x11")
    guard = CoexistenceGuard(presence=monitor, release_all=lambda reason: [])

    class _B:
        name = "linux-x11"

    reason = cu._refuse_if_disclosure_declined_with_human_present(
        {key: False}, guard, _B()
    )
    assert reason is not None
    assert key in reason
    assert "drive_anyway" in reason


@pytest.mark.parametrize("key", ["announce", "enabled"])
def test_mount_time_check_proceeds_when_nobody_present(key: str):
    clock = FakeClock(start_idle_ms=999_999.0)
    monitor = PresenceMonitor(idle_source=clock.idle_ms, platform="linux-x11")
    guard = CoexistenceGuard(presence=monitor, release_all=lambda reason: [])

    class _B:
        name = "linux-x11"

    reason = cu._refuse_if_disclosure_declined_with_human_present(
        {key: False}, guard, _B()
    )
    assert reason is None


def test_mount_time_check_is_a_noop_when_disclosure_not_declined():
    clock = FakeClock(start_idle_ms=0.0)  # would be "present" if checked
    monitor = PresenceMonitor(idle_source=clock.idle_ms, platform="linux-x11")
    guard = CoexistenceGuard(presence=monitor, release_all=lambda reason: [])

    class _B:
        name = "linux-x11"

    reason = cu._refuse_if_disclosure_declined_with_human_present({}, guard, _B())
    assert reason is None


def test_mount_time_check_is_a_noop_when_no_guard_exists():
    class _B:
        name = "some-backend"

    reason = cu._refuse_if_disclosure_declined_with_human_present(
        {"enabled": False}, None, _B()
    )
    assert reason is None


def test_mount_time_check_fails_safe_on_unreadable_idle():
    """§9.6's fail-safe direction (unreadable idle -> treat as present),
    applied here exactly as `_handle_channel_failure` already does."""

    def _boom() -> float:
        raise RuntimeError("idle counter unreadable")

    monitor = PresenceMonitor(idle_source=_boom, platform="linux-x11")
    guard = CoexistenceGuard(presence=monitor, release_all=lambda reason: [])

    class _B:
        name = "linux-x11"

    with pytest.raises(IdleUnreadableError):
        # Sanity: the monitor itself really does raise (not swallowed).
        monitor.sample()

    reason = cu._refuse_if_disclosure_declined_with_human_present(
        {"announce": False}, guard, _B()
    )
    assert reason is not None, "unreadable idle must fail SAFE (refuse), not proceed"


# == 3. End to end via the real mount() - Defect C's specific requirement ===
# "Any test you'd write must prove refusal at mount, not merely that
# _build_announcement returns None - a test reachable only through
# execute() proves nothing about mount-time behavior."


@pytest.mark.parametrize("key", ["announce", "enabled"])
def test_mount_refuses_outright_when_disclosure_declined_and_human_present(
    monkeypatch, key: str
):
    """FAILS WITHOUT THE FIX: pre-fix, `mount()` had no disclosure check at
    all - it always mounted `computer`/`desktop` and the refusal (if any)
    only ever happened later, inside `_ensure_announced`, on the session's
    first real action. This proves the refusal happens INSIDE `mount()`
    itself: `computer`/`desktop` must never appear in the coordinator's
    mounted tools, and the stub explaining why must appear instead.
    """
    clock = FakeClock(start_idle_ms=0.0)  # human "present" on first sample
    backend = _FakeBackendWithPresence(clock)
    monkeypatch.setattr(cu, "select_backend", lambda cfg: backend)

    cfg = {"coexistence": {key: False}}
    coordinator = _RecordingCoordinator()
    asyncio.get_event_loop().run_until_complete(cu.mount(coordinator, cfg))

    assert "computer" not in coordinator.tools_by_name, (
        "mount() must refuse outright, not mount a live 'computer' tool "
        "that will only fail later on first use"
    )
    assert "desktop" not in coordinator.tools_by_name
    assert isinstance(
        coordinator.tools_by_name.get("computer_use_unavailable"),
        cu.ComputerUseUnavailableTool,
    )
    stub = coordinator.tools_by_name["computer_use_unavailable"]
    assert key in stub._reason
    assert "7.6" in stub._reason
    # The backend must be closed, not leaked, on a mount-time refusal.
    assert backend.closed is True


@pytest.mark.parametrize("key", ["announce", "enabled"])
def test_mount_proceeds_normally_when_declined_but_nobody_present(
    monkeypatch, key: str
):
    """The legitimate remaining use of both keys: on a target where nobody
    is currently at the console, disclosure is skipped exactly as before -
    but the guard (halt/pause/binding/exclusion) is still fully live, and
    the tool mounts and works normally."""
    clock = FakeClock(start_idle_ms=999_999.0)
    backend = _FakeBackendWithPresence(clock)
    monkeypatch.setattr(cu, "select_backend", lambda cfg: backend)

    cfg = {"coexistence": {key: False}, "read_only": True}
    coordinator = _RecordingCoordinator()
    asyncio.get_event_loop().run_until_complete(cu.mount(coordinator, cfg))

    assert set(coordinator.tools_by_name) == {"computer", "desktop"}
    computer_tool = coordinator.tools_by_name["computer"]
    assert computer_tool._coexistence_guard is not None, (
        "the guard (halt/pause/binding/exclusion) must still be built even "
        "when disclosure itself was declined"
    )

    exec_result = asyncio.get_event_loop().run_until_complete(
        computer_tool.execute({"action": "screenshot"})
    )
    assert exec_result.success is True
