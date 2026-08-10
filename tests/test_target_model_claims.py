"""Guards against the SECOND instance of the disease `test_docs_capability_claims.py`
was built for (see that file's own docstring for the first: nine remote ops
claimed "Phase 2" for 27 commits after they were actually wired).

Here, `registry._TARGET_MODEL` and `context/computer-use-awareness.md` both
asserted the target machine is bound ONCE at mount and switching requires a
new session/restart - true when written, falsified by two features that
shipped after:

- `65f97b7` (M4 live re-target): `ComputerTool.retarget` (__init__.py:1533)
  re-binds an already-mounted session's target live, mid-session.
- `1b497ff` (self-configuring stub): `ComputerUseUnavailableTool._activate`
  (__init__.py:4988) binds and mounts real tools from a session where
  nothing mounted yet, also live, no restart.

Ground truth here is narrower than `_HANDLERS` (a dispatch table to diff a
whole list of ops against): there is only one behavioral claim, not a list,
so the check is existence-of-mechanism (does `retarget`/`_activate` still
exist as real methods) crossed with a stale-phrasing regex, not a table
diff. It still fails loud the same way: if the prose claims restart-only
binding while the live-rebind methods exist, that is exactly the drift
direction the original guard was built to catch - the docs UNDERSTATING an
agent's actual capability to a user.
"""

from __future__ import annotations

import re
from pathlib import Path

from amplifier_module_tool_computer_use import ComputerTool, ComputerUseUnavailableTool
from amplifier_module_tool_computer_use.registry import _TARGET_MODEL

ROOT = Path(__file__).resolve().parents[1]
AWARENESS_DOC = ROOT / "context" / "computer-use-awareness.md"

# Matches the family of stale phrasings this repo actually shipped in
# `_TARGET_MODEL` and computer-use-awareness.md before this fix: framing
# machine-switching as requiring a brand new session/restart rather than a
# call on an already-mounted (or not-yet-mounted) session.
RESTART_ONLY_CLAIM = re.compile(
    r"restart(ing)?\s+with\s+a\s+new\s+config\.target"
    r"|answerable only with a new session"
    r"|not a new argument to an existing call",
    re.IGNORECASE,
)


def test_ground_truth_live_retarget_mechanisms_still_exist():
    """If either of these disappears, the guard below is checking prose
    against ground truth that no longer exists in the code - that is a
    signal to re-derive this test (the binding model may have reverted to
    restart-only), not to silently delete it.
    """
    assert hasattr(ComputerTool, "retarget"), (
        "ComputerTool.retarget (live re-target, M4/65f97b7, "
        "__init__.py:1533) no longer exists - re-derive this guard, the "
        "binding-model claim it protects may no longer hold"
    )
    assert hasattr(ComputerUseUnavailableTool, "_activate"), (
        "ComputerUseUnavailableTool._activate (bootstrap activate, "
        "1b497ff, __init__.py:4988) no longer exists - re-derive this "
        "guard, the binding-model claim it protects may no longer hold"
    )


def test_target_model_and_awareness_doc_do_not_claim_restart_is_required():
    """Fails if `_TARGET_MODEL` or computer-use-awareness.md still claims
    switching machines needs a restart/new session, while the mechanisms
    that falsify that claim (`ComputerTool.retarget`, __init__.py:1533;
    `ComputerUseUnavailableTool._activate`, __init__.py:4988) exist in the
    running code - i.e. fails exactly when the docs and the code disagree.
    """
    docs = {
        "registry._TARGET_MODEL": _TARGET_MODEL,
        "context/computer-use-awareness.md": AWARENESS_DOC.read_text(encoding="utf-8"),
    }
    violations = [
        f"{name} claims restart/new-session is required to switch "
        "machines, but ComputerTool.retarget (__init__.py:1533) and "
        "ComputerUseUnavailableTool._activate (__init__.py:4988) both "
        "rebind live, mid-session, with no restart - the docs are stale, "
        "not the code."
        for name, text in docs.items()
        if RESTART_ONLY_CLAIM.search(text)
    ]
    assert not violations, "\n".join(violations)


def test_self_test_restart_only_claim_regex_matches_the_actual_historical_wording():
    """The instrument that would have caught this drift must be proven to
    fire on the exact wording that actually shipped - a regex that
    silently fails to match is indistinguishable from "no drift found".
    Reproduces the real stale sentences from `_TARGET_MODEL` and
    computer-use-awareness.md as they existed at 5e8e90d, before this fix.
    """
    stale_registry_sentence = (
        "Driving a different machine means restarting with a new "
        "config.target, not a new argument to an existing call."
    )
    stale_awareness_sentence = (
        'A user naming a different machine (by hostname, "my other '
        'computer", over Tailscale/VPN) is asking a `config.target` '
        "question, answerable only with a new session, not a limitation "
        "to report."
    )
    assert RESTART_ONLY_CLAIM.search(stale_registry_sentence), (
        "detector does not match the real historical registry.py wording - "
        "it would have silently passed on the actual defect"
    )
    assert RESTART_ONLY_CLAIM.search(stale_awareness_sentence), (
        "detector does not match the real historical awareness.md wording "
        "- it would have silently passed on the actual defect"
    )
