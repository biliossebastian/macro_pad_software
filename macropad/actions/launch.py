"""Start a program, or open a file/URL with its default handler."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from typing import Any, Dict, List

from .base import Action, FieldSpec
from .registry import register


@register
class LaunchAction(Action):
    TYPE = "launch"
    LABEL = "Launch program / open file"

    def __init__(self, target: str = "", args: str = "") -> None:
        self.target = target
        self.args = args

    @classmethod
    def fields(cls) -> List[FieldSpec]:
        return [
            FieldSpec(
                name="target",
                label="Program, file or URL",
                kind="file",
                placeholder=r"C:\Windows\notepad.exe",
            ),
            FieldSpec(name="args", label="Arguments", placeholder="optional"),
        ]

    def execute(self) -> None:
        if not self.target:
            raise ValueError("no target set")
        # Never wait for the launched program: Popen / startfile return at once.
        if self.args:
            subprocess.Popen([self.target, *shlex.split(self.args, posix=False)])
        elif sys.platform == "win32":
            os.startfile(self.target)  # handles .exe, documents and URLs
        else:
            subprocess.Popen(["xdg-open", self.target])

    def describe(self) -> str:
        name = os.path.basename(self.target.rstrip("/\\")) or self.target
        return f"Launch {name}" if name else "Launch (unset)"

    def to_params(self) -> Dict[str, Any]:
        return {"target": self.target, "args": self.args}

    @classmethod
    def from_params(cls, params: Dict[str, Any]) -> "LaunchAction":
        return cls(target=params.get("target", ""), args=params.get("args", ""))
