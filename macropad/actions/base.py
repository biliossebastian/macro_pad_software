"""Base class and field metadata for actions.

An :class:`Action` knows how to (a) run itself, (b) serialize to/from a plain
dict for the JSON config, and (c) describe its editable fields so the GUI can
build an editor form generically — no per-action UI code required.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class FieldSpec:
    """Describes one editable parameter of an action, for the GUI form."""

    name: str
    label: str
    kind: str = "text"  # "text" | "multiline" | "combo" | "file"
    placeholder: str = ""
    help: str = ""
    choices: List[str] = field(default_factory=list)


class Action(ABC):
    """Something that happens when a mapped button is pressed."""

    #: Stable identifier stored in the config; must be unique across actions.
    TYPE: str = ""
    #: Human-readable label shown in the action-type picker.
    LABEL: str = ""

    @classmethod
    def fields(cls) -> List[FieldSpec]:
        """Editable parameters, in display order. Override in subclasses."""
        return []

    @abstractmethod
    def execute(self) -> None:
        """Perform the action. May raise; the engine catches and logs errors."""

    @abstractmethod
    def describe(self) -> str:
        """Short one-line summary for the mapping list, e.g. ``Ctrl+Shift+T``."""

    # -- serialization -------------------------------------------------------
    @abstractmethod
    def to_params(self) -> Dict[str, Any]:
        """Return just this action's parameters (without the ``type`` key)."""

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"type": self.TYPE}
        data.update(self.to_params())
        return data

    @classmethod
    @abstractmethod
    def from_params(cls, params: Dict[str, Any]) -> "Action":
        """Build an instance from a params dict (inverse of :meth:`to_params`)."""
