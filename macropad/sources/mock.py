"""A simulated event source for developing the app with no hardware attached.

Crucially, :meth:`MockSource.press` builds a *real* 32-byte report via
:func:`macropad.protocol.build_button_report` and decodes it through
:func:`macropad.protocol.parse` — the same path the real HID source uses. So the
only thing left untested until the firmware exists is opening/reading the USB
device itself; the protocol and everything downstream is already exercised.
"""

from __future__ import annotations

from .. import protocol
from .base import EventSource


class MockSource(EventSource):
    """Emits button events on demand instead of from USB.

    The GUI's simulator panel (and unit tests) call :meth:`press`/:meth:`release`
    to inject events exactly as if a physical key were tapped.
    """

    name = "Simulator (no hardware)"

    def start(self) -> None:
        self._set_status("connected")

    def stop(self) -> None:
        self._set_status("stopped")

    def press(self, button_id: int) -> None:
        """Simulate a full tap (press + release) of ``button_id``."""
        self._inject(button_id, protocol.EDGE_PRESS)
        self._inject(button_id, protocol.EDGE_RELEASE)

    def press_only(self, button_id: int) -> None:
        self._inject(button_id, protocol.EDGE_PRESS)

    def release(self, button_id: int) -> None:
        self._inject(button_id, protocol.EDGE_RELEASE)

    def _inject(self, button_id: int, edge: int) -> None:
        report = protocol.build_button_report(button_id, edge)
        self._emit(protocol.parse(report))
