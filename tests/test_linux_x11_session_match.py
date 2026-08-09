"""Regression tests for the defect this fix closes: `LinuxX11Backend.probe()`
used to accept ANY reachable, XTEST-capable X server as "the" desktop, with
no check that it was actually the user's own interactive session. A stray
`Xvfb` left running from an earlier `CONTRIBUTING.md` ship-gate run (with
`DISPLAY` still exported in a shell nobody closed) satisfied every existing
check - `DISPLAY` non-empty, X connectable, XTEST present - identically to
the real desktop. Capture, click, and type would all "succeed" against the
wrong display with zero errors.

None of this touches a real X server - `linux_x11.xlib_display` and
`linux_x11._reference_session_display` are both faked, exactly the pattern
`test_announcement_wiring.py` and `test_registry.py` already use (see
CONTRIBUTING.md: "Tests must pass on Linux with no desktop present").
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modules" / "tool-computer-use"))

from amplifier_module_tool_computer_use import linux_x11
from amplifier_module_tool_computer_use.linux_x11 import LinuxX11Backend


class _FakeXlibDisplay:
    """Just enough of `Xlib.display.Display` for `probe()` to succeed."""

    def __init__(self, name: str) -> None:
        self.name = name

    def query_extension(self, _name: str) -> SimpleNamespace:
        return SimpleNamespace(present=True)

    def screen(self) -> SimpleNamespace:
        return SimpleNamespace(root=object())

    def close(self) -> None:
        pass


class _FakeXlibDisplayModule:
    """Stand-in for the `Xlib.display` module - `probe()` only ever calls
    `.Display(name)` on it."""

    def Display(self, name: str) -> _FakeXlibDisplay:  # noqa: N802 - Xlib's own casing
        return _FakeXlibDisplay(name)


def _install_fake_xlib(monkeypatch) -> None:
    monkeypatch.setattr(linux_x11, "xlib_display", _FakeXlibDisplayModule())
    monkeypatch.setattr(linux_x11, "_IMPORT_ERROR", None)


def test_probe_rejects_env_display_that_does_not_match_user_session(monkeypatch):
    """The core regression: a blindly-picked-up DISPLAY that differs from
    this user's own registered session display must be refused - and must
    be refused BEFORE ever touching a real X connection (no fake Xlib
    installed at all here; if the mismatch check did not fire first, this
    test would blow up on a real `Xlib.display.Display(':99')` call in a
    sandbox with no X server)."""
    monkeypatch.setattr(linux_x11, "_IMPORT_ERROR", None)
    monkeypatch.setattr(linux_x11, "_reference_session_display", lambda: ":1")
    monkeypatch.setenv("DISPLAY", ":99")

    backend = LinuxX11Backend({})  # no explicit config -> blind env pickup
    result = backend.probe()

    assert result.available is False
    assert result.reason is not None
    assert ":99" in result.reason
    assert ":1" in result.reason
    assert "does not match" in result.reason


def test_probe_accepts_env_display_that_matches_user_session(monkeypatch):
    """The real desktop's own DISPLAY, picked up blindly from the
    environment exactly like a real mount would, must still be accepted."""
    _install_fake_xlib(monkeypatch)
    monkeypatch.setattr(linux_x11, "_reference_session_display", lambda: ":1")
    monkeypatch.setenv("DISPLAY", ":1")

    backend = LinuxX11Backend({})
    result = backend.probe()

    assert result.available is True


def test_probe_accepts_env_display_when_no_session_reference_available(monkeypatch):
    """Honest edge: a headless CI box or container has no systemd --user
    session at all (or one that never exported DISPLAY) - there is nothing
    to compare against, so the blindly-picked-up DISPLAY must still be
    trusted rather than refused. This is the legitimate no-user-session
    case, not the accidental one."""
    _install_fake_xlib(monkeypatch)
    monkeypatch.setattr(linux_x11, "_reference_session_display", lambda: None)
    monkeypatch.setenv("DISPLAY", ":99")

    backend = LinuxX11Backend({})
    result = backend.probe()

    assert result.available is True


def test_probe_skips_session_match_check_for_explicit_display_config(monkeypatch):
    """`scripts/verify_coexistence.py` (and anything else that names
    `config["display"]` on purpose) is a DELIBERATE target, not an
    accidental one - it must never be refused just because it differs from
    whatever the interactive session happens to be. The reference lookup
    must not even be consulted for an explicit target."""
    _install_fake_xlib(monkeypatch)

    def _boom():
        raise AssertionError(
            "explicit config['display'] must not consult the session reference at all"
        )

    monkeypatch.setattr(linux_x11, "_reference_session_display", _boom)
    monkeypatch.setenv("DISPLAY", ":1")  # a real session IS present here

    backend = LinuxX11Backend({"display": ":99"})  # explicit, deliberate
    result = backend.probe()

    assert result.available is True


def test_reference_session_display_returns_none_when_systemctl_missing(monkeypatch):
    """No `systemctl` on PATH at all (a bare container) -> no reference,
    not a crash and not treated as a mismatch signal."""

    def _raise_file_not_found(*_args, **_kwargs):
        raise FileNotFoundError("systemctl not found")

    monkeypatch.setattr(linux_x11.subprocess, "run", _raise_file_not_found)

    assert linux_x11._reference_session_display() is None


def test_reference_session_display_returns_none_when_no_display_key(monkeypatch):
    """A reachable systemd --user manager that has simply never exported a
    DISPLAY (never had a GUI login) -> no reference, legitimate headless
    case."""

    class _Result:
        returncode = 0
        stdout = "HOME=/home/ci\nLANG=en_US.utf8\n"

    monkeypatch.setattr(linux_x11.subprocess, "run", lambda *a, **kw: _Result())

    assert linux_x11._reference_session_display() is None


def test_reference_session_display_parses_real_display_line(monkeypatch):
    """Sanity check of the parsing itself against real-shaped output."""

    class _Result:
        returncode = 0
        stdout = "HOME=/home/bkrabach\nDISPLAY=:1\nXDG_RUNTIME_DIR=/run/user/1000\n"

    monkeypatch.setattr(linux_x11.subprocess, "run", lambda *a, **kw: _Result())

    assert linux_x11._reference_session_display() == ":1"


def test_reference_session_display_returns_none_on_nonzero_exit(monkeypatch):
    """`systemctl --user` reachable but erroring (e.g. no bus for this
    user) -> no reference, not a mismatch."""

    class _Result:
        returncode = 1
        stdout = ""

    monkeypatch.setattr(linux_x11.subprocess, "run", lambda *a, **kw: _Result())

    assert linux_x11._reference_session_display() is None
