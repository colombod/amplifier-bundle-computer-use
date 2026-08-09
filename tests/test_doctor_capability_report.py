"""Unit tests: `desktop(action="doctor")` (Increment 1, M3 -
docs/designs/capability-awareness.md).

Three things this file proves, per the council's non-negotiable conditions:

1. `doctor` is structurally incapable of returning screen contents (\u00a75.4) -
   not "does not today", but "cannot", enforced by making every content
   method raise if `doctor` ever reaches it.
2. The action-surface report has a real fourth bucket
   (`blocked_by_os_permission`) distinct from `blocked_by_policy` - a
   confirmed macOS permission denial must never be reported as `works`.
3. `doctor` is dispatched BEFORE `_ensure_announced` (the disclosure-gate
   exemption), never after.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modules" / "tool-computer-use"))

import amplifier_module_tool_computer_use as cu  # noqa: E402
from amplifier_module_tool_computer_use import ComputerTool, DesktopTool  # noqa: E402
from amplifier_module_tool_computer_use.backend import (  # noqa: E402
    MonitorInfo,
    ScreenGeometry,
)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class _ContentTrap(RuntimeError):
    """Raised by a fake backend's content methods - proof `doctor` never
    called them, rather than merely "happening" not to call them."""


class _FakeBackend:
    """Minimal `Backend` double. Every method that could reveal screen
    CONTENT (as opposed to hardware geometry) raises `_ContentTrap` so a
    test can assert `doctor` never reaches it - the structural guard \u00a75.4
    requires, not a comment asserting one."""

    def __init__(
        self,
        name: str = "linux-x11",
        is_remote: bool = False,
        handshake: dict | None = None,
        presence_platform: str | None = None,
    ) -> None:
        self.name = name
        self.is_remote = is_remote
        # Mirrors `RemoteBackend`: `presence_platform` is the BARE remote
        # platform (e.g. "macos"), never the composite `name`
        # ("remote-ssh:macos") - see that class's own docstring.
        self.presence_platform = presence_platform
        self.handshake = handshake
        self.user_host = "user@host" if is_remote else None

    @property
    def handshake_age_seconds(self):
        return 1.5 if self.is_remote else None

    # -- allowed: hardware geometry, never content -----------------------
    def screen_geometry(self) -> ScreenGeometry:
        return ScreenGeometry(1920, 1080, 0, 0)

    def list_monitors(self):
        return [MonitorInfo(id="0", x=0, y=0, width=1920, height=1080, primary=True)]

    # -- forbidden for `doctor` to ever call - \u00a75.4 ----------------------
    def capture(self, region=None):
        raise _ContentTrap("capture() must never be called by doctor")

    def capture_scaled(self, *args, **kwargs):
        raise _ContentTrap("capture_scaled() must never be called by doctor")

    def cursor_position(self):
        raise _ContentTrap("cursor_position() must never be called by doctor")

    def list_windows(self):
        raise _ContentTrap("list_windows() must never be called by doctor")

    def get_clipboard(self):
        raise _ContentTrap("get_clipboard() must never be called by doctor")

    def type_text(self, text, guard=None):  # pragma: no cover - unused
        raise _ContentTrap("type_text() must never be called by doctor")

    def set_clipboard(self, text):  # pragma: no cover - unused
        raise _ContentTrap("set_clipboard() must never be called by doctor")

    def focus_window(self, handle):  # pragma: no cover - unused
        raise _ContentTrap("focus_window() must never be called by doctor")

    def close(self) -> None:  # pragma: no cover
        pass


def _make_desktop(backend: _FakeBackend, cfg: dict | None = None):
    computer = ComputerTool(backend, cfg or {})
    computer.resolve_display()
    desktop = DesktopTool(computer)
    return desktop, computer


# -- (1) structural guard: doctor cannot return screen contents --------------


def test_doctor_cannot_return_screen_contents():
    """`doctor` must never call `capture`/`capture_scaled`/`cursor_position`/
    `list_windows`/`get_clipboard` - the `_ContentTrap` fake makes each of
    those raise, so a passing, successful `doctor` call is direct proof none
    of them were reached, not an assumption."""
    backend = _FakeBackend()
    desktop, _computer = _make_desktop(backend)

    result = _run(desktop.execute({"action": "doctor"}))

    assert result.success is True
    report = json.loads(result.output)
    # Sanity: the report actually has real content, not an empty stub.
    assert "action_surface" in report
    assert "bound_target" in report


def test_doctor_output_contains_no_content_fields():
    """Belt-and-suspenders on the OUTPUT shape itself: no screenshot bytes,
    no window titles, no clipboard text, no cursor coordinates anywhere in
    the serialized report."""
    backend = _FakeBackend()
    desktop, _computer = _make_desktop(backend)

    result = _run(desktop.execute({"action": "doctor"}))
    output = result.output

    # Deliberately NOT checking for the substring "cursor" alone - the action
    # NAME "cursor_position" legitimately appears in the action-surface lists
    # (it is an action doctor reports ON, never one it calls). These check for
    # actual CONTENT fields a capture/clipboard/cursor read would produce.
    for forbidden in (
        "clipboard_text",
        "window_title",
        "png",
        "base64",
        "cursor_x",
        "cursor_y",
    ):
        assert forbidden not in output.lower()


# -- (2) the fourth bucket: OS-permission-denied != policy-blocked -----------


def test_remote_macos_confirmed_denied_accessibility_is_not_reported_as_works():
    """The council's exact scenario: a naive report could say `drag: works`
    while Accessibility is denied. This must land in
    `blocked_by_os_permission`, not `works`, and not `blocked_by_policy`."""
    handshake = {
        "ops": sorted(
            cu._ACTION_WIRE_OP[a] for a in cu._ACTION_WIRE_OP if cu._ACTION_WIRE_OP[a]
        ),
        "permissions": {"accessibility": False, "screen_recording": True},
    }
    backend = _FakeBackend(
        name="remote-ssh:macos",
        is_remote=True,
        handshake=handshake,
        presence_platform="macos",
    )
    desktop, _computer = _make_desktop(
        backend, {"read_only": False, "gate_writes": False}
    )

    result = _run(desktop.execute({"action": "doctor"}))
    report = json.loads(result.output)
    surface = report["action_surface"]

    assert "left_click_drag" in surface["blocked_by_os_permission"]
    assert "left_click_drag" not in surface["works"]
    assert "left_click_drag" not in surface["blocked_by_policy"]
    # screen_recording IS granted, so screenshot must NOT be in that bucket.
    assert "screenshot" not in surface["blocked_by_os_permission"]
    assert "screenshot" in surface["works"]


def test_remote_macos_denied_screen_recording_blocks_screenshot_not_drag():
    handshake = {
        "ops": sorted(
            cu._ACTION_WIRE_OP[a] for a in cu._ACTION_WIRE_OP if cu._ACTION_WIRE_OP[a]
        ),
        "permissions": {"accessibility": True, "screen_recording": False},
    }
    backend = _FakeBackend(
        name="remote-ssh:macos",
        is_remote=True,
        handshake=handshake,
        presence_platform="macos",
    )
    desktop, _computer = _make_desktop(
        backend, {"read_only": False, "gate_writes": False}
    )

    result = _run(desktop.execute({"action": "doctor"}))
    surface = json.loads(result.output)["action_surface"]

    assert "screenshot" in surface["blocked_by_os_permission"]
    assert "zoom" in surface["blocked_by_os_permission"]
    assert "left_click_drag" in surface["works"]


def test_policy_blocked_stays_distinct_from_os_permission_blocked():
    """read_only blocks MUTATING actions for a reason that has NOTHING to do
    with macOS permissions - a Linux target with read_only=True must show
    `drag` in `blocked_by_policy`, and `blocked_by_os_permission` must stay
    empty (Linux has no permission model at all)."""
    backend = _FakeBackend(name="linux-x11", is_remote=False)
    desktop, _computer = _make_desktop(backend, {"read_only": True})

    result = _run(desktop.execute({"action": "doctor"}))
    surface = json.loads(result.output)["action_surface"]

    assert "left_click_drag" in surface["blocked_by_policy"]
    assert surface["blocked_by_os_permission"] == {}
    assert "left_click_drag" not in surface["works"]


def test_unknown_permission_is_never_collapsed_into_denied():
    """\u00a73.4: an omitted/unknown permission key must NOT move an action into
    `blocked_by_os_permission` - only a CONFIRMED `False` does."""
    handshake = {
        "ops": sorted(
            cu._ACTION_WIRE_OP[a] for a in cu._ACTION_WIRE_OP if cu._ACTION_WIRE_OP[a]
        ),
        "permissions": {},  # both keys omitted - "could not determine"
    }
    backend = _FakeBackend(
        name="remote-ssh:macos",
        is_remote=True,
        handshake=handshake,
        presence_platform="macos",
    )
    desktop, _computer = _make_desktop(
        backend, {"read_only": False, "gate_writes": False}
    )

    result = _run(desktop.execute({"action": "doctor"}))
    report = json.loads(result.output)

    assert report["permissions"]["accessibility"] == "unknown"
    assert report["permissions"]["screen_recording"] == "unknown"
    assert report["action_surface"]["blocked_by_os_permission"] == {}
    assert "left_click_drag" in report["action_surface"]["works"]


def test_remote_op_not_in_handshake_is_not_carried_by_binding():
    """A remote agent whose handshake omits a wire op entirely must land
    that action in `not_carried_by_binding`, distinct from both policy and
    permission blocks."""
    handshake = {"ops": ["click", "move"], "permissions": {}}
    backend = _FakeBackend(
        name="remote-ssh:linux-x11", is_remote=True, handshake=handshake
    )
    desktop, _computer = _make_desktop(
        backend, {"read_only": False, "gate_writes": False}
    )

    result = _run(desktop.execute({"action": "doctor"}))
    surface = json.loads(result.output)["action_surface"]

    assert "left_click_drag" in surface["not_carried_by_binding"]
    assert "left_click" in surface["works"]


def test_windows_has_no_permission_model_applicable_false():
    backend = _FakeBackend(name="windows-wsl2", is_remote=False)
    desktop, _computer = _make_desktop(backend)

    result = _run(desktop.execute({"action": "doctor"}))
    report = json.loads(result.output)

    assert report["permissions"]["applicable"] is False


# -- (3) the disclosure-gate exemption ---------------------------------------


def test_doctor_bypasses_ensure_announced(monkeypatch):
    """`doctor` must be dispatched BEFORE `_ensure_announced` - proven by
    making that method raise if called at all, then asserting `doctor`
    still succeeds."""
    backend = _FakeBackend()
    _desktop, computer = _make_desktop(backend)

    def _boom():
        raise AssertionError("_ensure_announced must not be called for doctor")

    monkeypatch.setattr(computer, "_ensure_announced", _boom)
    desktop = DesktopTool(computer)

    result = _run(desktop.execute({"action": "doctor"}))

    assert result.success is True


def test_non_doctor_action_still_goes_through_the_gate(monkeypatch):
    """The exemption must be scoped to `doctor` only - every other desktop
    action must still hit `_ensure_announced` exactly as before."""
    backend = _FakeBackend()
    _desktop, computer = _make_desktop(backend)

    calls: list[str] = []
    original = computer._ensure_announced

    def _tracked():
        calls.append("called")
        return original()

    monkeypatch.setattr(computer, "_ensure_announced", _tracked)
    desktop = DesktopTool(computer)

    _run(desktop.execute({"action": "list_monitors"}))

    assert calls == ["called"]


# -- Wayland reporting --------------------------------------------------------


def test_local_linux_reports_wayland_as_unverified(monkeypatch):
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    backend = _FakeBackend(name="linux-x11", is_remote=False)
    desktop, _computer = _make_desktop(backend)

    result = _run(desktop.execute({"action": "doctor"}))
    display_server = json.loads(result.output)["display_server"]

    assert display_server["verified"] is False
    assert "wayland" in display_server["value"]


def test_local_linux_reports_x11_as_verified(monkeypatch):
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    backend = _FakeBackend(name="linux-x11", is_remote=False)
    desktop, _computer = _make_desktop(backend)

    result = _run(desktop.execute({"action": "doctor"}))
    display_server = json.loads(result.output)["display_server"]

    assert display_server == {
        "value": "x11",
        "verified": True,
        "note": "XDG_SESSION_TYPE=x11 - a native X11 session, not XWayland.",
    }


def test_display_server_none_for_macos_and_remote():
    backend = _FakeBackend(name="macos", is_remote=False)
    desktop, _computer = _make_desktop(backend)
    result = _run(desktop.execute({"action": "doctor"}))
    assert json.loads(result.output)["display_server"] is None

    remote_backend = _FakeBackend(
        name="remote-ssh:linux-x11",
        is_remote=True,
        handshake={"ops": [], "permissions": {}},
    )
    desktop2, _computer2 = _make_desktop(remote_backend, {"read_only": False})
    result2 = _run(desktop2.execute({"action": "doctor"}))
    assert json.loads(result2.output)["display_server"] is None
