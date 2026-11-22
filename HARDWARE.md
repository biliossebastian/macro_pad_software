# Macro pad hardware I/O reference

Every input and output on the board, and how it reaches the RP2040. Use this
file instead of opening Altium.

**Source:** `../PCB_Designs/macro-pad/macro_pad.PcbDoc` netlist (saved
2026-11-21), the `LEDs.SchDoc` / `macro_pad.SchDoc` notes, and the
2026-10-27 BOM. If the PCB changes, regenerate this file. Do not edit it by hand
to match the firmware.

The firmware config in [keyboard.json](firmware/keyboards/macropad/keyboard.json)
covers only what QMK needs to know (matrix, encoders, WS2812 pin). It leaves out
LED10, the status LED, the buttons, debug, unused pins and fitting options.

---

## GPIO map

| GPIO | RP2040 pin | Net | Function | Dir | Notes |
|---|---|---|---|---|---|
| GP0 | 2 | C0 | Matrix col 0 | in/out | via R15 27R array |
| GP1 | 3 | C1 | Matrix col 1 | in/out | via R15 |
| GP2 | 4 | C2 | Matrix col 2 | in/out | via R15 |
| GP3 | 5 | R0 | Matrix row 0 | in/out | via R15 |
| GP4 | 6 | R1 | Matrix row 1 | in/out | via R15 |
| GP5 | 7 | R2 | Matrix row 2 | in/out | via R15 |
| GP6 | 8 | — | unused | | |
| GP7 | 9 | — | unused | | |
| GP8 | 11 | Row0_R | Alt route to row 0 | | R21 0R **DNP**; keep high-Z |
| GP9 | 12 | Row1_R | Alt route to row 1 | | R22 0R **DNP**; keep high-Z |
| GP10 | 13 | Row2_R | Alt route to row 2 | | R23 0R **DNP**; keep high-Z |
| GP11 | 14 | Row3_R | **Matrix row 3 (encoder pushes)** | in/out | only connected if R24 (0R, DNP) is fitted by hand |
| GP12–14 | 15–17 | — | unused | | |
| GP15 | 18 | ENC1_A | Encoder 1 A | in | |
| GP16 | 27 | ENC1_B | Encoder 1 B | in | |
| GP17 | 28 | ENC2_A | Encoder 2 A | in | |
| GP18 | 29 | ENC2_B | Encoder 2 B | in | |
| GP19 | 30 | ENC3_A | Encoder 3 A | in | |
| GP20 | 31 | ENC3_B | Encoder 3 B | in | |
| GP21–23 | 32, 34, 35 | — | unused | | |
| GP24 | 36 | → LED_IN | Addressable LED data (LED1–9) | out | R38 27R, then IC2 5 V buffer |
| GP25 | 37 | → D6 | User/status LED (yellow-green) | out | active **high**, R8 1k |
| GP26 | 38 | → LED10 W | LED10 white | out | active **low**, R39 1k, PWM5A |
| GP27 | 39 | → LED10 R | LED10 red | out | active **low**, R41 1k, PWM5B |
| GP28 | 40 | → LED10 B | LED10 blue | out | active **low**, R40 1k, PWM6A |
| GP29 | 41 | → LED10 G | LED10 green | out | active **low**, R42 1k, PWM6B |

Free for expansion: GP6, GP7, GP12, GP13, GP14, GP21, GP22, GP23 (no pads
broken out). GP8–GP10 are free while R21–R23 stay unfitted.

---

## Physical layout (top view, USB edge at top)

```
  [USB-C J2]                     [BOOT B1] [RESET B2]   <- B1/B2/J2 on bottom side
  J3(SWD)  D6  D5  LED10
     (ENC1)        (ENC2)        (ENC3)                 SW10 / SW12 / SW11
     [ K0 ]        [ K1 ]        [ K2 ]                 SW1  SW2  SW3
      LED1          LED2          LED3
     [ K3 ]        [ K4 ]        [ K5 ]                 SW4  SW5  SW6
      LED4          LED5          LED6
     [ K6 ]        [ K7 ]        [ K8 ]                 SW7  SW8  SW9
      LED7          LED8          LED9
```

The encoders are physically **above** the keys. `keyboard.json` puts them at
`y: 3.5`, below the keys. That only changes how configurators draw the board,
not the matrix.

---

## Inputs

### Key matrix: 3 cols × 4 rows, `COL2ROW`

Diode cathodes face the row (D7–D18, 1N4148-type SOD-323F). The keys are MX
switches (SW1–9) in Kailh hot-swap sockets (U1–9). The electrical contact is the
socket.

| Matrix [row, col] | Button id | Part | Position |
|---|---|---|---|
| [0,0] [0,1] [0,2] | 0 1 2 | SW1 SW2 SW3 | top row, L→R |
| [1,0] [1,1] [1,2] | 3 4 5 | SW4 SW5 SW6 | middle row |
| [2,0] [2,1] [2,2] | 6 7 8 | SW7 SW8 SW9 | bottom row |
| [3,0] [3,1] [3,2] | 9 10 11 | ENC1 / ENC2 / ENC3 push | encoder row, L→R |

Button id = `row * 3 + col`. The host GUI assumes this mapping (see
[BRINGUP.md](firmware/BRINGUP.md) stage 3).

Row 3 (the encoder pushes, diodes D16–18) reaches GP11 **only through R24**,
which is DNP on the 2026-10-27 BOM. If R24 is missing, ids 9–11 never fire.

### Rotary encoders: 3× Bourns PEC12R-4225F-S0024

24 detents per revolution, with push switches.

| Encoder | Part | A | B | Push (matrix) |
|---|---|---|---|---|
| ENC1 (left) | SW10 | GP15 | GP16 | [3,0] via D16 |
| ENC2 (middle) | SW12 | GP17 | GP18 | [3,1] via D17 |
| ENC3 (right) | SW11 | GP19 | GP20 | [3,2] via D18 |

The encoder common pin is tied to GND. Each A/B line has a 10k pull-up to 3V3
(R16), a 10k series resistor (R17) and 10 nF to GND (C25/C26), which gives an RC
debounce of about 0.1 ms. The internal pull-ups are not needed.

Note the designator order: the middle encoder is SW**12** and the right encoder
is SW**11**.

### Buttons (not GPIO)

| Part | Function | Net |
|---|---|---|
| B1 | BOOTSEL. Hold it while plugging in to enter the UF2 bootloader. | QSPI_SS via R14 1k |
| B2 | RESET | RUN (R11 10k pull-up, C20) |

Double-tapping RESET also enters the bootloader (set in `config.h`).

---

## Outputs

### Addressable RGB, LED1–LED9 (SK6812-mini style, 5 V)

- Data: GP24 → R38 27R → IC2 → LED1 DIN → … → LED9. LED9 DOUT is not
  connected.
- Chain order matches button id order: LED*n* sits under key *n−1*, row-major,
  not serpentine.
- IC2 is a single-gate buffer powered from 5 V that level-shifts the data line.
  The BOM MPN is **SN74LVC1G126** (pin 1 OE is tied high). The schematic
  comment wrongly says `SN74LVC1G175`.
  - Caveat: at VCC = 5 V, LVC V<sub>IH</sub> is 0.7 × VCC = 3.5 V, so a 3.3 V
    input is marginal. If LEDs glitch, suspect this.
- Power: the 5V0_LEDs rail comes from USB 5 V through R37 (a 0R 1206 jumper on
  the PCB; the BOM lists a 0R1 1210). Each LED has a 100 nF capacitor.
- Firmware: `ws2812.driver = vendor` (PIO), `rgblight.led_count = 9`.

### LED10: discrete RGBW (Dialight 599-2310-427F, 3030)

Common anode at 3V3, so each channel lights when its pin is driven **low**.
There is 1k in series per channel. All four pins can do PWM.

| Channel | GPIO | PWM slice |
|---|---|---|
| R | GP27 | 5B |
| G | GP29 | 6B |
| B | GP28 | 6A |
| W | GP26 | 5A |

### Single LEDs

| Part | Colour | Driven by | Meaning |
|---|---|---|---|
| D6 | yellow-green | GP25, active high | user/status LED (heartbeat in the test keymap) |
| D5 | blue | 3V3 via R3 | power |
| D22 | yellow-green | 3V3 via R20 (bottom side) | power |

---

## Power, USB, debug, and clock

- **USB-C (J2):** USB 2.0 device. 5.1k CC pull-downs (R9/R10), 27R series
  resistors on D+/D− (R4/R5), TVS diodes D1–D4. No GPIO senses VBUS.
- **3V3:** AMS1117-3.3 LDO (IC1), fed from USB 5 V. The RP2040 core regulator
  provides 1V1.
- **SWD (J3, 3-pin 2.54 mm):** pin 1 SWCLK, pin 2 GND, pin 3 SWDIO.
- **Flash:** W25Q128JV, 16 MB, QSPI (L1).
- **Crystal:** 12 MHz (Y1).
- **Unused ADC pins:** GP26–29 drive LED10, so no ADC inputs are free.
- **Naming trap:** D19, D20 and D21 are 1 µF capacitors, not diodes.

---

## Fitting options (DNP on the 2026-10-27 BOM)

| Part | Effect when fitted |
|---|---|
| R24 0R | Connects GP11 to row 3. **Needed for the encoder pushes.** |
| R21–R23 0R | Also connect GP8–GP10 to rows 0–2. Only fit these if you move the rows off GP3–GP5. |
| C21–C24 | 100 nF filter caps on GP8–GP11 (debug filter, per the schematic note) |
