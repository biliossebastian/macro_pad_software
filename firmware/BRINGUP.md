# Macro pad bring-up plan

Minimum path from "RP2040 enumerates" to "companion app reacts to a keypress."

Hardware as confirmed: RP2040, 3x3 key matrix with diodes, 3 rotary encoders,
BOOT button present, Raw-HID-only (the pad sends **no** keystrokes to the OS —
the companion app owns all behaviour).

Each stage ends in a **pass/fail test**. Do not start a stage until the previous
one passes. Most bring-up pain comes from debugging two unknowns at once.

---

## Fill this in first (from the schematic)

Everything below is parameterized on the pinout. It is captured from the Altium
netlist in [HARDWARE.md](../HARDWARE.md). Use that, not memory.

**Diode direction:** anode at switch, cathode at row = `COL2ROW`. The opposite is
`ROW2COL`. Read it off the schematic symbol; guessing costs an hour in stage 2.

**Encoder push switches:** if the encoders have integrated push buttons, they are
almost certainly a 4th matrix row (3 cols x 4 rows = 12 positions, button ids
9/10/11) or three direct GPIOs. Decide which, because it changes `MATRIX_ROWS`
and the button-id map the host expects.

---

## Stage 0 — Prove the QSPI flash (5 minutes, do this first)

**"The RP2040 is detected" does not mean the board is good.** Enumerating as the
`RPI-RP2` mass-storage drive proves the 3V3 rails, the 12 MHz crystal, the USB
D+/D- routing and the boot ROM. It proves *nothing* about the external QSPI
flash, because the boot ROM runs entirely from internal ROM/SRAM. A board with
dead, unrouted, or rotated flash enumerates as `RPI-RP2` forever and looks
identical to a perfect board.

1. Hold BOOT, plug in, confirm the `RPI-RP2` drive mounts.
2. Drag `flash_nuke.uf2` (Raspberry Pi's official flash eraser) onto it.
   **The drive will unmount and then come straight back — that is expected.**
   `flash_nuke` erases flash and deliberately returns to BOOTSEL. This step has
   no pass/fail of its own; it just clears any garbage so step 3 is a clean test.
3. Drag any valid UF2 onto it. A stock Pico `blink.uf2` is fine — it targets
   GP25, which your custom board probably has no LED on, but that does not
   matter: the test below does not need to see it blink.

**The test is step 3 only.**

**Pass:** after step 3 the `RPI-RP2` drive unmounts and **stays gone**. The chip
is running from flash.

**Fail:** after step 3 the drive unmounts and immediately reappears. The chip
fell back to BOOTSEL because it could not read a valid image. That is a flash
fault — check CS/SCK/D0-D3 routing, part orientation, and solder joints. Stop
and fix the hardware; no amount of firmware work will get past this.

This is the one misdiagnosis that costs days, and it takes five minutes to rule
out.

---

## Stage 0.5 — Guarantee an escape route

You have a BOOT button, so you are not at risk of a hard brick. Still, put these
in the very first firmware — they cost nothing and save reaching for the button
on every single flash cycle:

- `QK_BOOT` on one key (or a two-key combo / a held layer, so you cannot hit it
  by accident).
- In `config.h`:

  ```c
  #define RP2040_BOOTLOADER_DOUBLE_TAP_RESET
  #define RP2040_BOOTLOADER_DOUBLE_TAP_RESET_TIMEOUT 500U
  ```

---

## Stage 1 — Minimal QMK keyboard, plain keycodes

Set up the toolchain (QMK MSYS on Windows) and keep the keyboard definition
**inside this repo**, so `protocol.py`'s claim to be "the single source of truth
for both ends" is actually true:

```
qmk setup
qmk config user.overlay_dir="<path-to-repo>/firmware"
qmk new-keyboard          # name: macropad, MCU: RP2040
```

That gives you `firmware/keyboards/macropad/`. Edit `keyboard.json`:

```jsonc
{
  "processor": "RP2040",
  "bootloader": "rp2040",
  "board": "GENERIC_RP_RP2040",
  "diode_direction": "COL2ROW",              // or ROW2COL
  "matrix_pins": {
    "rows": ["GP__", "GP__", "GP__"],
    "cols": ["GP__", "GP__", "GP__"]
  },
  "usb": { "vid": "0xFEED", "pid": "0x0001", "device_version": "0.0.1" }
}
```

> Verify the exact schema keys against the QMK docs for the revision you check
> out — the data-driven format has moved over versions, and a stale snippet
> silently produces a board that builds but does nothing.

Two things `qmk new-keyboard` generates that you must reconcile:

- **The `layouts` block.** The template emits one sized to whatever it asked you
  for. If its key count does not match the 3x3 you hand-edit into `matrix_pins`,
  stage 1 fails to compile with a confusing error. Fix the layout, not the pins.
- **`ENCODER_MAP_ENABLE`.** If the template turns this on, `encoder_update_user()`
  never fires and stage 2's encoders look dead. Check for it *before* you start
  debugging wiring.

Put the VID/PID in [protocol.py](../macropad/protocol.py) as constants too. It is
the stated single source of truth for both ends, and stage 4's device lookup
needs them — otherwise the magic numbers get duplicated silently.

**The first keymap is deliberately NOT the final one.** Map the nine keys to
`KC_A`..`KC_I`, no Raw HID, no encoders. This isolates matrix wiring from
protocol bugs.

```
qmk compile -kb macropad -km default
```

**Pass:** the UF2 flashes, the board boots (drive stays unmounted), and tapping
keys types `a`..`i` into Notepad.

---

## Stage 2 — Verify the matrix and the encoders

Almost every board has at least one wrong pin here. Enable the console so you can
see what the firmware thinks is happening:

- `rules.mk`: `CONSOLE_ENABLE = yes`
- Run `qmk console` while pressing keys.

Diagnose in this order:

1. **Nothing at all registers** — wrong row/col pin lists, or the whole matrix is
   on the wrong pins.
2. **A whole row or column fires together** — rows and cols are swapped.
3. **Keys register but ghost when two are held** — wrong `diode_direction`.
4. **Keys are transposed** — row/col lists are swapped in `keyboard.json`.

Then add the encoders to `keyboard.json`:

```jsonc
"features": { "encoder": true },
"encoder": {
  "rotary": [
    { "pin_a": "GP__", "pin_b": "GP__" },
    { "pin_a": "GP__", "pin_b": "GP__" },
    { "pin_a": "GP__", "pin_b": "GP__" }
  ]
}
```

Temporarily map them to volume up/down via `encoder_update_user()` so you can
confirm direction and detent count by ear.

**Pass:** all 9 keys (plus any encoder pushes) report the correct unique position,
and all 3 encoders turn in the expected direction.

- **If an encoder is backwards,** swap `pin_a`/`pin_b`. Do not "fix" it on the host.
- **If one detent gives 2 or 4 steps,** set `ENCODER_RESOLUTION` (commonly 2 or 4)
  rather than dividing on the host.

---

## Stage 3 — Raw HID, ping/pong before anything else

`rules.mk`: `RAW_ENABLE = yes`. The defaults `RAW_USAGE_PAGE 0xFF60` /
`RAW_USAGE_ID 0x61` are what the host will filter on — leave them alone.

Implement in this order, testing each:

1. **Ping/pong.** `raw_hid_receive()` sees `MSG_PING` (0x02) and replies with a
   32-byte report starting `MSG_PONG` (0x03). This proves both directions of the
   pipe with zero application logic in the way.
2. **Button events.** In `process_record_user()`, translate
   `record->event.key.row/col` into a button id and send
   `[MSG_BUTTON_EVENT, id, EDGE_PRESS|EDGE_RELEASE, 0...]`. Use explicit custom
   keycodes (`MP_BTN0`..`MP_BTN8` off `SAFE_RANGE`) rather than `KC_NO`, so the
   intent is readable and nothing leaks to the OS. Return `false` so QMK does not
   also emit a keycode.

**Button id must be `row * MATRIX_COLS + col`.** The GUI in
[ui/main_window.py](../macropad/ui/main_window.py) builds its grid with
`row, col = divmod(i, 3)` and treats *button id == grid index*. That assumption
is currently only implicit in the UI code — the firmware has to match it, or
key 3 will light up cell 1.

Mirror the constants from [protocol.py](../macropad/protocol.py) exactly:
`REPORT_SIZE 32`, `MSG_BUTTON_EVENT 0x01`, `MSG_PING 0x02`, `MSG_PONG 0x03`,
`MSG_SET_LED 0x10`, `EDGE_RELEASE 0x00`, `EDGE_PRESS 0x01`, `EDGE_HOLD 0x02`.

**Test with a ~20-line `hidapi` script, not the GUI.** Adding Qt to the debug loop
at this point means three layers of unknowns.

**Pass:** the script prints a press and a release report for every key tap.

---

## Stage 4 — Host side: `macropad/sources/hid_source.py`

This file is referenced throughout [protocol.py](../macropad/protocol.py) but does
not exist yet. It subclasses `EventSource` from
[sources/base.py](../macropad/sources/base.py), runs a blocking read loop on a
background thread, and calls `self._emit(protocol.parse(report))`.

Two gotchas account for most "connected, but no events" reports:

- **Open by usage page, not by VID/PID.** QMK exposes several HID interfaces on
  one VID/PID. Filter `hid.enumerate()` for `usage_page == 0xFF60 and usage ==
  0x61` and open *that* interface's `path`. Opening by VID/PID alone grabs the
  keyboard interface and reads nothing, forever, with no error.
- **On Windows, writes need a leading report-ID byte.** Send 33 bytes
  (`b"\x00" + report`) even though reads return 32. Getting this wrong makes
  `write()` fail or silently no-op.

Also handle reconnects — the read loop should survive unplug/replug rather than
killing the thread, since you will be reflashing constantly.

**Pass:** the GUI's status goes to "connected", and physical key presses drive the
same code path `MockSource` already exercises.

---

## Stage 5 — Encoders over Raw HID (protocol change needed)

`protocol.py` has no message type for the encoders, and the three 0-100
`QSlider`s in [ui/main_window.py](../macropad/ui/main_window.py) currently have
nowhere to get a value from.

**Encoders are relative; sliders are absolute.** The firmware sends a delta per
detent and the *host* accumulates and clamps. Do not keep absolute state in the
firmware — it will drift out of sync with the UI on every reconnect.

Proposed layout (`0x04` is free — no collision with `0x01`/`0x02`/`0x03`/`0x10`):

```
byte 0 : MSG_ENCODER (0x04)
byte 1 : encoder id (0..2)
byte 2 : delta, int8 two's complement (typically +1 / -1 per detent)
```

Firmware: `encoder_update_user(index, clockwise)` sends one report per detent.
Host: `value = clamp(value + delta, 0, 100)`, then update the slider.

**This is an architectural edit, not a constant addition — scope it honestly.**
Today `parse()` returns `Optional[ButtonEvent]` and bails on
`report[0] != MSG_BUTTON_EVENT`, and `_emit()` drops `None` silently. So an
encoder report is **swallowed with no error** until you either widen `parse()`'s
return type or give it a second entry point, *and* widen
`EventCallback = Callable[[ButtonEvent], None]` through
[sources/base.py](../macropad/sources/base.py). Plan for touching `protocol.py`,
`sources/base.py`, `hid_source.py`, `mock.py` and the UI.

**Decode byte 2 as signed.** `report[2]` reads 0-255, so a counter-clockwise
detent arrives as `255`, not `-1`. Use `struct.unpack('b', ...)` or
`v - 256 if v > 127 else v`.

Send *only* on change. One report per detent is naturally rate-limited, which is
exactly why encoders are easier here than potentiometers would have been — pots
would have needed ADC polling, a deadband, and jitter filtering.

---

## Notes

- **This directory is not a git repository.** Before stage 1, `git init`. Firmware
  bring-up is where bisecting between "worked" and "doesn't" pays for itself, and
  you will otherwise lose a known-good `keyboard.json` to a bad edit.
- **Add `firmware/.build/` and `*.uf2` to `.gitignore`.**
- **`MSG_SET_LED` (0x10) is defined but has no firmware side.** That is fine —
  leave it unimplemented until the rest works. Do not bring up LEDs and Raw HID
  at the same time.
