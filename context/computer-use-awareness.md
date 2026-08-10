# Computer Use (real desktop control)

This session can see and control a real desktop — Windows, macOS, or Linux — through the
LLM provider's native computer-use tool, named `computer`. It works on anything on screen
— including applications with no API, no CLI, and no extension.

**Which machine this session drives binds at mount** from `config.target` (unset means
this machine; `ssh://user@host` means a different, reachable one) — but it is not frozen
there. `desktop(action="retarget")` re-points an already-mounted session at a new machine,
and `computer_use_unavailable(action="activate")` binds and mounts real tools when nothing
mounted yet; neither needs a restart. There is still no per-call host parameter on
ordinary actions (click, type, screenshot, ...) — that absence means use retarget/activate
to switch machines, not that this capability is local-only. A user naming a different
machine is asking to retarget/activate, not reporting a limitation.

**Delegate desktop work to `computer-use:computer-operator`.** It carries the operating
rules for driving a live machine safely. Use it whenever the user asks what is on their
screen, asks you to click, type, drag, scroll, or open something in a desktop
application, or hits a task that cannot be done through an API.

**This capability is not always present.** If `computer_use_unavailable` appears in your
tool list instead of `computer`/`desktop`, no backend was available for this session —
relay that tool's explanation to the user and stop; do not improvise a workaround (e.g.
driving a remote machine over a shell tool).

The screen is captured, downscaled, and handed to the model as an image; coordinates the
model emits are scaled back to physical pixels automatically. Never guess coordinates —
take a screenshot first.

**A human may share this keyboard, and keystrokes can interleave.** See the `desktop`
tool's own description for the full safety note — moved there because it reaches the
model on every dialect, unlike this always-loaded file, which competes with others for a
fixed budget.
