"""The abstract event source the rest of the app is written against."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, List, Optional

from ..protocol import ButtonEvent

EventCallback = Callable[[ButtonEvent], None]
StatusCallback = Callable[[str], None]


class EventSource(ABC):
    """Produces button events from somewhere (hardware, mock, network, ...).

    Concrete sources call :meth:`_emit` whenever a button event occurs and
    :meth:`_set_status` when their connection state changes. Both may run on a
    background thread, so callbacks must be cheap or marshal to the UI thread
    themselves (the Qt layer does exactly that).
    """

    #: Human-readable name shown in the UI.
    name: str = "event source"

    def __init__(self) -> None:
        self._event_cbs: List[EventCallback] = []
        self._status_cbs: List[StatusCallback] = []
        self._status: str = "stopped"

    # -- subscription --------------------------------------------------------
    def on_event(self, cb: EventCallback) -> None:
        self._event_cbs.append(cb)

    def on_status(self, cb: StatusCallback) -> None:
        self._status_cbs.append(cb)

    @property
    def status(self) -> str:
        return self._status

    # -- lifecycle (implemented by subclasses) -------------------------------
    @abstractmethod
    def start(self) -> None:
        """Begin producing events. Must be safe to call once."""

    @abstractmethod
    def stop(self) -> None:
        """Stop producing events and release resources. Must be idempotent."""

    def send(self, report: bytes) -> None:  # noqa: D401 - optional capability
        """Send a raw host->device report. No-op unless the source supports it."""

    # -- helpers for subclasses ---------------------------------------------
    def _emit(self, event: Optional[ButtonEvent]) -> None:
        if event is None:
            return
        for cb in list(self._event_cbs):
            cb(event)

    def _set_status(self, status: str) -> None:
        self._status = status
        for cb in list(self._status_cbs):
            cb(status)
