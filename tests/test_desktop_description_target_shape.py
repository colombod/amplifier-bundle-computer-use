"""The `config.target` SHAPE fact must reach `DesktopTool.description` -
this is the load-bearing surface for a real, forensically-confirmed failure:
a model asked to drive a named remote machine reasoned from tool-schema
silence (no per-call host parameter on either `computer` or `desktop`) all
the way to "there's no address to point at another machine ... this isn't a
networking gap I can close with config" - a plausible-sounding but WRONG
inference, because `ssh://`, `config.target`, and `remote_agent` occurred
zero times anywhere in that session's system prompt, tool schemas, or
messages.

Asserting existence ("remote is supported") would not have fixed this: it
contradicts what the schema visibly shows (no host parameter) and a model
reconciling prose against schema trusts the schema. The fix is a SHAPE fact
instead - the target is resolved once, at mount, from `config.target`, not
per call - shared verbatim (`registry._TARGET_MODEL`) between the one place a
human sees it today (`NoBackendAvailable`'s remediation text, `_REMEDIATION`,
seen only when computer-use fails to mount) and `DesktopTool.description`
(seen by the model on every successfully mounted session - `desktop` is an
ordinary tool with its own `input_schema`, never replaced by a provider's
native server-side `computer` tool block, so this text is one of the few
computer-use surfaces that reliably reaches the model on every dialect).

If this regresses - the fact silently drops out of the description string,
or `_REMEDIATION` and `DesktopTool.description` drift apart - the whole fix
reverts with no other signal. Hence a standalone, explicit assertion here.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modules" / "tool-computer-use"))

from amplifier_module_tool_computer_use import ComputerTool, DesktopTool
from amplifier_module_tool_computer_use.backend import MonitorInfo, ScreenGeometry
from amplifier_module_tool_computer_use.registry import (
    _TARGET_MODEL,
    NoBackendAvailable,
)


class _FakeBackend:
    """Bare minimum a `Backend` needs for `ComputerTool.__init__` +
    `resolve_display()` to succeed - not exercising any actual desktop
    control, since this test only inspects `.description` text."""

    name = "fake"
    is_remote = False

    def screen_geometry(self) -> ScreenGeometry:
        return ScreenGeometry(4, 4, 0, 0)

    def list_monitors(self):
        return [MonitorInfo(id="fake-0", x=0, y=0, width=4, height=4, primary=True)]

    def cursor_position(self) -> tuple[int, int]:
        return (0, 0)

    def type_text(self, text: str) -> None:  # pragma: no cover - unused
        pass

    def close(self) -> None:  # pragma: no cover - unused
        pass


def _make_desktop() -> DesktopTool:
    computer = ComputerTool(_FakeBackend(), {})
    computer.resolve_display()
    return DesktopTool(computer)


def test_desktop_description_names_config_target_and_ssh_scheme():
    """The exact wrong inference to pre-empt: no `config.target` name, no
    `ssh://` example, means a model has nothing to reconcile the schema's
    silence against."""
    description = _make_desktop().description

    assert "config.target" in description
    assert "ssh://user@host" in description


def test_desktop_description_states_absent_host_param_is_expected_shape():
    """The load-bearing sentence itself: the absence of a per-call host
    parameter must be explained as deliberate shape, not left for the model
    to (mis)read as evidence of a local-only limitation."""
    description = _make_desktop().description

    assert "no per-call host parameter" in description
    assert "not evidence" in description or "not local-only" in description.replace(
        "is not evidence this capability is local-only", "not local-only"
    )


def test_desktop_description_and_failure_remediation_share_the_fact_verbatim():
    """One fact, two audiences (`registry._TARGET_MODEL`): the failure path
    (`NoBackendAvailable`, read by an operator when mount fails) and the
    success path (`DesktopTool.description`, read by the model on every
    mounted session) must never drift apart - that drift is exactly how a
    true fact ends up reachable only when the capability is broken, which is
    the original bug this fix closes."""
    description = _make_desktop().description
    remediation_text = str(NoBackendAvailable([("fake", "unavailable")]))

    assert _TARGET_MODEL in description
    assert _TARGET_MODEL in remediation_text
