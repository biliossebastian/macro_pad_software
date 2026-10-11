"""Raw HID wire protocol shared by the companion app and the QMK firmware.

This is the single source of truth for the byte layout that travels over the
Raw HID interface. Both the real :class:`~macropad.sources.hid_source.HidSource`
and the :class:`~macropad.sources.mock.MockSource` build/parse bytes through the
functions here, so the mock exercises the *exact* code the hardware will use.

When you wire up the firmware later, mirror these constants in the keyboard's
``raw_hid_receive`` / report-sending code and the two ends will agree.

Report layout (fixed 32 bytes, matching QMK's ``RAW_EPSIZE``)
-------------------------------------------------------------
Device -> Host, button event::

    byte 0 : MSG_BUTTON_EVENT (0x01)
    byte 1 : button id (0..255)
    byte 2 : edge      (EDGE_RELEASE=0 / EDGE_PRESS=1 / EDGE_HOLD=2)
    byte 3.. : reserved (zero-filled)

Host -> Device (defined now, used later for LED feedback etc.)::

    byte 0 : MSG_SET_LED (0x10)
    byte 1 : led index
    byte 2 : r
    byte 3 : g
    byte 4 : b
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

#: Fixed report size in bytes. QMK's default Raw HID endpoint size is 32.
REPORT_SIZE = 32

# --- Message types (byte 0) -------------------------------------------------
# Device -> Host
MSG_BUTTON_EVENT = 0x01
MSG_PONG = 0x03
# Host -> Device
MSG_PING = 0x02
MSG_SET_LED = 0x10

# --- Button edges (byte 2 of a button event) --------------------------------
EDGE_RELEASE = 0x00
EDGE_PRESS = 0x01
EDGE_HOLD = 0x02

_EDGE_NAMES = {EDGE_RELEASE: "release", EDGE_PRESS: "press", EDGE_HOLD: "hold"}


@dataclass(frozen=True)
class ButtonEvent:
    """A single button state change decoded from a Raw HID report."""

    button_id: int
    edge: int

    @property
    def is_press(self) -> bool:
        return self.edge == EDGE_PRESS

    @property
    def is_release(self) -> bool:
        return self.edge == EDGE_RELEASE

    @property
    def edge_name(self) -> str:
        return _EDGE_NAMES.get(self.edge, f"0x{self.edge:02x}")

    def __str__(self) -> str:
        return f"button {self.button_id} {self.edge_name}"


def build_button_report(button_id: int, edge: int = EDGE_PRESS) -> bytes:
    """Build a 32-byte device->host button-event report.

    Used by the firmware (conceptually) and by the mock source so tests and the
    simulator drive the real :func:`parse` path.
    """
    if not 0 <= button_id <= 0xFF:
        raise ValueError(f"button_id out of range: {button_id}")
    if edge not in _EDGE_NAMES:
        raise ValueError(f"unknown edge: {edge}")
    report = bytearray(REPORT_SIZE)
    report[0] = MSG_BUTTON_EVENT
    report[1] = button_id
    report[2] = edge
    return bytes(report)


def parse(report: bytes) -> Optional[ButtonEvent]:
    """Decode a raw report into a :class:`ButtonEvent`, or ``None``.

    Returns ``None`` for reports that are the wrong size or carry a message type
    this version does not understand, so unknown traffic is ignored rather than
    crashing the listener.
    """
    if report is None or len(report) < 3:
        return None
    if report[0] != MSG_BUTTON_EVENT:
        return None
    return ButtonEvent(button_id=report[1], edge=report[2])


def build_set_led(led_index: int, r: int, g: int, b: int) -> bytes:
    """Build a 32-byte host->device LED report (for future firmware support)."""
    report = bytearray(REPORT_SIZE)
    report[0] = MSG_SET_LED
    report[1] = led_index & 0xFF
    report[2] = r & 0xFF
    report[3] = g & 0xFF
    report[4] = b & 0xFF
    return bytes(report)
