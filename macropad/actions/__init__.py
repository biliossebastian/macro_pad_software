"""Actions the app can run in response to a button event."""

from .base import Action, FieldSpec  # noqa: F401
from .registry import (  # noqa: F401
    ACTION_TYPES,
    action_from_dict,
    make_default,
    register,
)

# Importing these modules registers their action types as a side effect.
from . import keystroke  # noqa: F401,E402
from . import launch  # noqa: F401,E402
