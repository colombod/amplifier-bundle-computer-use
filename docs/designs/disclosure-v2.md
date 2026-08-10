# Disclosure v2 — the shape of the indicator, the config that could turn it off, and the platform that has none

**Status:** Design proposal — **revision 2**, rewritten against a six-lens review that returned CONCERN on all six.
**Scope:** *What the disclosure control looks like*, *whether it can be switched off*, and *what macOS honestly gets*.
**Baseline:** `bbf3dcf`. The body was traced at `60bf7ef`; **exactly four files changed between the two** (`git diff --stat 60bf7ef bbf3dcf`: `CONTRIBUTING.md`, `docs/SETUP.md`, `linux_x11.py`, one new test file), so every claim citing those paths was re-traced at `bbf3dcf` and everything else cites unchanged code. That re-trace produced one new shipped fix (§2.1 S7) and corrected four stale line references. Revision 1 was written against `9b9d034`.
**Date:** 2026-08-08

**Authority this must not contradict:** `docs/designs/coexistence.md` §7.1, §7.3, §7.5, §7.6 — preserved unchanged. §7.1 is **strengthened**, not weakened, by this revision (§4.1).

**Authority this deliberately contradicts, with evidence, in two places.** Both are flagged rather than smuggled:
1. **§7.4's capture-based self-verification** — evidence in §6.4, retired in §6.5.
2. **coexistence.md §13's "Confirmed closed, not for decision: Agent-drawn macOS overlay — O2 tested it directly. Settled negative. Stop probing."** — **O2 is overturned.** §5 carries the probe transcript. This is the largest change in this revision and the one most worth attacking.

`docs/designs/band-lifetime.md` — **wholly preserved.** This document changes *what is drawn*. It does not touch *when it is raised or lowered*. §7.2-as-revised-by-band-lifetime (per driving episode), the channel-keyed `_ChannelBandState`, `_band_enter`/`_band_exit`, and the ledger clause all carry over verbatim (§4.6).

**Explicitly out of scope:** `coexistence_guard.py`, `presence.py`, `halt_state.py` — untouched by this design. Every change proposed below lives in `__init__.py`, `overlay_linux.py`, `overlay_windows.py`/`.ps1`, or `announce_macos.py`.

**The stability claim, re-derived at `bbf3dcf` rather than carried forward.** Revision 2 said *"untouched for fourteen consecutive commits."* **Fourteen is wrong.** It was copied out of an earlier commit message instead of being re-run — in a document whose entire thesis (§0.1) is that this is exactly what not to do. Re-derived, with the commands:

- Last commit to touch any of the three: **`fe5dcd3`** (`git log --oneline bbf3dcf -- <the three paths>`; `--full-history` over `fe5dcd3..bbf3dcf` returns nothing, so no touch is being hidden by history simplification).
- Commits since: `git rev-list --count fe5dcd3..bbf3dcf` = **21**. Linear — `--merges` = 0, `--first-parent` = 21 — so the count is unambiguous.
- Content: `git diff fe5dcd3 bbf3dcf --` over the three paths is **empty**. Byte-identical, not merely unmodified-in-spirit.
- What `fe5dcd3` did to them: **6 changed lines, every one inside a docstring** (`--numstat`: 1/1, 2/2, 3/3), rewriting `docs/X.md` → `docs/designs/X.md`. No statement, no signature, no constant.
- The last *functional* change is `e843248` (`resolve_resume_command`): `git rev-list --count e843248..bbf3dcf` = **28**, so 28 commits of behavioural stability.

**A trap worth naming, because it caught this correction on its first pass.** In `git log --oneline -- <paths>`, `e843248` appears *immediately* above `fe5dcd3`, which reads as "one commit earlier" and yields 22. It is not: that listing is filtered to commits touching those paths, and `git rev-list --count e843248..fe5dcd3` = **7**. **Adjacency in a path-filtered log is not adjacency in history.** Both numbers here come from `rev-list`, not from counting rows.

The property revision 2 was asserting holds, and holds more strongly than it claimed. The number attached to it did not. **21 at `bbf3dcf`** — and if this document is re-read at a later commit, re-run the command rather than editing the digit.

---

## 0. Recommendation, up front

**T0 is done and shipped at `60bf7ef` — this revision records what actually landed, including where it differs from what revision 1 recommended.**

**For the indicator: ship the tab alone. Do not ship the ring.** The tab carries the label and both stop controls — the entire §7.1 requirement. The ring carries neither, costs `SHAPE`/`WS_EX_TRANSPARENT` machinery on two of three platforms, introduces a new catastrophic failure mode (an unshaped full-screen frame), and its only benefit — peripheral salience — is **entirely unmeasured**. Revision 1 recommended the ring anyway. That was the same error the last two designs were failed for: an unmeasured constant carrying a design. Conceded in full (§9.1).

**For macOS: reopen it.** Revision 1 declared parity "not achievable with the mechanisms this bundle has" on the strength of probe O2. **O2 is wrong**, and I proved it today on real hardware: O2's negative was a *race*, not a wall (§5.1). An SSH-launched process can and does put real, composited pixels on the console user's physical display. macOS is not the platform with no indicator; it is arguably the *easiest* of the three.

| Tier | What | Gate | Status |
|---|---|---|---|
| **T0** | Disclosure cannot be removed by config | none | **SHIPPED `60bf7ef`.** §3 |
| **W-DPI** | Windows Pause/Cancel reachable at ≠100 % DPI | real-hardware before/after | **SHIPPED `60bf7ef`.** §2.1 S5 |
| **T1** | **Linux X11: replace the 36 px band with a labelled tab** | **L-GATE** (§4.4) — four items, including the human-eyes study. **Mechanical in form; enforced by discipline, not by CI — §8.1** | proposed |
| **T2** | **Windows: same tab** | **W-GATE** (§4.5) — now two items, not four; DPI is fixed | proposed |
| **T3** | **macOS: same tab** — newly possible | **M-GATE** (§5.4) | proposed |
| — | Perimeter ring | **deferred behind Q1.** Not scheduled. | §9.1 |

Ordering rationale: T0 closed the only defect where disclosure could be **absent while the agent drives**. T1–T3 close a defect where disclosure is **present but unlabelled and intrusive** — and on macOS, where it is *absent after the first dialog*. That is the severity ordering, and it is why T0 shipped alone and first.

### 0.1 The standing rule this revision exists to enforce

Both prior designs died the same death: **a confidently-stated safety claim that was never traced against current code.** Revision 1's §3.2 asserted that refusing at mount was "the same shape as the existing `NoBackendAvailable`/`AnnouncementRefused` handling in `mount()`." It was not — and revision 1's own §2.1 said so three paragraphs earlier. All six lenses caught it independently.

> **Every safety-mechanism claim in this document carries a `file:line` traced at `60bf7ef`. Where a claim could not be verified, it is marked UNVERIFIED and nothing is built on it.**

That rule is applied to §5's macOS reversal as hard as to anything else: the reversal rests on six probes run today, with raw output in §5.1, not on an argument.

---

## 1. Problem framing

Three complaints, one system. One of the three is now closed.

1. **The band occludes.** 36 px across the full width of the target monitor (`overlay_linux.py:54`, `BAND_HEIGHT = 36`), for the whole time an agent is driving, over every window's title bar / menu bar / tab strip. Externally reported as intrusive. **Open.**
2. **A config key could silently disable disclosure — and, worse, the halt.** **CLOSED at `60bf7ef`** (§3).
3. **macOS is not equivalent.** One modal dialog at session start, then nothing. **Open, and its premise has changed** (§5).

They were one design because they were the same question asked three ways: **what does the human at the machine actually perceive, for how long, and can anything make that perception go away?** With (2) closed, the remaining question narrows to *what is drawn, where, and on which platforms*.

### 1.1 The governing rule, and its three failure layers

> §7.1: *"an announcement that failed to render is a stop button the human cannot reach."*

band-lifetime §1.3 extended this to attention: *an announcement the human has learned to ignore is also a stop button they cannot reach.* Revision 1 added the third:

> **An announcement a config key removed is a stop button that was never built.**

Ranked by how badly each fails §7.1: config-removed > failed-to-render > ignored-as-furniture. **The worst layer is now closed.** A fourth layer, found by this review and not previously recorded, sits between the second and third:

> **An announcement that renders but whose click handler is dead is a stop button that looks reachable and is not.** This is live today on Linux — §6.3, `overlay_linux.py:242-243`.

---

## 2. What I verified, and what I did not

### 2.1 Shipped since revision 1 (`9b9d034` → `60bf7ef`) — re-read, not assumed

| # | What shipped | Where | Effect on this document |
|---|---|---|---|
| S1 | **`_build_coexistence_guard` no longer has an `enabled` short-circuit.** The function now returns `None` only for the two *capability* causes (no `presence_idle_ms`, platform absent from `GUARD_MS`). No config key can prevent the guard being built. | `__init__.py:2095` onward | **V3 is obsolete.** coexistence.md C1 acceptance item 6 is now true and has an executable proof (`tests/test_disclosure_config_keys.py`, 19 tests). |
| S2 | **`enabled` was kept, not deleted** — narrowed to a documented alias of `announce` that declines *session-start disclosure only*. | `_disclosure_decline_reason`, `__init__.py:2524` | **Revision 1's "delete both keys" recommendation is withdrawn.** §3.1 argues why the shipped shape is better than what I proposed. |
| S3 | **A real mount-time presence check.** Samples `guard.presence.sample()`; `IdleUnreadableError` is treated as *human present* (§9.6 fail-safe, matching `_handle_channel_failure`). | `_refuse_if_disclosure_declined_with_human_present`, `__init__.py:2548` | This is what "refuse at mount" actually means — see S4 for what it does *not* mean. |
| S4 | **`mount()` routes that refusal to `_mount_unavailable`**: `backend.close()`, `logger.error`, and a `ComputerUseUnavailableTool` stub mounted in place of `computer`/`desktop` so the model sees the refusal in its tool list. | `__init__.py:3069` → `_mount_unavailable` | Corrects revision 1's false claim — see §3.2. |
| S5 | **Windows DPI defect fixed.** `overlay_windows.ps1:123` calls `SetProcessDpiAwarenessContext(PER_MONITOR_AWARE_V2)` and `throw`s `DPI_AWARENESS_FAILED` if refused — no silent fallback. Verified on real hardware: before, Pause and Cancel sample points both read plain band colour `(184,134,11)`; after, band `(184,134,11)`, Pause `(85,85,85)`, Cancel `(164,30,30)`, each at its requested physical coordinate, and a synthetic click at Pause's physical centre produced `{"event":"pause"}` — reaching `OnMouseDown`'s hit-test, not inferred from corrected geometry. | `overlay_windows.ps1:120-131` | **V7 is closed.** Revision 1 made this a prerequisite for Windows. The prerequisite is met, and W-GATE shrinks accordingly (§4.5). |
| S6 | **All three coexistence keys are now documented** in the operator-facing config table. | `docs/SETUP.md:420-422` (was `:407-409` at `60bf7ef`; `bbf3dcf` added 13 lines above them) | **V2's "zero documentation" is obsolete.** This is the fact that makes deleting `enabled` a breaking change to a documented interface. |
| **S7** | **`LinuxX11Backend.probe()` accepted *an* X server as *the* user's desktop.** It checked python-xlib, a non-empty `DISPLAY`, a connection, and XTEST — all of which a stray `Xvfb` satisfies identically, so capture/click/type all "succeeded" against the wrong display **with zero errors**. `probe()` now compares a *blindly-picked-up* `DISPLAY` against `systemctl --user show-environment` and refuses on a known mismatch; an **explicitly configured** `display` is trusted as named and never consulted (that is how `scripts/verify_coexistence.py` drives `Xvfb` on purpose). An unavailable reference is trusted as-is — the honest headless/CI case. | `linux_x11.py:249` (`probe()`), `:274-291` (the check), `:123` (`_reference_session_display`); `tests/test_linux_x11_session_match.py` | **Relevant to this design twice.** (a) It is the *nearest miss* to E1: the same probe still has **no Wayland check**, so the failure mode S7 closed for a stray X server remains open for XWayland — §6.2 E1, Q8. (b) Root cause was partly **our own `CONTRIBUTING.md`**, which instructed a backgrounded `Xvfb` with no cleanup; an orphan was found alive, `ppid 1`, 6 days elapsed. A ship-gate instruction manufactured the hazard the probe then failed to detect. |

**Stated as the commit itself states it, not softened:** S5 was proven by invoking the `.ps1` directly with the exact arguments `overlay_windows.py` computes, **not** through a full session with a live model, and 100 %-scaled monitors were **not** run as a same-row control. That is a real residual gap and W-GATE item 2 exists to close it.

### 2.2 Still true at `60bf7ef` — re-read at this commit

| # | Finding | Where |
|---|---|---|
| V4 | `self._announcement is None` still conflates several distinct states. Two of them (`announce`/`enabled` decline) are now *also* surfaced at mount by S3/S4, so the conflation is less load-bearing than revision 1 described, but it is not gone. | `__init__.py:2620`, `:2632` |
| V5 | **The Linux band renders no text at all.** `_paint()` fills two rectangles; the module states the absence as a deliberate dependency choice — *"no font/text rendering dependency."* A human sees an amber strip with a grey box and a red box, unlabelled. **This is the single strongest argument for the tab and it is unchanged.** | `overlay_linux.py:58-64, 211-221` |
| V6 | **The Windows band swallows clicks across its entire strip.** The single-window replacement carries `WS_EX_NOACTIVATE \| WS_EX_TOPMOST \| WS_EX_TOOLWINDOW` and **no `WS_EX_TRANSPARENT`** — the script's own comment states clicks inside the strip but outside the buttons are swallowed, "a real, stated platform difference, not hidden." **And `overlay_windows.py`'s module docstring still describes the reverted three-window `WS_EX_TRANSPARENT` design as current.** That drift is unfixed. | `overlay_windows.ps1:175-182, 207-211` vs `overlay_windows.py:81` |
| V8 | **§7.4's occlusion self-verification still does not exist.** Zero hits for `occluded` in `modules/`; `PresenceSnapshot` still has no `announcement` field. | grep over `modules/`; `presence.py` |
| V9 | The band is scoped to the **target monitor**, not the virtual desktop. | `__init__.py:473-518`, `monitors.py` |
| V10 | `hide()`'s `Stop-Process` is bounded at `STOP_PROCESS_TIMEOUT_SECONDS = 15.0`; `show()`'s ready handshake is bounded by the constructor timeout. | `overlay_windows.py:193, 659` |
| V11 | Remote raise/lower asymmetry stands: no lower op crosses the wire. | `remote_agent.py` |
| **V12** | **`show()` maps before it shapes.** `self._window.map()` at `:151`, `_apply_input_shape()` at `:152`. Harmless for a 36 px band. Load-bearing for anything full-screen — see §9.1. | `overlay_linux.py:151-152` |
| **V13** | **The input shape covers the two button rects only**, and the exclusion registration covers exactly the same two rects. Everything else in the band — including any future label region — is input-transparent. | `overlay_linux.py:148-150, 200-209` |
| **V14** | **The overlay's event-poll thread exits silently on any unexpected exception.** Bare `except Exception: return`, no logging, no flag, no detection path. `self._shown` stays `True`; `_band_enter` keeps early-returning on it. The band stays on screen looking live; Pause and Cancel do nothing. | `overlay_linux.py:242-243` |
| **V15** | **Geometric exclusion is enforced at the injection call site, not in the overlay.** So V14 does *not* let the agent click its own controls — that safety property survives the poll thread's death. | `coexistence_guard.py:263` |
| **V16** | **Display geometry is resolved once, at mount, and cached.** Only `screen_info`'s explicit `refresh=True` and a `select_monitor` target switch ever re-resolve. **There is no RandR/display-change listener anywhere in the module.** | `__init__.py:473-487`, `:3044` |
| **V17** | **The Linux backend probe has no Wayland check.** It tests `DISPLAY`, an X connection, and XTEST — all three of which XWayland satisfies. `docs/SETUP.md:281-290` documents this and states the bundle "has **never verified input or capture under XWayland**, and makes no claim about it." **Still true at `bbf3dcf`, and now conspicuously so:** S7 taught `probe()` to interrogate *which* X server it found, and added no Wayland check while it was in there. Grep for `wayland` in `linux_x11.py` returns exactly one hit — `.mutter-Xwaylandauth`, an `XAUTHORITY` path candidate, not a check. | `linux_x11.py:249-314` (`probe()`, re-traced at `bbf3dcf`; was `:168-203` at `60bf7ef`); `docs/SETUP.md:221, 281-290` (unchanged) |

### 2.3 Probed on live hardware — Linux X11

Host `spark-1`, `DISPLAY=:1`, X.Org with GNOME/mutter compositing, 1024×768, python-xlib 0.33. Nothing in the repository was modified.

| # | Probe | Result |
|---|---|---|
| P1 | Is `SHAPE` available, and does `shape.SK.Bounding` exist? | **Yes.** SHAPE 1.1; `SK` exposes `Bounding`, `Clip`, `Input`. |
| P2 | Can one full-monitor override-redirect window be `Bounding`-shaped to a ring + tab and `Input`-shaped to the controls, shape applied **before** `map()`? | **Yes.** No protocol error on `sync()`. |
| P3 | Does the interior stay untouched? | **Yes.** Interior sample identical before, during, after (`(11,11,11)`). |
| P4 | Can `root.get_image()` read back the overlay's own pixels — i.e. is §7.4's self-verification implementable? | **No.** A plain **white** 400×300 override-redirect window sampled at its own centre returned `(29,29,29)`, the desktop background. A pixel check cannot distinguish "rendered" from "absent" on this desktop. |

P1–P3 remain valid and are what would make the ring buildable *if* Q1 ever justified it. They are not load-bearing for anything this revision proposes to ship: **the tab needs no `Bounding` shape at all.**

### 2.4 Probed on live hardware today — macOS

Host `brians-macbook-pro-os`, macOS 26.6 arm64, single 1728×1117 display at backing scale 2.0, console user `brkrabac` == the SSH user. Full transcript and interpretation in §5.1. No repository file was modified; every probe binary and capture was deleted from the target afterwards.

**What I could not verify, and will not pretend to:** whether *any* of these indicators is **noticeable to a distracted human**. That is Q1, it has never been run on any platform, and this revision makes it a **gate** rather than an epilogue (§4.4, §8).

---

## 3. The config decision — as shipped

**Shipped:** the coexistence guard is built unconditionally wherever the backend supports presence detection. `announce` and `enabled` both survive, both narrowed to declining session-start disclosure only, both gated by a real mount-time presence check: refuse loudly if a human is currently detected; proceed, loudly logged, if nobody is there.

**Revision 1 recommended deleting both keys and refusing to mount if either was present. That recommendation is withdrawn.** It was wrong on two of the three axes the two keys differ on.

### 3.1 Why the shipped shape beats what I proposed

The review's fourth finding was that `enabled` and `announce` were given one argument though they differ on three axes. Re-checked at `60bf7ef`, they do:

| Axis | `announce` | `enabled` |
|---|---|---|
| **Documentation status** | Documented at `docs/SETUP.md:421` | Documented at `docs/SETUP.md:420` — **and was documented, as a first-class key with different semantics, before this change** |
| **Enforcement timing** | Declines disclosure; nothing else | *Used to* prevent the guard existing at all — halt, pause, target binding, exclusion, in one boolean |
| **Operator consequence of deletion** | Low — the key only ever meant one thing | **High** — a headless/automation operator with `enabled: false` in a working config gets a hard mount failure with no equivalent |

Revision 1's "zero consumers means zero backward-compat burden" was measured against the *repository*, and the repository is not where operator config lives. `enabled` was documented, first-class, and the honest thing an operator would reach for on a machine nobody sits at. Deleting it strands exactly the population §7.6 was written to serve.

The shipped fix is strictly better than mine on the property that actually matters: **it separates the dangerous half from the legitimate half.** The dangerous half — a config key that could prevent the halt invariant existing — is gone, unconditionally, and cannot be reintroduced by any key. The legitimate half — an operator on an unattended machine declining a window nobody will look at — is preserved, and routed through the gate §7.6 already uses for a technically-failed channel. One defect closed; one working affordance kept. That is a smaller change than mine and a better one.

I record this as a design error on my part, not a scope difference. The instinct in the brief pointed the other way and the brief was right.

### 3.2 The claim that was false, and the corrected version

Revision 1 §3.2 said refusing to mount would be *"the same shape as the existing `NoBackendAvailable`/`AnnouncementRefused` handling in `mount()`."* **Half of that was false.** Traced at `60bf7ef`:

- `mount()` catches `NoBackendAvailable` (`__init__.py:3000`), `ValueError`/`TypeError`, and `RemoteTargetUnavailable`. Each routes to `_mount_unavailable`.
- `mount()` **does not catch `AnnouncementRefused` at all, and cannot** — `_ensure_announced` (`__init__.py:1063`) was deliberately moved out of `mount()` in `5b9ebbf` because the kernel calls `mount()` twice and the probe call was showing a real dialog to a real human for a tool that was about to be discarded. It now fires on the session's **first real action** (`__init__.py:1597`, `:1879`), where `AnnouncementRefused` becomes an ordinary-looking `ToolResult(success=False)`.

So "refuse at mount" and "`AnnouncementRefused`" were, at the time I wrote that sentence, opposite behaviours — and my own §2.1 table had recorded the `5b9ebbf` move three paragraphs earlier. I asserted a symmetry between a mechanism I had read and a mechanism I had not re-read.

**The shipped fix had to do real work to make the claim true**, and did: it added a genuine, side-effect-free presence sample in `mount()` itself (`__init__.py:2548`, called at `:3069`) rather than reusing the first-action gate.

**One sentence of revision 2 must come out here, because it is the same error one layer down.** Revision 2 wrote: *"`_build_announcement`'s own §7.6 policy still runs again, unchanged, at first use — the mount check closes the 'silent until first action' gap; it does not replace that gate."* That sentence was taken from `_refuse_if_disclosure_declined_with_human_present`'s own docstring rather than from the branch it describes. **Traced at `bbf3dcf`, it is false for the decline path.** `_build_announcement` reaches `_disclosure_decline_reason` at `__init__.py:2620` and, when a key declined, does exactly two things — `logger.info(...)` at `:2622` and `return None` — with **no presence sample at all**. §7.6's human-detected-vs-not judgement runs **once, at mount, and never again**. The corrected version, and its consequence, are §3.4.

**Corrected claim, traced:** a declined disclosure with a human present now produces `logger.error`, `backend.close()`, and a `ComputerUseUnavailableTool` stub in the model's tool list — the same shape as `NoBackendAvailable`, and *not* the same shape as `AnnouncementRefused`, which remains a first-action result by design.

### 3.3 What this deliberately does not fix

V4's conflation of `self._announcement is None` is real. A `DisclosureOutcome` enum naming which case occurred would be better than a `None`. **Not proposed.** The mount-time check now surfaces the two dangerous cases early and loudly; the rest are distinguished by their log lines; and inventing a type to carry a distinction nothing reads is the apparatus reflex. Recorded as an observation, not a task.

### 3.4 The QUIET floor — the decline gate's precision boundary

Two review lenses found this independently, from different angles, and revision 2 was silent on it. It is named here because a gap two readers can find and the document cannot is not an accepted risk; it is an unrecorded one.

**The mechanism, traced.** `_refuse_if_disclosure_declined_with_human_present` decides on one line: `human_present = snap.state is PresenceState.HUMAN_ACTIVE` (`__init__.py:2578`). Anything that is not `HUMAN_ACTIVE` — including `QUIET` at **HIGH** confidence — means "nobody is there," and `mount()` proceeds with disclosure declined. `_classify` reaches `QUIET`/`HIGH` off a single threshold: `QUIET_FLOOR_SECONDS = 2.0` (`presence.py:207`), applied at `presence.py:512-513` on the mount-time first sample (`margin_ms is None`, since nothing has been injected yet) and at `:520-521` thereafter.

**So the floor is two seconds.** A human sitting at the machine reading the screen, on their phone, or thinking, who has not touched a key or the mouse for 2.001 s, is classified `QUIET` at *high* confidence — not `UNKNOWN` — and an agent begins driving their desktop with **no on-screen indicator at all**. Two failures follow, and they are different:

1. **No notice.** The person is present and never told.
2. **No record.** The snapshot that made the call is not persisted anywhere the decision is later legible, and `HIGH` confidence is emitted for both the correctly-empty room and the still-human. Afterwards nothing distinguishes a true negative from a false one.

**And the mount-time sample is the only one.** Per §3.2, `_build_announcement`'s decline branch (`__init__.py:2620-2622`) logs and returns without sampling. Someone who walks up in the window between `mount()` and the first real action gets **zero** disclosure — not a stale check, no check.

#### 3.4.1 Why this is a disclosure-courtesy gap and not a §7.1 breach — verified, not asserted

The claim "the stop button stays reachable" was checked against the halt path rather than repeated:

- `CoexistenceGuard.before_event()` re-samples presence on **every** elementary injected event — `self.presence.sample()` at `coexistence_guard.py:249`, not once per action and not once per session.
- `if snap.state is PresenceState.HUMAN_ACTIVE:` at `:250` latches `_halted = True`; `:253-256` then `release_all("halted")` and raises `HaltedError`.
- **Confidence is never consulted on this path.** Only `state`. The QUIET floor's `HIGH`/`LOW` label cannot reach the halt decision — `presence.py:207`'s own comment says so: *"Purely a confidence label; it never gates the halt invariant."*
- The call sites are the real injection paths, not a wrapper: `__init__.py:953`, `linux_x11.py:674`, `macos.py:1179`.

**Consequence:** the still human's stop control is intact. The instant they touch the keyboard or trackpad, the next injected event samples `HUMAN_ACTIVE` and driving stops before it lands. That is the same mechanism §5.5's macOS interim text already promises out loud. **What they lose is the notice, not the control** — they are not told they *should* reach for it. Courtesy, not §7.1.

**The precision boundary, stated exactly.** The gap is bounded by all four of these holding at once, and closes if any one fails:
- `coexistence.announce` or `coexistence.enabled` is set `false` — the default is `true` on both, so this is off the shipped path entirely;
- **and** a human is present but has been input-idle for > 2.0 s at the moment of the mount sample;
- **and** the halt invariant is unaffected — it is, unconditionally, and `tests/test_halt_invariant.py` asserts it by construction;
- **and** the exposure ends at the human's first touch, not at some timer.

#### 3.4.2 Disposition: **accepted, not fixed**

Recorded rather than closed, for reasons that are on the record rather than implied:

- Raising `QUIET_FLOOR_SECONDS` trades one silent misclassification for the opposite one and has **no measurement** behind either value. Picking a new constant here is precisely the `T = 90 s` / `T = 6 px` pattern §0.1 exists to stop.
- Re-sampling at first action is a real candidate and a small one — but it narrows the window, it does not close it, and it is a change to the shipped decline path with no test articulating what it should do. **Not proposed here.**
- The population is opt-in: an operator who set a key to `false` on a machine they said nobody sits at.

**What is required of anyone who does touch it:** the honest form of the mount-time log line is *"presence sampled QUIET after N ms idle — mounting with disclosure declined"*, naming `last_human_input_ago_ms`, so a false negative is at least legible afterward. That is a strictly-additive log change, it invents no constant, and it makes item 2 above (no record) recoverable without touching item 1. **Recorded as the smallest honest improvement; not scheduled, and not a gate.**

---

## 4. The indicator

### 4.1 What is drawn — the tab, and only the tab

One indicator object per channel, replacing the 36 px band. **One window, one small rectangle.**

```
                    ┌────────────────────────────────────┐
                    │ AGENT DRIVING     [Pause] [Cancel] │   ← ~280 × 30
                    └────────────────────────────────────┘
   everything else on the screen is the human's own desktop, untouched
```

Three regions, three different behaviours, and the distinction is exact because the review found revision 1 fuzzy on it:

| Region | Pixels | Real human clicks | Agent's synthetic clicks |
|---|---|---|---|
| **Label text** | opaque | **pass through** (not in the Input shape) | permitted (not in the exclusion list) |
| **Pause rect** | opaque | consumed | **refused at the injection call site** |
| **Cancel rect** | opaque | consumed | **refused at the injection call site** |

This is exactly what `overlay_linux.py` does today (V13): the Input shape and the exclusion registration are built from the *same* two-element `_button_rects()` list, so they cannot drift. **Revision 1's §4.1 called the tab "the only opaque, only clickable, only click-excluded part" — three properties treated as one.** They are not the same property and the label region has only the first. The review was right to flag it; the table above is the fix, and it means the tab needs **no new shape code at all** on Linux — only different geometry fed to the call that already exists.

**Why the tab, and why it is not optional.** §7.1 requires the announcement to carry the stop control where the platform supports one; removing Pause/Cancel would weaken §7.1, which is forbidden. V5 is the second, independent reason: the band renders **no text today**, so a human who did not start anything sees a coloured shape with two unlabelled boxes and has no idea what it claims or what the boxes do. The label has to go somewhere, and the somewhere it goes is the same object as the controls. **One object, two jobs, no new concepts** — and, against today's band, one *fewer* concept, because the full-width strip disappears.

**§7.1 is strengthened, not weakened.** Today's Linux indicator has controls and no label. The tab has both. Today's Windows indicator swallows clicks across the whole screen width (V6); the tab swallows them across 280 px.

### 4.2 What the tab is *not*

It is not a "corner affordance." Revision 1 rejected that candidate for solving the controls and not the label; a tab is a corner affordance that also says what it is, in text, which is precisely the gap V5 names.

It is not a *reduced* ring. The ring is not descoped-for-now-and-then-added; it is **not scheduled**, and §9.1 states the condition under which it would be reconsidered.

### 4.3 Per-platform mechanism

#### Linux X11 — T1

Same override-redirect window class, same connection, same `ExclusionZone` registration, same `_poll_events` thread, same `SK.Input` call. What changes:

```
create_window(tab_x, tab_y, TAB_W, TAB_H, override_redirect=1)   # was: full-width × 36
shape_rectangles(SO.Set, SK.Input, …, [pause_rect, cancel_rect])  # unchanged call, new geometry
draw the label                                                    # NEW — the only new capability
```

**The label is the only genuinely new thing, and it is the one that costs a dependency.** `overlay_linux.py` states its no-text property as a deliberate choice: *"no font/text rendering dependency, keeping this module's only dependency the same Xlib the rest of the Linux backend already requires."* Text on X11 via python-xlib means either a core-font `PolyText8` (available on the existing connection, no new dependency, ugly, and **UNVERIFIED** — I did not probe whether a core font is present on a modern GNOME X server) or Xft/Pango (a real new dependency).

**This is the one place the tab is not free, and it is L-GATE item 1.** No constant, no font name, and no rendering path is specified here ahead of that probe. Revision 1 invented `T = 6 px` without measurement; this revision declines to invent a font.

**No shape-before-map hazard.** V12's ordering defect is real but it is only *catastrophic* for a full-screen window, where one unshaped frame is an opaque rectangle over the whole display. For a 280 × 30 window, one unshaped frame is a 280 × 30 window. The existing map-then-shape order is left exactly as it is. **This is a direct consequence of dropping the ring and it removes an entire class of failure from the design.**

#### Windows — T2

One `Form` at the tab's bounds, `WS_EX_NOACTIVATE | WS_EX_TOPMOST | WS_EX_TOOLWINDOW` as today. **No `WS_EX_TRANSPARENT`, and therefore no re-opening of the design the team already reverted.** V6's click-swallowing does not need a fix; it needs a smaller window. A 280 × 30 tab swallows clicks in 8,400 px². Today's band swallows them across `screen_width × 36` — 69,120 px² on a 1920-wide monitor, spanning the Start button, the tray, and every title bar it crosses. **The tab is an 88 % reduction in swallowed area and it achieves it by deleting code, not adding it.**

Label text is free on Windows: `OnPaint` already draws button labels via `System.Drawing`.

#### macOS — T3, newly possible

See §5. Mechanically the *simplest* of the three: one small opaque `NSWindow`, `.statusBar` level, `ignoresMouseEvents = false`, text via `NSAttributedString`. The cost is not the drawing; it is the AppKit dependency and the run loop (§5.3).

#### Remote — inherits the target platform's own tab

`_build_remote_announcement` dispatches to the target's own channel. V11's raise/lower asymmetry is **unchanged and out of scope** — band-lifetime §0.5's stated deferral, not reopened here.

### 4.4 L-GATE — the mechanical condition for Linux

The review's seventh finding was that revision 1 gave Windows a mechanical gate and Linux a prose one — the same asymmetry the previous design was failed for. Accepted without argument. Linux now has a gate of the same kind, and it is **blocking**:

> **On a real GNOME/X11 desktop, with the tab raised:**
> 1. **Text renders.** A pixel sample inside the label region differs from the tab background colour, and a photograph or capture shows legible glyphs. *(This is also the probe that decides the font mechanism — §4.3.)*
> 2. **Q4 — placement survives the shell.** With the tab at its chosen position, on GNOME/mutter: (a) a capture shows the tab's pixels present, not overpainted by the shell panel; (b) a real click at the Pause rect's centre invokes the pause handler. **Both, on the platform T1 ships on.** See §4.4.1.
> 3. **Nothing interactive is covered.** With the tab up, every OS-owned control it could overlap — panel, dock, tray, Activities — is still clickable by a human.
> 4. **Q1 — a human sees it.** Metric 5 (§8), run against a light desktop and a dark one: a person mid-task is interrupted; do they see the tab, and does it read as "an agent is driving"?

All four are blocking. Linux keeps the 36 px band until all four pass. Item 4 is a gate, not a signal — see §4.4.2.

#### 4.4.1 Why Q4 is a gate and not an open question

Three lenses converged on this independently and they are right. The chain is short and every link is documented:

- GNOME's shell panel may composite **above** an override-redirect window. U4 found this directly (a GNOME-Shell-composited polkit modal obscured a window `query_tree` confirmed topmost among client windows), and coexistence.md §7.4 is built on that finding.
- Linux X11 is the platform T1 ships on, **first**.
- The tab is the *only* opaque, labelled control in the entire redesign. Under the band, a covered button still left 36 px of amber strip to signal that something was there. Under the tab, if the tab is covered, **there is no indicator at all** — and by §7.1 that is a stop button the human cannot reach.

So the exact failure Q4 names would, on the first shipping platform, produce the exact outcome §7.1 forbids. That is not an epilogue item. Revision 1 wrote "I picked top-centre for the mock and **I cannot defend it**" and then shipped it as an open question anyway; the honest consequence of not being able to defend a placement is that placement is a gate.

**No placement is specified in this document.** L-GATE item 2 selects it.

#### 4.4.2 Human-eyes validation is a gate. Resolved.

Revision 1 said so in §0 and §10 and then called it a non-blocking "signal" in §8's metrics table. The review's third finding. **Resolved in favour of gate**, for the reason revision 1's own §7 gave and then ignored: *"The dominant tradeoff is safety-through-tolerability versus an unmeasured appearance claim, and it is decided by exactly one thing nobody has done: putting the indicator on a screen and looking at it."*

A design whose dominant tradeoff turns on one measurement cannot treat that measurement as optional. §8 is corrected to match.

### 4.5 W-GATE — the mechanical condition for Windows

S5 closed the DPI defect and with it two of revision 1's four W-GATE items. The ring's input-transparency item disappears with the ring. What remains:

> **On real Windows hardware at a display scaling factor ≠ 100 %, with the tab raised:**
> 1. A pixel sample inside the Pause rect returns the Pause colour and inside Cancel the Cancel colour, each distinct from the tab colour; the label region shows legible text.
> 2. A synthetic click at the centre of each rect appends the matching `{"event":"pause"}` / `{"event":"cancel"}` line to `overlay-events.ndjson` — **and the same run is repeated on a 100 %-scaled monitor as a same-row control**, which S5's own commit records as not having been done.

Two items, not four, because a shipped fix retired two of them and a dropped feature retired the third. That is what a gate is for.

### 4.6 What the tab explicitly does **not** change

- **Lifetime.** `_band_enter`/`_band_exit`, `_ChannelBandState`, the channel-keyed depth counter, the `ledger.held_tokens` clause, the re-check under lock. All verbatim. A second lifetime mechanism would re-open F8, which is closed and tested.
- **The consent gate.** `_ensure_announced`, the sticky refusal, `_announcement_decisions`. Untouched.
- **§7.5's exclusion split.** Only the two interactive rects are excluded, built from the same list as the Input shape (V13).
- **Bounded teardown.** `STOP_PROCESS_TIMEOUT_SECONDS`, the ready handshake bound (V10). Unchanged.
- **The map/shape order.** Left as-is (V12) — see §4.3.

---

## 5. The macOS decision — reopened

**Revision 1 said: "Parity is not achievable with the mechanisms this bundle has. I am not going to specify something that cannot be built." That verdict rested on probe O2, and O2 is wrong.**

The review's fifth finding was that the "impossible" verdict was SSH-only and generalised, and that a permanent parity gap must not rest on an untested generalisation. Accepted. **I probed it. The result is larger than the finding anticipated: the SSH case itself works.**

### 5.1 What I ran today, and what came back

Six probes on `brians-macbook-pro-os` (macOS 26.6, arm64, 1728×1117 @ 2.0, console user == SSH user `brkrabac`). Probes M1–M2 create nothing visible. M3–M6 put a small window on the display for under two seconds each, `.accessory` activation policy, `orderFront` (never `makeKeyAndOrderFront`), `ignoresMouseEvents = true` — **no focus steal, no input injected**. All binaries and captures deleted from the target afterwards.

**M1 — the SSH process's security session (read-only, no window).**
```
SessionGetInfo status=0 sid=0x186b8 bits=0x1
  sessionIsRoot=1  sessionHasGraphicAccess=0  sessionHasTTY=0  sessionIsRemote=0
CGSessionCopyCurrentDictionary = NULL   (no window-server session attached)
CGMainDisplayID = 1
```

**M2 — the same binary in the console user's Aqua session** (`launchctl bootstrap gui/501`, no window, no input):
```
SessionGetInfo status=0 sid=0x186b9 bits=0x2030
  sessionIsRoot=0  sessionHasGraphicAccess=1  sessionHasTTY=1
CGSessionCopyCurrentDictionary = non-NULL
    kCGSSessionOnConsoleKey = 1;  kCGSSessionUserIDKey = 501;  kCGSSessionUserNameKey = brkrabac;
CGMainDisplayID = 1
```

M1/M2 confirm the two contexts genuinely differ. **They also produce a precise negative worth recording: that difference does not predict what O2 measured.** See M3.

**M3 — O2's own test, re-run from SSH.** 1×1 `NSWindow`, `.accessory`, `.statusBar`, `orderFront`, run loop pumped 0.4 s, then `CGWindowListCopyWindowInfo(.optionOnScreenOnly)` filtered to own PID:
```
MATCH: kCGWindowIsOnscreen: 1, kCGWindowOwnerPID: 58444, kCGWindowLayer: 25,
       kCGWindowBounds: {X=400, Y=716, Width=1, Height=1}
O14 VERDICT: YES - window IS on the console user's desktop (matches=1)
```

**M4 — isolating the variable.** Twelve runs: activation policy ∈ {none, accessory, regular} × window level ∈ {normal, statusBar} × run loop ∈ {off, on}.
```
policy=none      level=normal    runloop=false  matches=0
policy=none      level=normal    runloop=true   matches=1
policy=none      level=statusBar runloop=false  matches=0
policy=none      level=statusBar runloop=true   matches=1
policy=accessory level=normal    runloop=false  matches=0
policy=accessory level=normal    runloop=true   matches=1
…  (regular ditto)                              …
```
**Every `runloop=true` gives `matches=1`. Every `runloop=false` gives `matches=0`. Activation policy and window level are irrelevant.**

> **M4 has no control, and the missing cell is the one that prices T3.** The matrix varies three factors and holds a fourth fixed by construction: `runloop=true` pumps the run loop **for 0.4 s** (M3), and `runloop=false` neither pumps nor waits. So `runloop` and *elapsed wall time before the query* move together in all twelve runs, and the design's conclusion — *"M4 proves the run loop is the load-bearing element"* (§5.3 cost 2) — is **not** what M4 measured. It is consistent with two hypotheses M4 cannot separate:
> - **H1 — the run loop must be pumped.** Then T3 needs a persistent `NSApplication` run loop, hence **a new thread** in the agent process. That is the cost §5.3 states, and it is the one thing that breaks §6.3's *"no new thread, no new lock, no new timer"* constraint.
> - **H2 — the window server needs ~0.4 s, by any mechanism.** Then a bounded wait at raise-time may suffice, **no thread, no persistent loop**, and §6.3's constraint survives intact.
>
> **The missing cell is a single run: `runloop=false`, `sleep(0.4)`, then query.** `matches=1` supports H2; `matches=0` supports H1. One condition, thirteenth row of an existing twelve-row harness.
>
> **This document does not claim to know which.** §5.3 cost 2 and §6.3's table both currently assert H1. Until the control is run, treat that assertion as **the more expensive of two live hypotheses, stated conservatively** — which is the right direction to be wrong in for a cost, and the wrong direction to be wrong in for a *design constraint*, since H1 is the sole reason this design breaks its own no-new-thread rule.

> **Two further limits on M1–M6, recorded because the panel found them and the document did not state them.**
>
> **(a) They are not in the probe log.** `docs/designs/coexistence-probes.md` carries O1, O2, O5 and U1b/U1c/U3–U7 with full transcripts and a summary table. **It contains no M1–M6** (grep: zero hits for `M1`…`M6`, `runloop`, `O14`). So the six probes that **overturn O2** — a finding that same file records as a settled negative — live only in §5.1 of a design document. A reader who opens the probe log to check O2 finds O2's negative and no sign it was disputed. Nothing here can fix that: **the probe log is a sibling authority document and editing it is a separate change with its own review.** Recorded as an outstanding action against `coexistence-probes.md`, owned by whoever lands the O2 reversal there.
>
> **(b) No probe held a window longer than ~2 s.** M3–M6 each put a window up for **under two seconds** (M5: ~1.9 s). Every macOS claim in §5 is therefore a claim about a ~2-second window. The subsystem's defining incident was **6 h 37 m**. Nothing in M1–M6 speaks to a window that persists for an entire driving episode: not run-loop starvation while the agent's main thread is busy, not space switches, not display sleep, not a compositor reclaiming an idle surface. **The design proposes a *continuous* indicator and has evidence only for a momentary one.** M-GATE (§5.4) is where that has to be closed; item 5 below adds it.

> **O2's negative was a race, not a wall.** It created a window and queried the on-screen list before the window server had processed the window's appearance. The window it built was fine. `visible=True` was not a lie; `matches=0` was a measurement taken too early.

**M5 — do real pixels reach the physical panel?** 40 × 40 magenta window from SSH, held ~1.9 s; `screencapture -x -R500,500,80,80` fired mid-flight; PNG decoded and sampled:
```
window region  -> (238, 82, 247)     magenta, as drawn
outside region -> (0, 0, 0)          unchanged
```
Not merely in a list. **Composited, on the display, from an SSH process.**

**M6 — the whole indicator design, on macOS, from SSH.** Full-screen (1728 × 1117) borderless `NSWindow`, `isOpaque=false`, `backgroundColor=.clear`, `.statusBar` level, `ignoresMouseEvents=true`, `collectionBehavior=[.canJoinAllSpaces,.stationary,.fullScreenAuxiliary]`, custom `NSView` drawing a 6 px amber perimeter **plus a 240 × 28 tab with real rendered text**. `matches=1`. Screen samples, before vs during:
```
ring pixels     (2,2)   (65,121,178) -> (247,197,69)      amber
                (6,6)   (64,121,177) -> (247,197,68)
                (2,40)  (65,122,178) -> (247,197,68)
                (40,2)  (63,121,176) -> (246,196,68)
non-ring pixels (30,30) (64,121,177) -> (64,121,177)      UNCHANGED
                (50,50) (65,122,178) -> (65,122,178)      UNCHANGED
interior region 600,400,40x40  before == during == after   BYTE-IDENTICAL
```

### 5.2 What this changes, stated exactly

| Revision 1 claim | Status |
|---|---|
| "An SSH/Background-domain process cannot put a window on the console user's desktop." | **FALSE.** M3, M5. |
| "Menu-bar item / Dock badge — same wall, same reason." | **The stated reason is void.** Whether `NSStatusItem` itself works is now simply **untested**, not closed. |
| "macOS parity is not achievable with the mechanisms this bundle has." | **FALSE as to mechanism.** It is achievable at a stated cost (§5.3). |
| "`macos.py` deliberately never imports AppKit" | **True, and it is now the whole of the cost** rather than a symptom of impossibility. |

And a bonus the probes were not looking for: **on macOS the hollow-ring geometry needs no `SHAPE` extension and no `WS_EX_TRANSPARENT`.** Alpha compositing gives the hollow interior; `ignoresMouseEvents` gives input pass-through; `NSAttributedString` gives text. M6's interior samples are byte-identical — the macOS equivalent of P3, obtained with two window properties instead of a shape protocol.

**A precise negative, recorded so nobody builds on it:** `sessionHasGraphicAccess` and `CGSessionCopyCurrentDictionary()` **do not predict window-server access.** From SSH both report "no GUI session" (M1) and windows composite anyway (M5). Neither may be used as a capability probe for this feature. That is exactly the shape of mistake O2 made — inferring a capability from an adjacent signal — and it is worth naming twice.

### 5.3 The cost, which is real and must not be buried

macOS becomes possible, not free.

1. **An AppKit dependency in a module that deliberately has none.** `macos.py` imports only Quartz `CG*`. This is a genuine architectural change to that module, not a variation.
2. **An `NSApplication` run loop must be pumped continuously — asserted, and *not yet* proven.** Revision 2 wrote *"M4 proves the run loop is the load-bearing element."* **M4 does not prove that.** Its `runloop=true` arm also waits 0.4 s and its `runloop=false` arm waits not at all, so the two factors are confounded across all twelve runs — see §5.1's note on M4. Two hypotheses remain live: **H1**, the loop must be pumped (persistent loop → **a new thread**); **H2**, the window server needs ~0.4 s by any mechanism (a bounded wait at raise-time → **no thread**). **This cost is stated at H1, the more expensive of the two, and it is the sole reason this design breaks §6.3's "no new thread, no new lock, no new timer" constraint.** One control run decides it (§5.1, Q10's prerequisite); it has not been run, and **Q10 must not be decided until it is** — asking someone to accept a new thread before knowing one is required is precisely the unmeasured-cost pattern §0.1 exists to stop.
3. **`ignoresMouseEvents` is per-window.** A ring that passes clicks through and a tab that receives them cannot be one window on macOS. **For the tab-only design this cost vanishes** — one window, `ignoresMouseEvents = false`, done. It would return with the ring.
4. **Click-without-focus-steal is UNVERIFIED.** Windows has `WS_EX_NOACTIVATE`; X11 has override-redirect, proven by U5. The macOS equivalent (a `.nonactivatingPanel` `NSPanel`) is untested here. **M-GATE item 2.**

### 5.4 M-GATE — the mechanical condition for macOS

> **On a real Mac with a console user:**
> 1. The tab renders with legible text and is present in `CGWindowListCopyWindowInfo(.optionOnScreenOnly)` **and** in a `screencapture` pixel sample — both, as in M5/M6.
> 2. A real click on Pause invokes the pause handler **without changing the foreground application** — measured as the frontmost app's bundle id before and after. If this fails, macOS gets a labelled *disclosure* with no controls, §7.1's degraded form, and §5.5's dialog text ships instead.
> 3. The tab survives a space switch and a fullscreen app (`.canJoinAllSpaces` / `.fullScreenAuxiliary` set in M6 but **not tested under a fullscreen app**).
> 4. Behaviour is recorded, not assumed, for: no console user; SSH user ≠ console user; screen locked; multi-display. M1–M6 all ran with SSH user == console user on a single display.
> 5. **The tab survives a driving-episode-length hold, not a probe-length one.** M3–M6 each held a window for **under ~2 s**; the incident this subsystem exists for ran **6 h 37 m**. Raise the tab and hold it while the agent drives for a duration on the incident's order of magnitude, with the main thread genuinely busy, and confirm at the end — by the *same* two checks as item 1, on-screen list **and** pixel read-back — that it is still there. §5.1(b).

Until M-GATE passes, macOS keeps the dialog, **with §5.5's text corrected** — because that text is currently the only thing a macOS user has and it is a six-line change.

### 5.5 The interim honest form

Ship this now, independent of everything else. Today's `_macos_announce_message` discloses the timeout and the two outcomes (§7.3, hard-won). It does not disclose the thing a macOS user most needs: **after they click Continue, nothing will tell them the agent is still there.**

```
While driving, this Mac will show no on-screen indicator yet. To stop the
agent at any time: use this Mac's own keyboard or trackpad; the agent halts
before its next action and stays halted.
```

Both sentences are true and both are mechanisms: the absence is today's behaviour, and the stop control is §6.0's halt invariant, unconditional on every platform. Revision 1 wrote *"macOS does not allow one here"* — **that sentence would now be a false statement to a user, and it is replaced by "yet."**

This does not weaken §7.1: §7.1 already provides for a platform whose announcement carries no pause button. It makes the design say so *to the human*, not only to the reader of the design.

### 5.6 A note for whoever reviews this

Two of these probes contradict a document this design is required not to contradict. coexistence.md §13 lists the agent-drawn macOS overlay under *"Confirmed closed, not for decision… Settled negative. Stop probing."* **I probed it, and the negative does not hold.** I am not editing coexistence.md here — that is a separate change with its own review — but the finding must not sit only in a probe log. **The most valuable thing in this revision may be the reminder that a "settled negative" is a measurement, and measurements can be wrong in the direction of a *missing* safety mechanism.**

---

## 6. Failure modes

Ordered by severity. **D** = disclosure drops or is inert; **E** = environment the design does not handle; **H** = anything that can hang.

### 6.1 D — disclosure drops while an action is in flight

**D1 — one tool lowers the indicator another is driving under.** *Closed, inherited, tested* (band-lifetime F8). This design's obligation is not to break it, discharged by reusing `_band_enter`/`_band_exit` verbatim (§4.6).

**D2 — the indicator process dies mid-episode while driving continues.**
*Linux: impossible by construction.* The window lives on the injector's own X connection; the connection's death destroys both the window and the ability to inject (U6).
*Windows: real, present today, unfixed by this design.* The overlay is a separate long-lived process; kill it and `_ensure_band_raised` early-returns on `handle.shown`, a Python bool that knows nothing about the remote process.
**Smallest available mitigation:** `_band_enter` additionally checks `self._proc.poll() is not None` before trusting `shown` — a local, non-blocking read, no `powershell.exe` spawn. If dead, treat as a raise failure and run `_handle_channel_failure` (existing §7.6 policy).
**UNVERIFIED and gated:** whether the interop launcher exits when the real Windows overlay process dies is not established — `show()`'s own docstring says the two PIDs differ. If Q2 comes back negative this mitigation is worthless and **must not ship**, because a liveness check that always reports "alive" is worse than none.

**D3 — the indicator is drawn but overpainted.** A compositor's chrome or a fullscreen client can sit above an override-redirect window (U4). **Undetectable — §6.4.** Under the band this degraded gracefully; under the tab it is total. **This is why Q4 is now L-GATE item 2 (§4.4.1), not an open question.**

**D4 — `announce`/`enabled` removes disclosure entirely.** **Closed at `60bf7ef`** (§3).

**D5 — the indicator renders and its controls are dead.** *Live today, on Linux, undetected.* V14: `_poll_events` catches bare `Exception` and returns with no log line, no flag, and no detection path; `self._shown` stays `True`. The band remains on screen, looking exactly as it does when working. Pause and Cancel do nothing. **By §7.1 that is a stop button the human cannot reach, and it is invisible to every layer above it.**

One thing this does *not* break, verified: **geometric exclusion survives.** It is enforced at the injection call site (`coexistence_guard.py:263`), not in the poll thread, so the agent still cannot click its own controls after the thread dies. The failure is one-sided — the human loses their control, the agent does not gain one.

**Smallest available fix, and it is three lines:** log the exception at ERROR with its traceback, and set a flag that `_band_enter` reads and routes to `_handle_channel_failure` — the same §7.6 policy path a failed raise already takes. No new thread, no new lock, no new timer, no watchdog. **Ships with T1.** Revision 1 did not mention this failure mode at all.

### 6.2 E — environments the design does not handle

**E1 — Wayland / XWayland.** Never mentioned in revision 1, on any of its 421 lines. It is the modern GNOME default and a **documented live gap**: `linux_x11.py:249-314`'s probe tests `DISPLAY`, an X connection, and XTEST, and XWayland satisfies all three, so the tools **mount** on a Wayland desktop and attach to XWayland rather than the compositor. `docs/SETUP.md:281-290` states plainly that input and capture under XWayland have **never been verified** and that the bundle makes no claim about them.

**S7 is the same defect class, caught in its other form, and it raises E1's priority.** `bbf3dcf` fixed a probe that accepted *an* X server as *the* desktop: a stray `Xvfb` passed every check, and the bundle drove it silently, with zero errors — "it says it did it, nothing happens on your screen." That is E1's predicted failure verbatim, arriving through a different door. The fix compares a blindly-picked-up `DISPLAY` against the user's own session and refuses on mismatch. **It added no Wayland check.** So the probe now knows *which X server* it found and still does not know *whether that X server is the compositor the human is looking at*. Q8 is no longer a symmetric unknown against a probe that checked nothing; it is the one remaining hole in a probe that has just been taught to be suspicious.

Consequence for this design, stated rather than fixed: **on a Wayland desktop the tab's behaviour is unknown.** An override-redirect XWayland window may render only within the XWayland surface, may not be positionable in compositor coordinates, and may not sit above native Wayland clients — in which case the platform mounts a tool that drives and shows an indicator nobody can see, which is §7.1's exact failure mode arriving through the front door.

**Not fixed here, and deliberately so.** A Wayland *backend* is a separate design (remote-transport §379 already scopes it as one). What belongs in *this* design is the honest statement that **L-GATE's four items are specified for X11 and say nothing about XWayland**, and that Q8 asks for the one-hour measurement that would tell us which of the two situations we are in. Adding a Wayland detection check to the probe is a real candidate and it is *not* proposed here, because refusing to mount on XWayland would remove a capability that may work fine — and nobody has looked.

**E2 — multi-monitor hot-plug and resolution change.** Verified: `resolve_display()` caches at mount (`__init__.py:473`, called at `:3044`) and only `screen_info`'s explicit `refresh=True` or a `select_monitor` target switch ever re-resolves. **There is no RandR or display-change listener anywhere in the module** (grep: no `randr`/`RRScreenChange` outside enumeration). So unplug the target monitor, or change its resolution, mid-episode, and the indicator's geometry is stale for the rest of the episode.

Blast radius under each design, which is the point:

| Indicator | Stale-geometry consequence |
|---|---|
| Today's band | A 36 px strip at a stale origin. Wrong, visible, survivable. |
| **The tab** | A 280 × 30 window at a stale origin — possibly off-screen entirely, i.e. **no indicator**. |
| The ring | A full-monitor window sized to a monitor that no longer exists. Largest blast radius of the three. |

**One more reason the ring is not scheduled.** For the tab, the exposure is real and is **not fixed here**: it is recorded as Q9 with a named smallest fix (re-resolve on `_band_enter` when the cached geometry no longer matches `list_monitors()` — a local call, no new thread) that is deliberately **not** specified until someone has measured how often it happens. Specifying a mechanism ahead of its measurement is the sin this revision exists to stop repeating.

### 6.3 H — anything that can hang

**No new thread, no new lock, no new timer, no new blocking call on Linux or Windows.** On macOS, T3 requires an `NSApplication` run loop, which **is** a new thread — stated in §5.3 rather than reclassified.

| Path | Bound | Status |
|---|---|---|
| `WindowsOverlay.hide()` → `Stop-Process` | 15 s (`STOP_PROCESS_TIMEOUT_SECONDS`), on the action path, ERROR-logged | Unchanged |
| `WindowsOverlay.show()` → ready handshake | constructor timeout; kills a never-ready process | Unchanged |
| Linux `shape_rectangles` + `sync()` | **Unbounded** — python-xlib has no per-request timeout | **Pre-existing.** `show()` already does `map()` + `sync()`. The tab adds no new request. **Deliberately not fixed** — a watchdog is the apparatus the last review struck out, and its own failure mode is what sank that design. |
| `_band_enter`'s `poll()` (D2, if it ships) | Non-blocking by definition | New; cannot hang |
| macOS run loop (T3) | N/A — a loop, not a call | **New, and the one constraint this design breaks — under H1, which is *asserted, not measured*.** If M4's missing control returns H2 (a bounded wait suffices), this row becomes a bounded call and the constraint survives. §5.1, §5.3 cost 2, Q10. |

### 6.4 The failure mode I cannot detect, and will not claim to

**P4 is the load-bearing negative of this document.** On a compositing GNOME/X11 desktop, `root.get_image()` does not read back an override-redirect window's own pixels: a pure-white test window sampled at its own centre returned the desktop background.

> **§7.4's proposed self-verification — "capture the overlay's own rectangle and check for expected pixels" — cannot be implemented with this bundle's capture path on this desktop.** A design that gated driving on such a check would refuse to drive on every GNOME box while the indicator was, in fact, correctly displayed.

Three things make carrying this against coexistence.md a deliberate act: §7.4's verification **was never built** (V8, re-confirmed at `60bf7ef`); the finding is **from a probe I ran**, not an inference; and it is **scoped to what I tested** — one compositing X11 desktop.

**And the scope now visibly matters, because macOS goes the other way.** M5 and M6 sampled the *console user's own display* through `screencapture` and read back the overlay's pixels exactly. So the capture-based check that is impossible on GNOME/X11 is demonstrably possible on macOS. **§7.4 is not wrong everywhere. It is wrong on the platform it was written for.**

What this design may honestly claim:
- **Detectable:** the window/process was created, shaped, mapped, and the API calls did not raise (Linux, synchronously, on `sync()`); the Windows overlay reached `ready` and its launcher is alive; on macOS, that the window is in the on-screen list *and* its pixels read back.
- **Not detectable, on Linux:** that a human can see it.

So the Linux liveness guarantee is **"the indicator was successfully created and its owner is alive"** — never "the indicator is visible." Any stronger phrasing in a log line, a tool description, or a result payload would be a claim the system cannot back.

**One check that does work everywhere, and it is the negative one.** P3 (X11) and M6 (macOS) both show the interior is byte-identical before, during, and after. *"The indicator occludes nothing outside its own rectangle"* is mechanically testable on both platforms even where *"the indicator is visible"* is not. That is §8's metric 2.

### 6.5 coexistence.md §7.4 — disposition

> **The disposition of `coexistence.md` §7.4, stated once, unambiguously, and by section number: §7.4 is RETIRED on Linux X11 and on Windows, and OWNED on macOS by the T3 follow-up (§0's tier table, gated by M-GATE §5.4). It is not "open," not "deferred," and not a standing promise anywhere.** Q6 (§11) is a pointer to this paragraph and carries no independent state. Two prior review rounds could not confirm this by name; this is the sentence to quote.

Per platform, with what backs each:

| Platform | Disposition | Basis |
|---|---|---|
| **Linux X11** | **RETIRED.** Nothing is owed and nothing is scheduled. | P4 (§2.3) measured directly that `root.get_image()` cannot read back an override-redirect window's own pixels on a compositing GNOME desktop; V8 confirms nothing was ever built on it. |
| **Windows** | **RETIRED for this document.** Not "unknown pending work" — no owner, no gate, no follow-up. Anyone reopening it re-opens it from scratch. | Capture goes through `bridge.ps1`, a different path, never probed. Revision 2 left this as "explicitly unknown," which is a state a reader can mistake for a live obligation. It is not one. |
| **macOS** | **OWNED by T3.** A named owner and a named decision, not a promise. | M5/M6 (§5.1) read the overlay's own pixels back through `screencapture`. The check is implementable there; whether it is *worth* its cost is T3's call. |

The review's ninth finding: §6.4's honest scoping was praised but left §7.4 standing as an ambiguous unbuilt promise. Accepted. **The reasoning behind the table, in three parts:**

1. **The pixel-verification form of §7.4 is retired on Linux X11.** P4 is a direct measurement and V8 confirms nothing was ever built on it. It should not remain in coexistence.md as a live commitment for that platform. *(That edit belongs to a coexistence.md change, not this one; recorded here as the finding that authorises it.)*
2. **The `shown` / `occluded` / `failed` tri-state is retired with it, on Linux.** A state nothing can produce is worse than a state nobody named — it invites a future implementer to fake it. Linux reports created-or-failed, and says which.
3. **One owned follow-up, not an open question: Q6, scoped to macOS.** M5/M6 show the check *is* implementable there. Whoever builds T3 owns deciding whether §7.4's cadence (on raise, plus a ~30 s timer) is worth its cost on the one platform where it works — a real screenshot on a slow timer is not free, and per-action verification would put a capture on the input hot path. **Owner: T3. Not a standing promise, and not left dangling.**

Windows is untested for this (capture goes through `bridge.ps1`, a different path) and stays explicitly unknown rather than assumed either way.

---

## 7. Tradeoffs

**K** = tab only (recommended). **B** = tab + perimeter ring (revision 1's recommendation). **T** = thin band, one edge. **S** = status quo, 36 px top band.

| Dimension | **K — tab only** | **B — tab + ring** | **T — thin band** | **S — status quo** |
|---|---|---|---|---|
| **Latency** | Identical to S. | Identical to S; two extra X requests. | Identical to S. | Baseline. |
| **Complexity** | **Lowest of the four that carry a label.** Same window class, same Input-shape call, new geometry, plus a text-rendering path. **Deletes** the full-width strip. | K plus: `SK.Bounding` geometry, a shape-before-map ordering rule (V12), `WS_EX_TRANSPARENT` on Windows, a two-window split on macOS (§5.3). | Two constants. No label. | Lowest; no label. |
| **Reliability** | No new catastrophic mode. Map-then-shape stays safe at 280 × 30. Smallest stale-geometry blast radius of the labelled options (§6.2 E2). | Adds the unshaped-full-screen-flash mode; re-opens a design the team already reverted; **largest** hot-plug blast radius. | No new failure surface. | Known-good mechanism. |
| **Cost** | Nil. | Nil. | Nil. | Nil. |
| **Security / safety** | **Best available today.** Carries a label for the first time (V5); keeps both controls; cuts Windows' swallowed-click area by ~88 % (V6). | K's properties plus an **unmeasured** peripheral-salience claim. | Middling; unlabelled. | **Worst.** Unlabelled; covers the highest-value UI real estate; the reported intrusion. |
| **Scalability** | One window per channel, same as the band. | Same. | Same. | Same. |
| **Reversibility** | **Highest.** Geometry constants and one draw call. | High; the shape rects are one function. | Highest. | n/a |
| **Org fit** | Ships on all three platforms with the gates the team can actually run. | Needs a Windows measurement *and* a macOS two-window design *and* Q1 before any of it is justified. | Contradicted by V5. | Contradicted by the report. |
| **Optimises for** | The smallest thing that closes the real defect. | An unmeasured perceptual claim. | Minimum change. | Minimum work. |
| **Sacrifices** | Peripheral salience — **which nobody has shown is worth anything.** | Simplicity, on the strength of that same unmeasured claim. | The label, and §7.1's substance. | The user's tolerance — which is what turns into an off-switch request. |

**The dominant tradeoff is peripheral salience versus every other dimension, and it is decided by Q1, which nobody has run.** Revision 1 identified exactly this and then recommended B anyway. Under the standing rule in §0.1, an unmeasured benefit cannot buy a measured cost. **K until Q1 says otherwise.**

---

## 8. What I would measure

| # | Metric | Target | Gate? | Catches |
|---|---|---|---|---|
| 1 | Elementary events injected while the indicator is down | **0, as a test** | **GATE** | The invariant. Inherited from band-lifetime metric 1. Non-negotiable. |
| 2 | **Occlusion:** with the indicator up, N sampled points outside its own rect equal their pre-raise values | **100 %** | **GATE** | The tab's reason to exist. Mechanically reliable under a compositor (P3, M6) — unlike any positive visibility check (P4). |
| 3 | **Pass-through:** a real human click on the tab's *label* region reaches the window underneath; a click on Pause/Cancel does not | **pass, as a test** | **GATE** | The three-region contract in §4.1 that revision 1 conflated. |
| 4 | **W-GATE (§4.5)** at ≠100 % DPI, with a 100 % same-row control | **pass, as a test** | **GATE** | Windows §7.1. Band stays until it passes. |
| 5 | **Q1 / L-GATE item 4 — noticeability:** a human mid-task is interrupted; do they see the tab, and does it read as "an agent is driving"? Light desktop and dark. | qualitative, **recorded** | **GATE** | The premise of the whole visual design. **Nobody has run it.** §4.4.2 resolves revision 1's contradiction: this is a gate. |
| 6 | Config: the halt invariant cannot be disabled by any key; `announce`/`enabled` refuse to mount with a human present | **pass, as a test** | **GATE — MET** | T0. `tests/test_disclosure_config_keys.py`, 19 tests, `60bf7ef`. Satisfies coexistence.md C1 item 6. |
| 7 | **L-GATE item 2 / Q4:** on GNOME, the tab's pixels are present and its Pause rect is clickable at the chosen placement | **pass, as a test** | **GATE** | D3 on the first shipping platform. §4.4.1. |
| 8 | **Poll-thread death is detected:** kill the handler path; the next `_band_enter` runs `_handle_channel_failure` and logs at ERROR | **pass, as a test** | **GATE** | D5 / V14 — live today, undetected. |
| 9 | **M-GATE (§5.4):** tab renders and reads back on macOS; a click on Pause does not change the frontmost app | **pass, as a test** | **GATE for T3** | §5.3 cost 4, the one UNVERIFIED item that decides whether macOS gets controls or only a disclosure. |
| 10 | Sessions where an action ran with `handle.shown == True` but the Windows overlay process was dead | **0** | signal | D2 — measurable only if Q2 comes back positive. |
| 11 | Episodes in which the target monitor's geometry changed mid-episode | **recorded, not targeted** | signal | E2. It is a cost; an unknown one is the problem. Feeds Q9. |

**Metrics 1–9 are gates. 10 and 11 are signals.** Revision 1 listed six metrics, called four of them gates, and put the one its own §7 named as decisive into the signal column. That inconsistency is the thing this table exists to remove.

### 8.1 What "GATE" means here — and what nothing in this repository will stop

Four review lenses checked and found the same thing, so it is stated in the table's own terms rather than left for a fifth to rediscover.

> **"GATE" in this table means a release-blocking obligation on a human. With one exception it does not mean CI will refuse a merge.** `.github/workflows/ci.yml` runs exactly three things: `pytest tests/`, `ruff format --check`, and `ruff check`. **Nothing else is enforced by any automation in this repository.**

| Metric | Enforcement, traced at `bbf3dcf` |
|---|---|
| **6** | **Mechanical and blocking.** `tests/test_disclosure_config_keys.py` runs inside `pytest tests/` in CI. A regression fails the build. This is the only gate in the table with that property. |
| **1, 3, 8** | **Human checklist.** Written as "pass, as a test," and they *should* be offline tests in `tests/` — CI would then enforce them for free. Metric 8's test cannot exist yet: it tests the D5 fix, which is unbuilt. |
| **2, 4, 5, 7, 9** | **Human checklist, and cannot be otherwise.** They need a real display, real Windows hardware at non-100 % DPI, a real Mac, or a real person. `ci.yml`'s own comment states the suite runs *"deliberately no display server."* |

**The ship gate is real but is not a merge gate.** `scripts/verify_coexistence.py` is a genuine statistical, real-subprocess evidence run — and `ci.yml` says in a comment that it is **not run there**; `CONTRIBUTING.md` asks a human to run it locally before cutting a release. Note the contrast the repository draws itself: the *other* out-of-CI gate, `scripts/wire_check.py`, has its staleness enforced offline by `tests/test_wire_attestation_freshness.py`, which fails the build if the attestation is missing or older than 30 days. **The coexistence gate has no such freshness check.** Nothing anywhere records that it was ever run, or when.

**Correcting the overclaim, in this document's own words.** §4.4 calls L-GATE "mechanical and blocking" and §12 finding 7 repeats it. *Mechanical* is accurate — each item names a specific observation with a pass/fail outcome, which is the property the finding asked for and the thing prose gates lacked. *Blocking* is a **discipline commitment, not an enforced one**: if someone skipped all four items and merged T1, no check in this repository would object.

**What would make them mechanical in the enforced sense**, named precisely so the claim is falsifiable rather than aspirational:
1. **Metrics 1, 3 and 8 become offline tests in `tests/`.** They stub the platform layer like the rest of the suite does, so CI enforces them at zero marginal cost. This is the cheapest step and it converts three gates.
2. **Hardware gates get an attestation file plus a freshness test**, copying `wire_check.py`/`test_wire_attestation_freshness.py` exactly — a pattern already shipped and tested in this repository, not a new one. The L-GATE/W-GATE/M-GATE runs write a dated result; an offline test fails the build if it is absent or stale. That makes "was the gate run?" mechanical even though the gate itself needs a human and a screen.
3. **Metric 5 (Q1) can never be CI-enforced** — it requires a person looking at a screen. Under (2) its *attestation* can be, which is the honest ceiling.

**None of this is proposed by this document.** It is scoped so the next reader knows the gap is measured rather than overlooked, and knows the shape of the fix.

---

## 9. Alternatives

### 9.1 B — tab + perimeter ring. **Rejected. This is a concession.**

Revision 1 recommended B and evaluated the tab only as a *component* of it, never as a candidate. The review's sixth finding. Evaluated properly now:

**What the ring adds:** peripheral salience — presence in all four quadrants of the visual field — and the screen-sharing idiom's recognisability.

**What the ring does not add:** the label (V5 — that is the tab), either stop control (§7.1 — those are the tab), and any defect closure whatsoever. Strip the ring from B and **every requirement §7.1 imposes is still met.**

**What the ring costs:** `SK.Bounding` geometry and a **shape-before-map ordering rule that is a safety property** (V12 — one unshaped frame on a full-monitor window is an opaque rectangle over the entire display); `WS_EX_TRANSPARENT` on Windows, re-opening a design the team already reverted for an undefined-z-order paint bug; a two-window split on macOS because `ignoresMouseEvents` is per-window (§5.3); the largest stale-geometry blast radius of any option (§6.2 E2); and a thickness constant `T` that revision 1 set to 6 px and then admitted, in its own §4.4, it could not defend.

**The decisive argument is the one the review named.** Revision 1 wrote of `T`: *"specifying a constant ahead of its measurement is what sank the last design, and I would rather name the same sin than repeat it quietly."* Naming it is not avoiding it. `T = 6` was unmeasured, the ring's *entire benefit* is unmeasured, and revision 1 recommended shipping both. **That is the `T = 90 s` pattern, at the level of a whole feature rather than a constant.**

> **The ring is not scheduled.** It is reconsidered only if Q1 (metric 5) returns a specific finding — that a labelled tab alone is *not* noticed by a distracted human while a perimeter is. That is a real, runnable experiment with a falsifiable outcome. Until it returns that result, the ring is an unmeasured claim buying a measured cost, and this document declines it.

Note what dropping the ring resolves in one move: the shape-before-map hazard, `T`, the `WS_EX_TRANSPARENT` re-opening, the macOS two-window split, and most of E2's blast radius. **Five problems deleted by removing one feature.** That is what "bias toward the smallest thing that closes the real defect" looks like when it is actually applied.

### 9.2 T — keep the band, make it thin, move it to one edge

> Change `BAND_HEIGHT` from 36 to ~6 and move the origin to the bottom edge. Two constants.

Genuinely the simplest option and it deserves a hearing. **It fails on one thing and the one thing is decisive: it does not carry the label, and V5 says nothing else does either.** The Linux band renders no text today; thinning it makes text impossible rather than merely absent. **A disclosure that does not say what it discloses is not, in the sense §7.1 means, an announcement.** Additionally, a bottom band on Windows would swallow Start-button and tray clicks across the full screen width (V6).

I would not trade the label. This is the same judgement revision 1 made, and it is the only one of its three arguments that survives — the other two (edge occlusion, perceptual shape) were arguments for the ring, and the ring is gone.

### 9.3 Everything else

| Candidate | Verdict |
|---|---|
| **Tray / menu-bar item** | **Reject on Linux and Windows.** GNOME removed the system tray (needs a third-party AppIndicator extension the operator does not control); Windows 11 hides tray icons in an overflow flyout **by default** — an indicator the OS may hide is §7.1's failure mode as a product decision. **On macOS, revision 1 rejected `NSStatusItem` as "same wall, same reason" — that reason is void (§5.2). It is now simply untested,** and it is a weaker candidate than the tab regardless, because a menu-bar item is small and easy to miss. Not proposed; no longer closed. |
| **Cursor change** | **Reject.** X11 cursors are per-window and client-owned; macOS `NSCursor` is per-app. Windows `SetSystemCursor` would work and is the worst option available: it mutates **system-wide state that outlives the process**, so a crash leaves the user's cursor permanently changed — a strictly worse orphan than the leaked band `da7972b` closed. |
| **OS-native capture indicator** | **Reject as the mechanism; keep as an observation (Q3).** Windows has no public "an app is controlling this machine" indicator. macOS's is tied to capture and says *recording* — the wrong claim, and absent during pure input injection. |
| **Audio cue** | **Reject as primary.** No persistent state; defeated by mute, headphones, and deafness; a repeating tone during driving is intolerable. A one-shot chime at episode start is defensible as an *addition* and is not specified here because nothing in the report asks for it. |
| **Toast / notification** | **Reject.** Transient by construction, and suppressible by Focus/DND — a disclosure channel the human's own OS settings can silently switch off. The same defect T0 just closed, relocated. |
| **Tab** | **Accept**, with placement, text mechanism, and noticeability all gated rather than asserted. |

---

## 10. Migration and rollout

0. **T0 — done.** Shipped at `60bf7ef`. No action.
1. **macOS dialog text (§5.5)** — six lines of string, no behaviour change, no gate, independent of everything else. **Ship first**, because it is the only thing that improves a macOS user's position today and because revision 1's proposed wording is now factually wrong.
2. **Run the probes that gate the rest.** L-GATE item 1 (does a core X font exist, or is a real text dependency required); Q4 / L-GATE item 2 (tab placement against the GNOME panel); Q2 (does `Popen.poll()` track the real Windows overlay's death); Q8 (XWayland). Hours, not days, and none of them require writing shipping code.
3. **D5 / V14 — the three-line poll-thread fix.** Independent of the tab, closes a live §7.1 hole, and is testable on its own (metric 8). **Can ship ahead of T1.**
4. **T1 — Linux tab**, only if L-GATE's four items pass. Metrics 1, 2, 3, 7, 8 as tests. If item 1 shows a real text dependency is required, that is a separate decision with its own review — **do not add a dependency inside a gate run.**
5. **T2 — Windows tab.** W-GATE's two items. The window shrinks and `WS_EX_TRANSPARENT` is never introduced, so this is smaller than revision 1's T2 by a wide margin. Fix `overlay_windows.py`'s stale docstring (V6) in the same change.
6. **T3 — macOS tab.** M-GATE's four items. **Its first item is a decision, not a measurement:** whether an AppKit dependency and a run-loop thread in the agent process are acceptable (§5.3). That decision is the user's, and it should be made before anyone writes the probe for M-GATE item 2.
7. **Q1 (metric 5) — the human-eyes study. It runs at step 4, not here.** It is L-GATE item 4, so it is a **precondition of shipping T1**, on a tab raised for the study on a real desktop — *not* on a tab already shipped to users. Step 7 is only the **consequence branch**: if Q1 returns "a tab alone is not noticed," §9.1's condition is met and the ring is reconsidered *then*, with a measurement behind it.

> **The four sections that had to agree, and now do.** §0's tier table (T1's gate is "L-GATE — four mechanical items, **including the human-eyes study**"), §4.4 item 4 + §4.4.2 (gate, resolved), §8 metric 5 (**GATE**), and §10 steps 4 and 7. **Reconciled: §0, §4.4, §8, §10.** Revision 1's contradiction was gate-in-§0/§10 versus signal-in-§8; revision 2 fixed §8 and left a **second, quieter form of the same contradiction** in §10 step 7, which scheduled Q1 "on the shipped tab" while §10 step 4 forbade shipping until Q1 passed. That is corrected above. **Q1 is a gate in all four places, and there is no remaining sentence in this document that schedules it after T1 ships.**

**Rollback:** every tier is geometry constants and one draw call per platform. Nothing persistent, nothing crossing a protocol boundary, no data model change. Reverting T1 restores the band.

---

## 11. Open questions

**Q1 — Is the indicator actually noticed, and does it read as "an agent is driving"?** **Now L-GATE item 4 and metric 5 — a gate, not a question.** Listed here because it is still unanswered on every platform. Needs: the tab on a real screen, light desktop and dark, at 100 % and 150 % scaling, with a person mid-task.

**Q2 — Does `Popen.poll()` track the real Windows overlay process's death?** D2's mitigation is worthless without it and worse than worthless if it silently always reports "alive." `show()`'s docstring establishes the launcher and the real Windows process are different PIDs; whether the launcher exits when the overlay dies is not established. One probe.

**Q3 — Does macOS's screen-recording indicator fire for this bundle's capture from a Background-domain process?** Still worth knowing; still never a substitute (wrong claim, absent during pure input injection). Lower priority now that §5 shows macOS can draw its own.

**Q4 — Where does the tab go?** **Now L-GATE item 2 — a blocking gate (§4.4.1).** No placement is specified in this document. Every screen edge is owned by something on some platform: GNOME's top panel (which may composite above an override-redirect window), Windows 11's centred taskbar, the Start button, the tray, the macOS menu bar and notch.

**Q5 — What text, in what font, at what size?** L-GATE item 1 decides the mechanism; the constants follow the measurement, not the other way round. **Revision 1's `T = 6 px` and its tab dimensions are withdrawn, not carried forward.** No constant in this revision is asserted ahead of the measurement that would justify it.

**Q6 — coexistence.md §7.4's self-verification.** **Not an open question. Dispositioned in full at §6.5**, which is the authoritative statement: **retired on Linux X11 and Windows; owned by T3 on macOS.** This entry is a pointer and carries no state of its own — it is listed here only because two review rounds looked for the disposition under "open questions" and did not find it named.

**Q7 — Should the tab's content change when the agent is paused?** A tab that renders text makes "PAUSED BY YOU" possible for the first time. **Deliberately not specified:** it is a new state machine in the indicator, it is not required by any reported defect, and adding it now is the apparatus reflex. Recorded so the omission is on the record.

**Q8 — What does the tab do under XWayland?** §6.2 E1. The probe mounts on Wayland today and attaches to XWayland; input and capture there have never been verified (`docs/SETUP.md:281-290`). One hour on a Wayland GNOME session answers whether L-GATE's results transfer, whether the platform needs its own gate, or whether the probe should refuse to mount there at all. **Nothing in this design may be claimed for Wayland until this is run.** **Raised in priority by S7:** `bbf3dcf` shipped the "am I looking at the right X server?" check and left the Wayland arm of that same question unanswered, so the next person to open `probe()` is the cheapest person to answer it.

**Q9 — How often does the target monitor's geometry change mid-episode?** §6.2 E2. There is no display-change listener and geometry is cached at mount. Metric 11 records the rate. A smallest fix exists (re-resolve on `_band_enter` when cached geometry no longer matches `list_monitors()`) and is **not specified here**, because specifying a mechanism ahead of its measurement is the failure mode this revision is written against.

**Q10 — Is an AppKit dependency and a run-loop thread acceptable for macOS disclosure?** §5.3. Not a research question — a **decision**, and the user's. It is the price of macOS ever having a continuous indicator, and §5's probes are what turned it from an impossibility into a price.

> **Named prerequisite — do not decide Q10 until this is run.** Q10 asks whether a price is acceptable, and **the price is not yet known**. §5.1's note on M4 shows the twelve-run matrix confounds `runloop` with elapsed wall time, so it cannot distinguish *"the run loop must be pumped"* (H1 — persistent run loop, new thread, breaks §6.3's no-new-thread constraint) from *"the window server needs ~0.4 s by any mechanism"* (H2 — a bounded wait at raise-time, no thread, constraint intact). **Prerequisite: one control run — `runloop=false`, `sleep(0.4)`, then query — added to the existing harness as a thirteenth condition.** `matches=1` → H2; `matches=0` → H1.
>
> **Asking the user to accept a new thread before knowing a new thread is required is the exact failure this revision was written against**: a cost asserted ahead of the measurement that would justify it. Q10 is **blocked on this control**, not merely informed by it. The Mac was not available when this was written, so the control was **not run** and nothing here assumes its outcome.

---

## 12. Disposition of the review

All six lenses returned CONCERN; none returned FAIL. Where I argued rather than accepted, it is marked and reasoned.

| # | Finding | Disposition |
|---|---|---|
| 1 | T0's central claim was false as written | **Accepted in full.** §3.2 states the false claim, the correction, and what the shipped fix had to do to make it true. §0.1 promotes it to a standing rule and applies it to §5. |
| 2 | Q4 must become a blocking gate | **Accepted in full.** L-GATE item 2, §4.4.1, metric 7. |
| 3 | §0/§10 vs §8 contradiction on human-eyes validation | **Accepted — and revision 2's fix was incomplete.** Resolved in favour of *gate* (§4.4.2), §8 rebuilt with an explicit Gate? column — but §10 step 7 still scheduled Q1 "on the shipped tab" while §10 step 4 forbade shipping until it passed. **Now reconciled across §0, §4.4, §8 and §10**, named by section at §10 step 7. |
| 4 | `enabled` and `announce` differ on three axes | **Accepted.** "Delete both" withdrawn; §3.1 argues the shipped split is better than what I proposed, and records the error as mine. |
| 5 | macOS "impossible" is SSH-only, generalised | **Accepted, and probed.** §5. **O2 overturned** — the SSH case works; the variable was a run loop, not a session boundary. §5.6 flags the contradiction with coexistence.md §13 rather than burying it. |
| 6 | Tab-only never evaluated as its own candidate | **Accepted, and conceded.** §9.1: the ring does not earn its cost, is not scheduled, and returns only if Q1 produces a specific finding. Five problems deleted with it. |
| 7 | Linux got prose gates; Windows got a mechanical one | **Accepted — with revision 2's own wording corrected.** L-GATE (§4.4) is **mechanical in form** (each item names a specific observation with a pass/fail outcome, which is what the finding asked for) but **not blocking in the enforced sense**: nothing in CI would refuse a merge if the checklist were skipped. Revision 2 said "mechanical and blocking" and that overclaimed. §8.1 states what is actually enforced and what would make the rest mechanical. W-GATE shrinks to two items because a shipped fix retired two. |
| 8 | Four uncovered items | **Accepted, all four.** Wayland/XWayland §6.2 E1 + Q8; hot-plug §6.2 E2 + Q9 + metric 11; the label region's input behaviour §4.1's three-region table; the silent poll thread §6.1 D5 + metric 8 + a three-line fix that can ship ahead of T1. |
| 9 | §7.4 left as an ambiguous standing promise | **Accepted, and re-stated by section because no lens could confirm it by name.** **§6.5 is the authoritative disposition: `coexistence.md` §7.4 is RETIRED on Linux X11 and Windows, OWNED by T3 on macOS.** Revision 2 left Windows as "explicitly unknown," which reads like a live obligation; it is not one. Q6 (§11) is now a pointer with no independent state. |

### 12.1 Round 3 — what a third review found that revision 2 had not recorded

Six items came back. Two are corrections to claims revision 2 asserted; four are gaps it was silent on. All were re-traced at `bbf3dcf` before being written down.

| # | Finding | Disposition |
|---|---|---|
| R1 | **"Untouched for fourteen consecutive commits" was copied from a commit message, not re-derived** — in the document that made not doing that its standing rule. All six lenses caught it independently. | **Accepted; the sharpest finding of the round.** Re-derived at `bbf3dcf`: **21**, with the commands, in the header. The underlying property holds *more* strongly than claimed (byte-identical, and **28** commits since the last functional change). §0.1 applies to this document's own arithmetic, not only to its code claims — **the first pass at this correction produced 22 by counting rows in a path-filtered log, and was caught by re-running `rev-list`.** |
| R2 | **The QUIET floor.** A present-but-still human >2 s idle is `QUIET`/**HIGH**, so `human_present = False` and the decline path mounts with no indicator; and the decline branch never re-samples, so anyone arriving between mount and first action gets nothing. Two lenses, independently, from different angles. | **Accepted and named — §3.4, with its precision boundary and disposition (accepted, not fixed).** The lenses' characterisation — *courtesy gap, not a §7.1 breach* — was **verified against `coexistence_guard.py:249-256` before being repeated**, not taken on trust: the halt re-samples every injected event and never consults confidence. Also corrected the false sentence in §3.2 that this finding exposed. |
| R3 | **§7.4's disposition was never confirmable by section number.** | **Accepted.** §6.5 restated as a single quotable sentence plus a per-platform table; Q6 demoted to a pointer. Finding 9 above rewritten. |
| R4 | **The gate-vs-signal contradiction was only half-fixed.** | **Accepted.** Revision 2 fixed §8 and left the same contradiction in §10 step 7. **Reconciled across §0, §4.4, §8, §10** — named at §10 step 7 and in finding 3 above. |
| R5 | **coexistence.md §13's stale "settled negative" is invisible to anyone reading that file alone.** Flagging rather than silently editing a sibling authority doc was judged correct — but a reader who never opens this document never learns the claim is disputed. | **Accepted.** One line added to `coexistence.md` §13 pointing at §5. That is the minimum that makes the dispute discoverable from the file that carries the stale claim; the substantive edit remains a separate change with its own review (§5.6). The same gap in `coexistence-probes.md` is recorded at §5.1(a) and **not** closed — no owner yet. |
| R6 | **No CI enforces any gate except metric 6.** Four lenses checked. "L-GATE is mechanical and blocking" was an overclaim. | **Accepted; the overclaim is withdrawn rather than softened.** §8.1 states what CI actually runs, which gates are human checklists and why, that the ship gate has no freshness check while `wire_check.py`'s does, and the three concrete steps that would make the rest mechanical. Finding 7 above rewritten. |

**Also recorded this round, from outside the review:** the `bbf3dcf` probe defect and its relation to E1 (§2.1 S7, §6.2 E1, Q8) — a shipped instance of the exact "drives the wrong display, silently, zero errors" failure E1 predicts for XWayland, whose fix pointedly added no Wayland check; and three limits on the macOS evidence (§5.1) — M4's **missing `runloop=false, sleep(0.4)` control**, now a named prerequisite blocking Q10 (§11) and flagged at §5.3 cost 2 and §6.3; M1–M6's absence from `coexistence-probes.md`; and no probe holding a window beyond ~2 s in a subsystem whose defining incident ran 6 h 37 m, now M-GATE item 5.

**Nothing was argued against.** Every finding held on re-reading the code, and one of them (5) turned out to understate the problem: the verdict was not merely untested outside SSH — it was wrong inside SSH.

**What I could not verify, stated plainly:**

- Whether the tab is **noticeable to a human** on any platform. Never measured. Now a gate.
- Whether a **core X font** is available for label rendering on a modern GNOME X server, or whether text requires a new dependency. L-GATE item 1.
- Whether the tab is **visible or clickable at any particular placement** on GNOME. L-GATE item 2.
- Anything at all about **XWayland**. Q8.
- Whether **`Popen.poll()`** tracks the real Windows overlay's death. Q2.
- On macOS: **click-without-focus-steal**, behaviour under a **fullscreen app** or **space switch**, with **no console user**, with **SSH user ≠ console user**, when **locked**, or on **multiple displays**. M1–M6 all ran single-display, SSH user == console user, unlocked. M-GATE items 2–4.
- Whether the shipped **Windows DPI fix** holds through a full live session, and how it behaves on a 100 %-scaled monitor as a same-row control — recorded as unverified by the commit that shipped it. W-GATE item 2.
