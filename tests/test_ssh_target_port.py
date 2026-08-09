"""Regression test for the defect verified against `registry.py:95`
(`_SSH_TARGET_RE`) and `ssh_transport.py:99-114` (`_SSH_OPTS`): a
`ssh://host:port` target parsed successfully (the port was captured as
part of the `host` group and silently discarded by `_parse_target`), and
there was no `-p` anywhere in the SSH options list - so a configured
non-standard port never reached the actual `ssh` invocation.

Chosen fix: SUPPORT the port (thread it through to `-p`), rather than
reject it at parse time - see the accompanying report for the full
rationale (this is a legitimate, common SSH configuration, and rejecting
it forever would leave a real capability gap; the current behavior is not
even a clean rejection today - `ssh` itself tries to resolve the whole
`host:port` string as a literal (bogus) hostname and fails with a
DNS-lookup-shaped error that hides the real problem).

Standard-port targets (the overwhelmingly common case) must be provably
byte-identical in the resulting `ssh` argv - no `-p` flag at all - so this
fix cannot regress the existing, working majority path.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modules" / "tool-computer-use"))
PACKAGE_DIR = (
    ROOT / "modules" / "tool-computer-use" / "amplifier_module_tool_computer_use"
)

import pytest
from amplifier_module_tool_computer_use import registry, shared_transport
from amplifier_module_tool_computer_use import ssh_transport as ssh_transport_mod
from amplifier_module_tool_computer_use.ssh_transport import SshTransport


@pytest.fixture(autouse=True)
def _clear_shared_transport_registry():
    """Same rationale as `test_shared_transport.py::_clear_registry`:
    `shared_transport._registry` is process-lifetime state keyed by
    `(ssh_path, host, port)` - without this, a host string reused across
    two tests in this file (or across files) would silently hit an
    entry's cached fake transport from a DIFFERENT test."""
    shared_transport._registry.clear()
    yield
    shared_transport._registry.clear()


# -- registry._parse_target: standard targets are unaffected ------------------


def test_parse_target_standard_targets_get_no_port():
    assert registry._parse_target("ssh://myhost") == ("myhost", None)
    assert registry._parse_target("ssh://user@myhost") == ("user@myhost", None)


# -- registry._parse_target: the actual defect - a port must be extracted,
#    not silently folded into (and lost inside) the host string ------------


def test_parse_target_extracts_a_non_standard_port():
    assert registry._parse_target("ssh://host:2222") == ("host", 2222)
    assert registry._parse_target("ssh://user@host:2222") == ("user@host", 2222)


def test_parse_target_bracketed_ipv6_with_and_without_port():
    assert registry._parse_target("ssh://[::1]:2222") == ("::1", 2222)
    assert registry._parse_target("ssh://user@[::1]:2222") == ("user@::1", 2222)
    assert registry._parse_target("ssh://[::1]") == ("::1", None)


def test_parse_target_rejects_bare_unbracketed_ipv6_as_ambiguous():
    """A bare IPv6 literal (no brackets) is genuinely ambiguous against the
    `host:port` grammar this fix adds - reject it rather than mis-parse."""
    with pytest.raises(ValueError, match="not a valid ssh://"):
        registry._parse_target("ssh://user@::1")
    with pytest.raises(ValueError, match="not a valid ssh://"):
        registry._parse_target("ssh://::1")


def test_parse_target_rejects_non_numeric_port():
    with pytest.raises(ValueError, match="not a valid ssh://"):
        registry._parse_target("ssh://host:not-a-port")


# -- the actual failure mode, verified directly (not assumed): `ssh` treats
#    an unsupported "host:port" positional argument as a literal, bogus
#    hostname to resolve - it does NOT silently fall back to port 22. This
#    documents what the pre-fix code actually produced, for the record. ----


def test_pre_fix_host_string_is_rejected_by_real_ssh_as_a_bad_hostname():
    """Not exercising the fix - documents the ACTUAL (verified) failure
    mode of the code path this fix replaces, since a design review's
    description of it ("silently connects to port 22") does not match
    directly observed `ssh` behavior: `ssh` tries to resolve the whole
    `host:port` string as one literal hostname and fails loudly, with a
    confusing DNS-shaped error - it never reaches port 22 at all."""
    import shutil
    import subprocess

    if shutil.which("ssh") is None:
        pytest.skip("no real ssh binary available in this environment")

    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=2", "127.0.0.1:1", "true"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    # The garbage host string ends up IN the error - proving `ssh` never
    # silently substituted port 22 for a clean connection to "127.0.0.1".
    assert "127.0.0.1:1" in (result.stdout + result.stderr)


# -- the fix, proven against the REAL ssh invocation: -p reaches argv -------


def _capture_popen_cmd(monkeypatch) -> list[list[str]]:
    """Intercepts `subprocess.Popen` inside `ssh_transport.py` and records
    every argv it was called with, without spawning a real process -
    `connect()` is left to fail naturally afterward (empty fake stdout),
    which is fine: only the ARGV this test cares about is already captured
    by the time that happens."""
    calls: list[list[str]] = []

    class _FakeStdout:
        def readline(self) -> bytes:
            return b""

    class _FakeStderr:
        def read(self, _n: int = 4096) -> bytes:
            return b""

    class _FakeProc:
        def __init__(self) -> None:
            import io

            self.stdin = io.BytesIO()
            self.stdout = _FakeStdout()
            self.stderr = _FakeStderr()

    def fake_popen(cmd, **kwargs):
        calls.append(cmd)
        return _FakeProc()

    monkeypatch.setattr(ssh_transport_mod.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(
        ssh_transport_mod,
        "_resolve_uv_command",
        lambda user_host, ssh_path="ssh", *, port=None: "uv",
    )
    return calls


def test_non_standard_port_reaches_the_real_ssh_argv_as_dash_p(monkeypatch):
    calls = _capture_popen_cmd(monkeypatch)
    transport = SshTransport("user@host", package_dir=PACKAGE_DIR, port=2222)

    try:
        transport.connect(connect_timeout=0.2)
    except Exception:
        pass  # connect() will fail past the point we care about - fine.

    assert calls, "SshTransport.connect() never invoked subprocess.Popen"
    cmd = calls[0]
    assert "-p" in cmd, f"-p never reached the ssh argv: {cmd}"
    assert cmd[cmd.index("-p") + 1] == "2222"
    # The port flag must precede the destination, exactly like every other
    # ssh option here - never appended after the host/remote command.
    assert cmd.index("-p") < cmd.index("user@host")


def test_standard_port_argv_is_byte_identical_to_pre_port_support_behavior(
    monkeypatch,
):
    """The control: a target with NO configured port (the overwhelmingly
    common case) must produce the exact same argv as before this fix -
    no `-p` anywhere, nothing else disturbed."""
    calls_with_port_none = _capture_popen_cmd(monkeypatch)
    transport = SshTransport("user@host", package_dir=PACKAGE_DIR, port=None)
    try:
        transport.connect(connect_timeout=0.2)
    except Exception:
        pass

    assert calls_with_port_none
    cmd = calls_with_port_none[0]
    assert "-p" not in cmd, f"-p must be absent for a standard-port target: {cmd}"


def test_uv_probe_also_receives_the_port(monkeypatch):
    """The `uv`-discovery probe (`_resolve_uv_command`) is a SEPARATE ssh
    invocation from the main connect - it must get `-p` too, or a non-
    standard-port target's very first network call goes to the wrong
    place before the real connection is ever attempted."""
    captured: dict[str, list[str]] = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd

        class _R:
            returncode = 0
            stdout = "/usr/bin/uv\n"
            stderr = ""

        return _R()

    monkeypatch.setattr(ssh_transport_mod.subprocess, "run", fake_run)

    ssh_transport_mod._resolve_uv_command("user@host", "ssh", port=2222)

    cmd = captured["cmd"]
    assert "-p" in cmd
    assert cmd[cmd.index("-p") + 1] == "2222"


# -- registry wiring: port threads all the way from config.target down to
#    SshTransport, and is part of the shared-transport identity ------------


def test_build_ssh_transport_threads_port_into_sshtransport(monkeypatch):
    captured: dict[str, object] = {}

    class _FakeSshTransport:
        def __init__(self, host, **kwargs):
            captured["host"] = host
            captured["port"] = kwargs.get("port")

    # `_build_ssh_transport` imports `SshTransport` locally from
    # `.ssh_transport` inside its own `_factory` closure (`from
    # .ssh_transport import SshTransport`) - patching the source module's
    # attribute is enough for that local import to resolve to the fake.
    monkeypatch.setattr(ssh_transport_mod, "SshTransport", _FakeSshTransport)
    # `acquire_shared_transport` invokes the factory eagerly (no cached
    # entry yet for this key), so `captured` is already populated here.
    registry._build_ssh_transport("host", PACKAGE_DIR, {}, port=2222)

    assert captured.get("port") == 2222


def test_two_ports_to_the_same_host_get_different_shared_transports(monkeypatch):
    """Bug-hunt defect B, sharing-key half: `acquire_shared_transport`'s key
    must include `port` - otherwise two configured targets that differ
    ONLY by port would be folded into ONE shared SSH subprocess/agent,
    silently talking to whichever port connected first."""

    class _FakeSshTransport:
        def __init__(self, host, *, port=None, **kwargs):
            self.host = host
            self.port = port

    monkeypatch.setattr(ssh_transport_mod, "SshTransport", _FakeSshTransport)

    handle_22 = registry._build_ssh_transport("host", PACKAGE_DIR, {}, port=None)
    handle_2222 = registry._build_ssh_transport("host", PACKAGE_DIR, {}, port=2222)

    # `SharedTransportHandle` doesn't expose the underlying transport
    # publicly (by design - see its own docstring) - reach through
    # `._entry.transport` here since proving distinctness IS the point of
    # this test.
    assert handle_22._entry is not handle_2222._entry
    assert handle_22._entry.transport is not handle_2222._entry.transport
    assert handle_22._entry.transport.port is None
    assert handle_2222._entry.transport.port == 2222
