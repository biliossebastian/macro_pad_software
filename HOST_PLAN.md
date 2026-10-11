# Companion app plan (host side)

The parallel track to [firmware/BRINGUP.md](firmware/BRINGUP.md). That document
takes the hardware from "RP2040 enumerates" to "Raw HID sends button events."
This one takes the Python app from "a window with dead widgets" to "a real key
press runs a real action" — **without hardware**, using `MockSource`.

The two tracks are independent until they meet: host stage H7 == BRINGUP stage 4.
Everything before that can be built and tested with the board still unsoldered.

Same rules as BRINGUP.md. Each stage ends in a **pass/fail test**. Do not start a
stage until the previous one passes.

---

## How to use this document if you don't know what you want to build yet

You don't have to. Two separate things get confused under the word "spec":

**The architecture is already decided, and it's sound.** `protocol.py` is the
wire contract. `EventSource` is the input seam — hardware, mock, anything else
behind one interface. `Action` + `registry` is the output seam. `MockSource`
means the entire host track proceeds with no board attached. None of that needs
re-deciding, and none of the stages below ask you to.

**What is genuinely unspecified is *behaviour*** — what the 9 buttons and 3
encoders actually *do*. That is a question about your own workflow, not about
software design, and you can answer it today. Fill in the table below.

Anything past the next unpassed stage is allowed to be vague. That is the point
of gates.

---

## Fill this in first

The equivalent of BRINGUP.md's `GP__` pin table. Button ids are `0..8` and match
the UI grid (`row, col = divmod(i, 3)`), so id 0 is top-left.

| Button | Action | Notes |
|---|---|---|
| 0 |Ctrl C||
| 1 |Ctrl | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |
| 6 | | |
| 7 | | |
| 8 | | |

| Encoder | Turn does | Push does (if wired) |
|---|---|---|
| 0 | | |
| 1 | | |
| 2 | | |

**`pycaw` is in `pyproject.toml`, which implies the sliders are meant for
per-app volume** (Spotify / Discord / browser, mixer-style). Confirm or change
that — it is currently an assumption sitting in a dependency list, and stage H8
is built entirely on it.

You do not need all twelve rows to start. **Two buttons and one encoder is enough
to get through H6.** Fill the rest in when you have used it for a week and know
what you actually reach for.

---

## Stage H0 — Repo hygiene (15 minutes, do this first)

BRINGUP.md already flags this and it still hasn't happened.

1. **`git init`.** There is real work here now — BRINGUP.md, `protocol.py`, a
   built blinky. Every stage below is a natural commit, and firmware bring-up is
   exactly where `git bisect` between "worked" and "doesn't" pays for itself.
2. **Check `git status` before the first commit.** `firmware/blinky/build/`
   contains a vendored copy of the pico-sdk. The bare `build/` rule in
   `.gitignore` should catch it — *confirm that it does* rather than assuming.
   Add `firmware/.build/` and `*.uf2` while you are there.
3. **Delete `main.py` and `Gui.py`.** Both are 0 bytes. The real entry point is
   `macropad/__main__.py`, declared in `pyproject.toml` as `macropad`.

**Pass:** `git status` on a fresh clone-equivalent shows no `pico-sdk`, no
`__pycache__`, no `.venv`, and the repo is under ~1 MB.

---

## Stage H1 — Widen the event type *before* anything depends on it

**Do this now, not at BRINGUP stage 5.** BRINGUP.md orders encoders last because
it is sequenced by *hardware* dependency. The host has a different constraint:
today `parse()` returns `Optional[ButtonEvent]`, `EventCallback` is
`Callable[[ButtonEvent], None]`, and the only consumer in the entire codebase is
`mock.py`. Widening costs an hour today. After H4/H5/H6 exist it touches the
engine, the config loader, the UI and both sources.

This is the one genuine "you will regret it later" item in the repo.

Add to `protocol.py`:

```
byte 0 : MSG_ENCODER (0x04)
byte 1 : encoder id (0..2)
byte 2 : delta, int8 two's complement (+1 / -1 per detent)
```

Then widen `parse()` to return `Optional[Event]` where
`Event = Union[ButtonEvent, EncoderEvent]`, and widen `EventCallback` in
`sources/base.py` to match. Give `MockSource` a `turn(encoder_id, delta)` that
goes through `build_encoder_report` → `parse`, the same way `press()` already
does.

**Failure modes, in the order they will bite you:**

- **Encoder reports vanish silently.** `parse()` returns `None` for unknown
  message types and `_emit()` drops `None` without a word. If you add the
  constant but not the parse branch, turning a knob does *nothing* and produces
  *no error* — the worst possible debugging signal. Add the branch first.
- **Counter-clockwise reads as +255.** `report[2]` is an unsigned byte. Decode
  with `struct.unpack('b', report[2:3])[0]`, not `report[2]`.
- **Callbacks blow up only when a knob is turned.** A handler written as
  `def on_event(e): do(e.button_id)` type-checks against nothing and raises
  `AttributeError` on the first encoder event. Branch on type at the top of every
  handler, from the start.
- **Absolute state in the firmware.** The firmware sends a *delta per detent*;
  the host accumulates and clamps to 0-100. Keep the position on the host or the
  sliders drift out of sync on every reconnect — and you will be reconnecting
  constantly.

**Pass:** `MockSource.turn(0, -1)` delivers an `EncoderEvent(encoder_id=0,
delta=-1)` — negative, not 255 — and `MockSource.press(0)` still delivers a
`ButtonEvent` unchanged.

---

## Stage H2 — Tests for the wire format

`pytest` is already in the dev extras with no `tests/` directory. This is a
one-file stage and it is worth more than it looks: **the firmware mirrors
`protocol.py`'s constants by hand.** There is no compiler checking that the two
ends agree. These tests are the only thing that will notice if a message type
gets renumbered.

`tests/test_protocol.py`, covering:

- Round-trip: `parse(build_button_report(id, edge))` equals the original, for
  every edge.
- **Assert on the bytes, not just the dataclass** — `report[0] == 0x01`,
  `len(report) == 32`. A test that only checks `event.button_id` passes happily
  after someone renumbers `MSG_BUTTON_EVENT`, which is precisely the break that
  would take a day to find against real firmware.
- Signed encoder delta at the boundaries: `-1`, `+1`, `-128`, `+127`.
- Junk in, `None` out: wrong size, unknown message type, empty bytes.

**Failure mode:** tests written against `MockSource`'s public API only. Those
prove the mock is self-consistent, which is not the same as proving the byte
layout is what the firmware will send. Test `build_*`/`parse` directly.

**Pass:** `pytest` is green, and flipping any constant in `protocol.py` by hand
turns it red.

---

## Stage H3 — Two real actions

`macropad/actions/__init__.py` imports `keystroke` and `launch`. **Neither file
exists**, so `import macropad.actions` raises `ImportError` today. It is latent,
not live — `__main__.py` reaches `ui.main_window` and never touches `actions`,
so `python -m macropad` still opens the window. It becomes live the moment the
engine lands in H4.

Write the two the `__init__` already promises:

- `keystroke.py` — send a key chord via `pynput`. `TYPE = "keystroke"`.
- `launch.py` — start a program or open a file/URL. `TYPE = "launch"`.

Both already have their shape dictated by `base.py`: `TYPE`, `LABEL`, `fields()`,
`execute()`, `describe()`, `to_params()`, `from_params()`, and the `@register`
decorator.

**Failure modes:**

- **Stuck modifiers.** If `execute()` presses Ctrl, presses Shift, then raises
  before releasing them, the OS thinks Ctrl+Shift are held down *system-wide*
  until you press and release them physically. Release in a `finally`. This one
  is genuinely alarming the first time and takes a reboot to figure out if you
  don't know the cause.
- **Blocking on launch.** `subprocess.run()` waits for the program to exit and
  will freeze whatever thread the engine runs on. Use `subprocess.Popen` (or
  `os.startfile` on Windows, which handles documents and URLs too).
- **`TYPE` strings are permanent.** They are written into the saved config in
  H5. Renaming `"keystroke"` to `"keys"` later silently orphans every existing
  mapping. Pick them now and treat them as frozen.

**Pass:** `python -c "import macropad.actions"` succeeds, and a two-line script
that builds a keystroke action from a dict and calls `execute()` types into
Notepad.

---

## Stage H4 — The engine (the actual missing middle)

Both seams exist. **Nothing joins them.** No file in the repo subscribes to an
`EventSource` and dispatches to an `Action`. This is the hole.

`macropad/engine.py`: holds the button-id → Action mapping, subscribes via
`source.on_event`, looks up and runs.

**Failure modes, all three of which you will hit:**

- **Every action fires twice.** `MockSource.press()` emits press *and* release,
  by design. An engine that dispatches on every `ButtonEvent` runs the action on
  both edges. Filter on `event.is_press`. (Decide deliberately whether any action
  should fire on release or hold — most should not.)
- **One bad action kills the app.** `base.py`'s docstring already promises "the
  engine catches and logs errors." Nothing implements that promise yet. Wrap
  `execute()` in try/except and log; an unhandled exception on the HID read
  thread in H7 takes the read loop down with it and the app just goes quiet.
- **A slow action stalls the event stream.** Launching an app takes hundreds of
  milliseconds. On the HID read thread that means dropped keypresses. Either
  dispatch to a worker thread or keep every `execute()` strictly non-blocking —
  decide which, and write it down, because "sometimes a keypress doesn't
  register" is miserable to diagnose after the fact.

**Pass:** a headless script wires `MockSource` to the engine with two mapped
buttons, calls `press(0)` and `press(1)`, and each action runs **exactly once**.

---

## Stage H5 — Config persistence

`to_dict` / `from_params` / `action_from_dict` are all written and entirely
unused. Give them a file.

Decide and record: **where**, **when written**, **what format**.

- **Where:** `%APPDATA%\MacroPad Companion\config.json`
  (`os.environ["APPDATA"]`). **Not next to the executable.** `pyproject.toml`
  already lists `pyinstaller` — a frozen app installed under `Program Files`
  cannot write to its own directory, and this fails only in the packaged build,
  never in development.
- **When:** on edit, not on exit. An app that loses your mappings when it is
  force-quit is an app you stop trusting.
- **Format:** `{"version": 1, "buttons": {"0": {"type": "...", ...}}, ...}`.
  Include the version key now, even though it is useless today — adding one to
  files already in the wild is much worse.

**Failure modes:**

- **Half-written config on crash.** Writing directly into `config.json` and
  dying mid-write leaves invalid JSON and the app won't start. Write to
  `config.json.tmp`, then `os.replace()` — atomic on Windows.
- **One unknown action type kills the whole config.** `action_from_dict` raises
  `KeyError` on an unrecognised `type`. Loaded in a plain loop, a single bad
  entry loses *all* of your mappings. Catch per-entry, skip, log, keep the rest.
- **JSON keys are strings.** `{"0": ...}` comes back as `"0"`, not `0`. Convert
  on load or every lookup misses silently.

**Pass:** map two buttons, kill the process with the task manager, restart — both
mappings are there. Then hand-edit one entry to `"type": "nonsense"` and confirm
the *other* mapping still loads.

---

## Stage H6 — Wire the UI (the payoff gate)

`main_window.py` says it is "intentionally logic-free scaffolding" and stores
`self.buttons` / `self.sliders` for exactly this. After this stage the app is
genuinely usable with no hardware at all.

**Settle one design question before writing code:** the 3x3 grid currently has
one set of buttons and two jobs — *editing* what a key does, and *simulating* a
key press. Clicking cannot do both. Pick one:

- Left-click simulates, right-click (or double-click) opens the editor; or
- The grid is the editor, and the simulator is a separate small panel.

Either works. Deciding it implicitly, per-widget, does not.

Then: build the action editor form generically from `FieldSpec` — that is what
`fields()`, `kind` and `choices` exist for. Resist writing per-action UI code;
the moment you do, every new action type needs a matching dialog.

**Failure modes:**

- **Touching widgets from the wrong thread.** In H7 events arrive on a
  background thread. Calling `label.setText()` from it is undefined behaviour in
  Qt — usually a crash, sometimes a silent hang, occasionally fine, which is the
  worst outcome because it hides until later. `sources/base.py` already notes
  callbacks "may run on a background thread" and that the Qt layer must marshal.
  **Build the signal bridge now, in H6, while the only source is the mock** — if
  you add it in H7 you will be debugging threading and USB simultaneously, which
  is the exact trap BRINGUP.md is organised to avoid.
- **Sliders fighting the user.** Once encoders drive slider values, a
  `valueChanged` handler that writes back into the source will oscillate. Use
  `blockSignals()` around programmatic updates.

**Pass:** launch the app, assign "launch Notepad" to button 0 through the GUI,
click/simulate it, Notepad opens. Close, reopen, it is still assigned.

---

## Stage H7 — Meet the hardware

This is **BRINGUP.md stage 4** — `macropad/sources/hid_source.py`. Do not
duplicate the detail here; it is already written up there, including the two
gotchas that account for most "connected but no events" reports (open by usage
page `0xFF60`/`0x61`, not VID/PID; Windows writes need a leading report-ID byte).

The one thing worth restating: because everything above was built against
`EventSource`, this stage should be a **single new file and one line changed** —
whichever line constructs `MockSource()`. If it turns out to be more than that,
something leaked through the seam, and that is worth fixing rather than working
around.

**Pass:** swap `MockSource` for `HidSource`, press a physical key, and the
action that H6 assigned runs.

---

## Stage H8 — Encoders to per-app volume

Only after H1's widened event type has been carrying encoder events through the
mock for several stages.

Host accumulates: `value = clamp(value + delta, 0, 100)` → set the slider → set
the volume via `pycaw`.

**Failure modes specific to `pycaw`:**

- **COM must be initialised per-thread.** `pycaw` is COM-based (`comtypes`).
  Calling it from the engine or HID thread without `CoInitialize()` on *that*
  thread fails with an opaque COM error. Initialise per-thread, or marshal
  volume calls onto a thread that has.
- **Sessions are per-process and they die.** An `AudioSession` for Spotify
  becomes invalid the moment Spotify closes, and a *new* session appears when it
  reopens. Caching the session object means the slider silently stops working
  after the first restart. Re-resolve by process name on each change.
- **Multi-process apps.** Browsers run audio in a child process, so matching
  `chrome.exe` may find several sessions or the wrong one. Decide whether to set
  all matches or just the loudest.

**Pass:** turn encoder 0, the matching slider moves, and the target app's level
moves in the Windows volume mixer — with the target app closed and reopened at
least once during the test.

---

## What to deliberately not build yet

Each of these is cheap later and expensive as a distraction now:

- **LEDs.** `MSG_SET_LED` (0x10) is defined and has no firmware side. BRINGUP.md
  is right: do not bring up LEDs and Raw HID together.
- **Layers / profiles / per-app mappings.** Easy to add once config has a
  `version` key. Impossible to design well before you have used nine fixed
  buttons for a fortnight.
- **Packaging.** `pyinstaller` is in the dev extras. It belongs after H7, and it
  will surface exactly one real bug — the config path from H5 — which is why H5
  specifies `%APPDATA%`.
- **Anything cross-platform.** `pycaw` is Windows-only and so is the audio half
  of the design. The `EventSource`/`Action` seams keep the door open; walking
  through it now buys nothing.

---

## Notes

- **Python 3.9** (`requires-python = ">=3.9"`, venv is 3.9.13) is in security-fix
  only mode. Not urgent — `from __future__ import annotations` is already used
  throughout, so the modern syntax works. But if you are going to move, move
  before the codebase grows past H6.
- Every stage above is one commit. Tag the one where H7 passes — that is the
  first point the whole system exists end to end, and it is the state you will
  want to get back to after the first ambitious refactor.
