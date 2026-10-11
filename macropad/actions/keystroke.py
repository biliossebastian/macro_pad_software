"""Send a key chord (e.g. ``ctrl+c``) to whichever window has focus."""

from __future__ import annotations

from contextlib import ExitStack
from typing import Any, Dict, List, Union

from pynput.keyboard import Controller, Key, KeyCode

from .base import Action, FieldSpec
from .registry import register

_MODIFIERS = {
    "ctrl": Key.ctrl,
    "control": Key.ctrl,
    "shift": Key.shift,
    "alt": Key.alt,
    "win": Key.cmd,
    "cmd": Key.cmd,
}

_keyboard = Controller()


def _parse_key(name: str) -> Union[Key, KeyCode]:
    """Map one token of a chord to a pynput key (named key or single char)."""
    name = name.strip().lower()
    if name in _MODIFIERS:
        return _MODIFIERS[name]
    if len(name) == 1:
        return KeyCode.from_char(name)
    try:
        return Key[name]  # e.g. "enter", "esc", "f5", "delete"
    except KeyError:
        raise ValueError(f"unknown key: {name!r}") from None


@register
class KeystrokeAction(Action):
    TYPE = "keystroke"
    LABEL = "Keystroke"

    def __init__(self, keys: str = "ctrl+c") -> None:
        self.keys = keys

    @classmethod
    def fields(cls) -> List[FieldSpec]:
        return [
            FieldSpec(
                name="keys",
                label="Keys",
                placeholder="ctrl+c",
                help="Modifiers and a key joined with '+', e.g. ctrl+shift+t",
            )
        ]

    def execute(self) -> None:
        tokens = [t for t in self.keys.split("+") if t.strip()]
        if not tokens:
            raise ValueError("empty key chord")
        *mods, final = (_parse_key(t) for t in tokens)
        # ExitStack releases every modifier even if a later step raises, so a
        # failure can never leave Ctrl/Shift stuck down system-wide.
        with ExitStack() as stack:
            for mod in mods:
                stack.enter_context(_keyboard.pressed(mod))
            _keyboard.tap(final)

    def describe(self) -> str:
        return "+".join(t.strip().capitalize() for t in self.keys.split("+"))

    def to_params(self) -> Dict[str, Any]:
        return {"keys": self.keys}

    @classmethod
    def from_params(cls, params: Dict[str, Any]) -> "KeystrokeAction":
        return cls(keys=params.get("keys", "ctrl+c"))
