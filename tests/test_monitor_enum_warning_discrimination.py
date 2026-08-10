"""Third-instance-of-a-defect-class fix: `_resolve_display_for_target`'s
(`__init__.py`) monitor-enumeration-unavailable fallback.

The reported shape, verbatim: a real X11 mount whose local backend mounts
successfully, but `Backend.list_monitors()` degrades - `RandR reported zero
active monitors` - printed TWICE (mount() runs this path once for
`amplifier_core`'s protocol-compliance probe and once for the real mount,
same as `test_double_mount_defect.py`), and unconditionally at WARNING even
when the backend can prove nothing is wrong (a genuinely headless/no-monitor
X11 session - verified live, see the report).

This file proves, with NO real X server:

1. The PROVEN-benign case (`MonitorEnumerationUnavailable(expected=True)`)
   never reaches the console at the default (WARNING) level.
2. A genuine anomaly, OR a backend that cannot make the determination at
   all (plain `BackendError`, `expected` defaults to `False`), still warns -
   exactly as loud as before this fix.
3. The log line - whichever level it lands at - fires at most once per
   physical channel per process (the double-mount duplication), reusing
   `_channel_registry_lock`/`_channel_identity`, the same mechanism
   `test_remote_latency_warning_dedup.py` already verifies for a different
   fact.
4. An explicit `target_monitor` (intent defeated) is never caught by this
   fallback at all - it raises, unconditionally, exactly as before.
"""

from __future__ import annotations

import logging
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modules" / "tool-computer-use"))

import amplifier_module_tool_computer_use as cu  # noqa: E402
from amplifier_module_tool_computer_use.backend import (  # noqa: E402
    BackendError,
    MonitorEnumerationUnavailable,
    MonitorInfo,
    ScreenGeometry,
)


def _unique(prefix: str) -> str:
    # `_monitor_enum_warned`/`_channel_ledgers` etc. are module-level,
    # process-wide caches that persist across tests in the same run (see
    # `test_retarget.py`'s own docstring for the same discipline) - every
    # backend name below must be unique so tests never dedupe against each
    # other's channel.
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


class _FakeBackend:
    """A local backend whose `list_monitors()` raises whatever `to_raise`
    is, on every call - real enough for `ComputerTool`/
    `_resolve_display_for_target` to exercise the real fallback/logging/
    dedup logic, with no real X server anywhere."""

    is_remote = False

    def __init__(self, name: str, to_raise: Exception) -> None:
        self.name = name
        self._to_raise = to_raise

    def type_text(self, text: str) -> None:
        """`ComputerTool.__init__` inspects this signature."""

    def screen_geometry(self) -> ScreenGeometry:
        return ScreenGeometry(1920, 1080, 0, 0)

    def list_monitors(self) -> list[MonitorInfo]:
        raise self._to_raise

    def close(self) -> None:
        pass


def _monitor_enum_records(records):
    return [r for r in records if "monitor enumeration unavailable" in r.message]


def _tool(
    backend: _FakeBackend, *, target_monitor_explicit: bool = False
) -> cu.ComputerTool:
    tool = cu.ComputerTool(backend, {})
    if target_monitor_explicit:
        tool._target_monitor_explicit = True
        tool._target_monitor = "some-specific-monitor"
    return tool


def test_expected_case_never_reaches_console_at_default_warning_level(caplog):
    """The PROVEN-benign (genuinely headless) case must not warn - proven by
    asserting nothing shows up even when only WARNING+ is captured (the
    default level any operator's console runs at)."""
    caplog.set_level(logging.WARNING, logger="amplifier_module_tool_computer_use")

    backend = _FakeBackend(
        _unique("linux-x11"),
        MonitorEnumerationUnavailable("zero active monitors", expected=True),
    )
    tool = _tool(backend)

    disp = tool.resolve_display()

    assert (disp.screen_width, disp.screen_height) == (
        1920,
        1080,
    )  # fell back correctly
    assert _monitor_enum_records(caplog.records) == [], (
        "the proven-benign/headless case must not reach the console at "
        "the default WARNING level"
    )


def test_expected_case_is_still_visible_at_debug_level(caplog):
    """Not silenced outright - still visible to anyone who turns logging up,
    same "state, not defeated ask" precedent `_mount_unavailable` already
    sets for a different mount-time condition (DEBUG, not gone)."""
    caplog.set_level(logging.DEBUG, logger="amplifier_module_tool_computer_use")

    backend = _FakeBackend(
        _unique("linux-x11"),
        MonitorEnumerationUnavailable("zero active monitors", expected=True),
    )
    tool = _tool(backend)
    tool.resolve_display()

    hits = _monitor_enum_records(caplog.records)
    assert len(hits) == 1
    assert hits[0].levelno == logging.DEBUG


def test_anomalous_case_still_warns_at_default_level(caplog):
    """A genuine anomaly (a monitor IS attached, RandR still failed) must
    stay exactly as loud as this warning has always been."""
    caplog.set_level(logging.WARNING, logger="amplifier_module_tool_computer_use")

    backend = _FakeBackend(
        _unique("linux-x11"),
        MonitorEnumerationUnavailable(
            "zero active monitors despite 1 CONNECTED output", expected=False
        ),
    )
    tool = _tool(backend)
    tool.resolve_display()

    hits = _monitor_enum_records(caplog.records)
    assert len(hits) == 1
    assert hits[0].levelno == logging.WARNING


def test_undecorated_backend_error_defaults_to_loud_unchanged(caplog):
    """A backend that cannot make the expected/anomaly determination at all
    (plain `BackendError`, e.g. `WindowsBackend`/`MacOSBackend` today) must
    behave EXACTLY as before this fix - loud, every time it's newly seen."""
    caplog.set_level(logging.WARNING, logger="amplifier_module_tool_computer_use")

    backend = _FakeBackend(_unique("windows-wsl2"), BackendError("no RandR here"))
    tool = _tool(backend)
    tool.resolve_display()

    hits = _monitor_enum_records(caplog.records)
    assert len(hits) == 1
    assert hits[0].levelno == logging.WARNING


def test_fires_at_most_once_per_channel_across_repeated_double_mount_calls(caplog):
    """The exact reported shape: printed twice for one real condition,
    because `mount()` runs `resolve_display()` once for the throwaway
    protocol-compliance probe and once for the real mount (both against the
    SAME physical channel/backend name) - must fire once between them, not
    once each."""
    caplog.set_level(logging.WARNING, logger="amplifier_module_tool_computer_use")

    name = _unique("linux-x11")
    # Two SEPARATE ComputerTool instances sharing the SAME backend `name`
    # (`_channel_identity` keys on `backend.name` for a local backend) -
    # mirrors two separate mount() calls against the same local machine.
    backend1 = _FakeBackend(
        name, MonitorEnumerationUnavailable("zero active monitors", expected=False)
    )
    backend2 = _FakeBackend(
        name, MonitorEnumerationUnavailable("zero active monitors", expected=False)
    )

    _tool(backend1).resolve_display()
    _tool(backend2).resolve_display()

    hits = _monitor_enum_records(caplog.records)
    assert len(hits) == 1, (
        f"expected exactly one log line across two mounts of the same "
        f"channel, got {len(hits)}: {[r.message for r in hits]}"
    )


def test_dedup_is_independent_per_channel_never_silenced_globally(caplog):
    """A genuinely different channel must still get its own log line - the
    fix dedups per-channel, not process-wide-forever."""
    caplog.set_level(logging.WARNING, logger="amplifier_module_tool_computer_use")

    backend_a = _FakeBackend(
        _unique("linux-x11"),
        MonitorEnumerationUnavailable("zero active monitors", expected=False),
    )
    backend_b = _FakeBackend(
        _unique("linux-x11"),
        MonitorEnumerationUnavailable("zero active monitors", expected=False),
    )

    _tool(backend_a).resolve_display()
    _tool(backend_b).resolve_display()

    hits = _monitor_enum_records(caplog.records)
    assert len(hits) == 2


def test_explicit_target_monitor_is_never_caught_by_this_fallback(caplog):
    """Intent defeated: an explicitly configured `target_monitor` must raise,
    unconditionally - never reach this fallback/logging path at all,
    regardless of `expected`."""
    caplog.set_level(logging.WARNING, logger="amplifier_module_tool_computer_use")

    backend = _FakeBackend(
        _unique("linux-x11"),
        MonitorEnumerationUnavailable("zero active monitors", expected=True),
    )
    tool = _tool(backend, target_monitor_explicit=True)

    try:
        tool.resolve_display()
        raised = False
    except BackendError:
        raised = True

    assert raised, "an explicit target_monitor must fail loud, never fall back silently"
    assert _monitor_enum_records(caplog.records) == [], (
        "the explicit-target path must never reach this fallback's logging - "
        "it raises before any of this code runs"
    )
