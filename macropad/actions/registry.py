"""Registry mapping action ``TYPE`` strings to their classes.

Actions register themselves with the :func:`register` decorator. The engine uses
:func:`action_from_dict` to rebuild actions from the JSON config, and the GUI
uses :data:`ACTION_TYPES` to populate the action-type picker.
"""

from __future__ import annotations

from typing import Any, Dict, List, Type

from .base import Action

_REGISTRY: Dict[str, Type[Action]] = {}


def register(cls: Type[Action]) -> Type[Action]:
    """Class decorator: record an action class under its ``TYPE``."""
    if not cls.TYPE:
        raise ValueError(f"{cls.__name__} must define a non-empty TYPE")
    if cls.TYPE in _REGISTRY and _REGISTRY[cls.TYPE] is not cls:
        raise ValueError(f"duplicate action TYPE: {cls.TYPE!r}")
    _REGISTRY[cls.TYPE] = cls
    return cls


def action_from_dict(data: Dict[str, Any]) -> Action:
    """Rebuild an action from its serialized ``{"type": ..., ...}`` form."""
    type_name = data.get("type")
    cls = _REGISTRY.get(type_name)
    if cls is None:
        raise KeyError(f"unknown action type: {type_name!r}")
    params = {k: v for k, v in data.items() if k != "type"}
    return cls.from_params(params)


def make_default(type_name: str) -> Action:
    """Create an action of ``type_name`` with default parameters (for the GUI)."""
    cls = _REGISTRY.get(type_name)
    if cls is None:
        raise KeyError(f"unknown action type: {type_name!r}")
    return cls.from_params({})


def action_types() -> List[Type[Action]]:
    """All registered action classes, sorted by label (for the GUI picker)."""
    return sorted(_REGISTRY.values(), key=lambda c: c.LABEL)


# Backwards-friendly alias used by the UI layer.
ACTION_TYPES = action_types
