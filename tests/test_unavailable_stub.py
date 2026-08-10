"""Defect 2 fix: `mount()` must never leave a session silently without
computer-use - whatever the reason it could not obtain a working backend, a
`computer_use_unavailable` diagnostic tool is mounted instead, so the model
sees WHY in its own tool declarations (sent with every request) rather than
computer-use simply being absent with no trace.

Self-configuring fix (this file's second half): that tombstone used to log
ERROR for every branch, including the one that is a platform STATE (no
`target` configured, no local backend on this machine) rather than a
defeated ask - a technical user on a headless box saw that ERROR twice at
startup for a bundle they never asked to drive a desktop with. The silent/
loud split (`mount()`/`_mount_unavailable`) keeps every REAL failure
(`RemoteTargetUnavailable`, malformed config, disclosure declined with a
human present) exactly as loud as before, and stops paging a human for the
one case where nothing was asked for and nothing was denied. The stub also
gained three actions (`discover`/`activate`/`persist`) so an agent can point
computer-use at a machine without anyone hand-editing settings.yaml.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modules" / "tool-computer-use"))

import pytest
from amplifier_core.testing import MockCoordinator
from amplifier_module_tool_computer_use import ComputerUseUnavailableTool
from amplifier_module_tool_computer_use import mount as cu_mount
from amplifier_module_tool_computer_use.backend import ScreenGeometry
from amplifier_module_tool_computer_use.registry import NoBackendAvailable
from amplifier_module_tool_computer_use.remote_backend import RemoteTargetUnavailable


def _mounted_stub(coordinator: MockCoordinator) -> ComputerUseUnavailableTool:
    entries = [e for e in coordinator.mount_history if e["mount_point"] == "tools"]
    assert len(entries) == 1, f"expected exactly one tool mount, got {entries}"
    tool = entries[0]["module"]
    assert isinstance(tool, ComputerUseUnavailableTool)
    return tool


# == Silent branch: no target configured, no local backend on this platform ==
# A STATE, not a defeated ask - see the silent/loud comment block directly
# above `_mount_unavailable` in __init__.py.


@pytest.mark.asyncio
async def test_no_backend_available_mounts_a_visible_stub_silently(caplog, monkeypatch):
    import amplifier_module_tool_computer_use as cu

    def _raise(cfg):
        raise NoBackendAvailable([("linux-x11", "no DISPLAY")])

    monkeypatch.setattr(cu, "select_backend", _raise)
    coordinator = MockCoordinator()

    with caplog.at_level(logging.DEBUG):
        manifest = await cu_mount(coordinator, {})

    assert manifest["provides"] == ["computer_use_unavailable"]
    tool = _mounted_stub(coordinator)
    assert tool.name == "computer_use_unavailable"
    # The MODEL still learns why, on every request, via the stub's own
    # description - fail-loud to the one audience that can act on it.
    assert "no DISPLAY" in tool.description
    # But nothing at ERROR/WARNING reaches the human's console for this
    # branch - this is the actual defect this fix closes.
    assert not any(rec.levelno >= logging.WARNING for rec in caplog.records)


# == Loud branches: someone configured something and it was refused ==========


@pytest.mark.asyncio
async def test_malformed_target_mounts_a_visible_stub_loudly(monkeypatch, caplog):
    import amplifier_module_tool_computer_use as cu

    def _raise(cfg):
        raise ValueError("config.target='user@host' is not a valid ssh:// target")

    monkeypatch.setattr(cu, "select_backend", _raise)
    coordinator = MockCoordinator()

    with caplog.at_level(logging.ERROR):
        manifest = await cu_mount(coordinator, {"target": "user@host"})

    assert manifest["provides"] == ["computer_use_unavailable"]
    tool = _mounted_stub(coordinator)
    assert "invalid configuration" in tool.description
    assert "not a valid ssh://" in tool.description
    assert any(
        rec.levelno >= logging.ERROR and "NOT MOUNTING" in rec.message
        for rec in caplog.records
    )


@pytest.mark.asyncio
async def test_remote_target_unavailable_mounts_a_visible_stub_loudly(
    monkeypatch, caplog
):
    """The exact defect from the live repro: an explicitly configured
    `target:` that could not be reached used to raise `RemoteTargetUnavailable`
    straight out of `mount()` uncaught - which `amplifier_core._session_init`
    then swallows with a `logger.warning` and continues the session with
    nothing mounted and nothing in the model's context. `mount()` must now
    catch this itself and register the same visible stub - loudly, since a
    specific machine was asked for and not reached."""
    import amplifier_module_tool_computer_use as cu

    def _raise(cfg):
        raise RemoteTargetUnavailable(
            "no handshake from user@down-host within 30.0s "
            "(agent may have crashed during bootstrap)"
        )

    monkeypatch.setattr(cu, "select_backend", _raise)
    coordinator = MockCoordinator()

    with caplog.at_level(logging.ERROR):
        manifest = await cu_mount(coordinator, {"target": "ssh://user@down-host"})

    assert manifest["provides"] == ["computer_use_unavailable"]
    tool = _mounted_stub(coordinator)
    assert "no handshake" in tool.description
    assert any(
        rec.levelno >= logging.ERROR and "NOT MOUNTING" in rec.message
        for rec in caplog.records
    )


@pytest.mark.asyncio
async def test_unexpected_select_backend_exception_still_raises(monkeypatch):
    """Only the known "computer-use is not usable this session" exceptions
    degrade to the visible stub. Anything else is a real bug and must still
    fail loud, exactly as before this fix."""
    import amplifier_module_tool_computer_use as cu

    def _raise(cfg):
        raise RuntimeError("something actually broke")

    monkeypatch.setattr(cu, "select_backend", _raise)
    coordinator = MockCoordinator()

    with pytest.raises(RuntimeError, match="something actually broke"):
        await cu_mount(coordinator, {})

    assert coordinator.mount_history == []


@pytest.mark.asyncio
async def test_stub_execute_always_fails_honestly_and_never_hangs():
    tool = ComputerUseUnavailableTool("no backend available on this platform")
    result = await tool.execute({"action": "screenshot"})
    assert result.success is False
    assert result.error is not None
    assert result.error["type"] == "ComputerUseUnavailable"
    assert "no backend available" in result.error["message"]


def test_stub_name_is_distinct_from_the_real_tools():
    """Deliberately NOT named 'computer'/'desktop' - see the class docstring:
    reusing those names would blur "broken" with "never existed" and would
    also route this stub through hook-computer-use's `computer`/`desktop`
    pattern-matching (gate, halt-notice) with no reason to."""
    tool = ComputerUseUnavailableTool("reason")
    assert tool.name not in ("computer", "desktop")


# == Self-configuring: discover/activate/persist =============================


@pytest.mark.asyncio
async def test_discover_is_read_only_and_never_touches_the_coordinator(
    monkeypatch, tmp_path
):
    """discover must never mount/unmount/write anything - it only reads
    ~/.ssh/config, ~/.ssh/known_hosts, and asks the local tailscaled (never
    the candidate machines themselves)."""
    import amplifier_module_tool_computer_use as cu

    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()
    (ssh_dir / "config").write_text(
        "Host known-good\n    HostName 10.0.0.5\n    User alice\n\n"
        "Host wildcard-*\n    User bob\n",
        encoding="utf-8",
    )
    (ssh_dir / "known_hosts").write_text(
        "old-box ssh-ed25519 AAAAstuff\n|1|hashed|entry ssh-ed25519 AAAAstuff\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cu.Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setattr(shutil, "which", lambda name: None)

    tool = ComputerUseUnavailableTool("no backend available", coordinator=None)
    result = await tool.execute({"action": "discover"})

    assert result.success is True
    payload = json.loads(result.output)
    candidates = payload["candidates"]
    sources = {c["source"] for c in candidates}
    assert sources == {"ssh_config", "known_hosts"}

    ssh_cfg_candidate = next(c for c in candidates if c["source"] == "ssh_config")
    assert ssh_cfg_candidate["host_alias"] == "known-good"
    assert ssh_cfg_candidate["user"] == "alice"
    assert ssh_cfg_candidate["ambiguous_user"] is False
    assert ssh_cfg_candidate["suggested_target"] == "ssh://alice@10.0.0.5"
    # The wildcard Host block is not a concrete candidate.
    assert all(
        c["host_alias"] != "wildcard-*"
        for c in candidates
        if c["source"] == "ssh_config"
    )

    known_hosts_candidate = next(c for c in candidates if c["source"] == "known_hosts")
    assert known_hosts_candidate["hostname"] == "old-box"
    assert known_hosts_candidate["ambiguous_user"] is True
    # The hashed known_hosts entry is not resolvable to a hostname - skipped.
    assert all(c["hostname"] != "hashed" for c in candidates)


@pytest.mark.asyncio
async def test_discover_never_asserts_tailscale_owner_as_ssh_user(monkeypatch):
    """The real ambiguity this was built for: a tailnet reports node owner
    'bkrabach@github' while the actual working ssh user for that same host
    is 'brkrabac' - discover must report the tailscale candidate with
    user=None/ambiguous_user=True rather than guessing the owner is the
    login name."""
    import amplifier_module_tool_computer_use as cu

    fake_status = {
        "Peer": {
            "nodekey:abc": {
                "HostName": "brians-macbook-pro-os",
                "DNSName": "brians-macbook-pro-os.tail8f3c4e.ts.net.",
                "TailscaleIPs": ["100.91.24.67"],
                "UserID": 1,
                "Online": True,
                "OS": "macOS",
            }
        },
        "User": {"1": {"LoginName": "bkrabach@github"}},
    }

    class _FakeCompletedProcess:
        returncode = 0
        stdout = json.dumps(fake_status)
        stderr = ""

    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/tailscale")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _FakeCompletedProcess())
    monkeypatch.setattr(cu.Path, "home", staticmethod(lambda: Path("/nonexistent")))

    tool = ComputerUseUnavailableTool("no backend available")
    result = await tool.execute({"action": "discover"})

    payload = json.loads(result.output)
    ts_candidate = next(c for c in payload["candidates"] if c["source"] == "tailscale")
    assert ts_candidate["hostname"] == "brians-macbook-pro-os"
    assert ts_candidate["tailscale_owner"] == "bkrabach@github"
    assert ts_candidate["user"] is None
    assert ts_candidate["ambiguous_user"] is True


@pytest.mark.asyncio
async def test_activate_mounts_real_tools_and_unmounts_the_stub(monkeypatch):
    """The requirement-1 unlock: from a stub with no coordinator-side
    mount of computer/desktop, action=activate must build+mount the real
    tools AND remove the stub, using the SAME `_mount_backend` machinery
    `mount()` itself uses (no parallel path)."""
    import amplifier_module_tool_computer_use as cu

    class _FakeBackend:
        name = "fake-local"
        is_remote = False
        presence_idle_ms = None

        def close(self):
            pass

        def screen_geometry(self):
            return ScreenGeometry(width=1280, height=800)

        def list_monitors(self):
            raise cu.BackendError("no RandR monitors on this fake backend")

    monkeypatch.setattr(cu, "select_backend", lambda cfg: _FakeBackend())

    coordinator = MockCoordinator()
    stub = ComputerUseUnavailableTool(
        "no backend available", coordinator=coordinator, cfg={}
    )
    await coordinator.mount("tools", stub, name=stub.name)

    result = await stub.execute({"action": "activate"})

    assert result.success is True, result.error
    mounted_names = {
        e["name"] for e in coordinator.mount_history if e["mount_point"] == "tools"
    }
    assert {"computer", "desktop"} <= mounted_names
    unmounted_names = {
        e["name"] for e in coordinator.unmount_history if e["mount_point"] == "tools"
    }
    assert "computer_use_unavailable" in unmounted_names


@pytest.mark.asyncio
async def test_activate_reports_failure_honestly_and_keeps_the_stub(monkeypatch):
    import amplifier_module_tool_computer_use as cu

    def _raise(cfg):
        raise NoBackendAvailable([("linux-x11", "no DISPLAY")])

    monkeypatch.setattr(cu, "select_backend", _raise)
    coordinator = MockCoordinator()
    stub = ComputerUseUnavailableTool("no backend available", coordinator=coordinator)

    result = await stub.execute({"action": "activate", "target": "ssh://user@host"})

    assert result.success is False
    assert result.error["type"] == "NoBackendAvailable"
    # Never unmounted itself on a failed activate.
    assert coordinator.unmount_history == []


@pytest.mark.asyncio
async def test_activate_with_no_coordinator_fails_honestly():
    tool = ComputerUseUnavailableTool("no backend available")
    result = await tool.execute({"action": "activate"})
    assert result.success is False
    assert result.error["type"] == "ComputerUseUnavailable"


@pytest.mark.asyncio
async def test_persist_writes_only_the_target_key_and_preserves_everything_else(
    tmp_path,
):
    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text(
        "bundle:\n  app: []\nconfig:\n  providers:\n"
        "  - module: provider-anthropic\n    config:\n      api_key: x\n",
        encoding="utf-8",
    )

    import amplifier_module_tool_computer_use as cu

    result = cu._persist_target(  # noqa: SLF001 - testing the module fn directly
        "ssh://brkrabac@brians-macbook-pro-os", settings_path=settings_path
    )

    assert result.success is True
    payload = json.loads(result.output)
    assert payload["wrote"] == str(settings_path)
    assert "undo" in payload

    import yaml

    written = yaml.safe_load(settings_path.read_text(encoding="utf-8"))
    # Untouched.
    assert written["bundle"] == {"app": []}
    assert written["config"]["providers"][0]["config"]["api_key"] == "x"
    # New entry, correct shape.
    tool_entries = written["config"]["tools"]
    assert tool_entries == [
        {
            "module": "tool-computer-use",
            "config": {"target": "ssh://brkrabac@brians-macbook-pro-os"},
        }
    ]


@pytest.mark.asyncio
async def test_persist_is_idempotent_and_updates_in_place(tmp_path):
    settings_path = tmp_path / "settings.yaml"

    import amplifier_module_tool_computer_use as cu

    cu._persist_target("ssh://a@host-1", settings_path=settings_path)
    cu._persist_target("ssh://b@host-2", settings_path=settings_path)

    import yaml

    written = yaml.safe_load(settings_path.read_text(encoding="utf-8"))
    tool_entries = written["config"]["tools"]
    assert len(tool_entries) == 1
    assert tool_entries[0]["config"]["target"] == "ssh://b@host-2"


@pytest.mark.asyncio
async def test_persist_never_runs_as_a_side_effect_of_discover_or_activate(
    monkeypatch, tmp_path
):
    """The council's ruling, honored: discover/activate never write
    settings.yaml - only an explicit action=persist call does."""
    import amplifier_module_tool_computer_use as cu

    settings_path = tmp_path / "settings.yaml"
    monkeypatch.setattr(cu, "_amplifier_home", lambda: tmp_path)
    monkeypatch.setattr(shutil, "which", lambda name: None)
    monkeypatch.setattr(cu.Path, "home", staticmethod(lambda: tmp_path))

    tool = ComputerUseUnavailableTool("no backend available")
    await tool.execute({"action": "discover"})
    assert not settings_path.exists()

    class _FakeBackend:
        name = "fake-local"
        is_remote = False
        presence_idle_ms = None

        def close(self):
            pass

        def screen_geometry(self):
            return ScreenGeometry(width=1280, height=800)

        def list_monitors(self):
            raise cu.BackendError("no RandR monitors on this fake backend")

    coordinator = MockCoordinator()
    tool2 = ComputerUseUnavailableTool("no backend available", coordinator=coordinator)
    monkeypatch.setattr(cu, "select_backend", lambda cfg: _FakeBackend())
    await tool2.execute({"action": "activate"})
    assert not settings_path.exists()
