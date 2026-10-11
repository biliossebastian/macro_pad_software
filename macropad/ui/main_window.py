"""Baseline main window: a 3x3 button matrix and three 0-100 sliders.

This is intentionally logic-free scaffolding. The widgets are stored on the
window (``self.buttons``, ``self.sliders``) so behaviour can be wired to them
later without touching the layout code.
"""

from __future__ import annotations

import logging
from typing import Dict, List

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ..actions import Action, action_from_dict

log = logging.getLogger(__name__)

#: Temporary hard-coded mapping (button index -> action) until the engine and
#: config land. Index 0 is the top-left button, labelled "1".
BUTTON_ACTIONS: Dict[int, Action] = {
    0: action_from_dict({"type": "keystroke", "keys": "ctrl+c"}),
}

BUTTON_COUNT = 9          # 3x3 matrix
BUTTON_GRID_COLS = 3
SLIDER_COUNT = 3
SLIDER_MIN = 0
SLIDER_MAX = 100


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MacroPad Companion")
        # Clicking a button must not pull focus away from the app the user is
        # working in, or Ctrl+C would be sent to this window instead.
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.WindowStaysOnTopHint
        )

        #: Button widgets, indexed 0..BUTTON_COUNT-1 (button id == index).
        self.buttons: List[QPushButton] = []
        #: Slider widgets, indexed 0..SLIDER_COUNT-1.
        self.sliders: List[QSlider] = []
        self._slider_value_labels: List[QLabel] = []

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        root.addWidget(self._build_button_grid())
        root.addWidget(self._build_sliders())
        root.addStretch(1)

        self.setCentralWidget(central)
        self.resize(420, 520)

    # -- 3x3 button matrix ---------------------------------------------------
    def _build_button_grid(self) -> QGroupBox:
        box = QGroupBox("Buttons")
        grid = QGridLayout(box)
        grid.setSpacing(10)

        for i in range(BUTTON_COUNT):
            action = BUTTON_ACTIONS.get(i)
            text = str(i + 1) if action is None else f"{i + 1}\n{action.describe()}"
            btn = QPushButton(text)
            btn.setMinimumSize(96, 96)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            font = QFont()
            font.setPointSize(18 if action is None else 12)
            btn.setFont(font)
            if action is not None:
                btn.clicked.connect(lambda _=False, a=action: self._run(a))
            row, col = divmod(i, BUTTON_GRID_COLS)
            grid.addWidget(btn, row, col)
            self.buttons.append(btn)

        return box

    def _run(self, action: Action) -> None:
        # A failing action must not take the UI down with it.
        try:
            action.execute()
        except Exception:
            log.exception("action %s failed", action.describe())

    # -- three 0-100 sliders -------------------------------------------------
    def _build_sliders(self) -> QGroupBox:
        box = QGroupBox("Sliders")
        outer = QVBoxLayout(box)
        outer.setSpacing(12)

        for i in range(SLIDER_COUNT):
            row = QHBoxLayout()

            name = QLabel(f"Slider {i + 1}")
            name.setMinimumWidth(64)

            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(SLIDER_MIN, SLIDER_MAX)
            slider.setValue(0)
            slider.setTickPosition(QSlider.TickPosition.TicksBelow)
            slider.setTickInterval(10)

            value = QLabel("0")
            value.setMinimumWidth(32)
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            # Only updates the read-out label; no application logic.
            slider.valueChanged.connect(value.setNum)

            row.addWidget(name)
            row.addWidget(slider, 1)
            row.addWidget(value)
            outer.addLayout(row)

            self.sliders.append(slider)
            self._slider_value_labels.append(value)

        return box
