from __future__ import annotations

from typing import Optional, Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QWidget


class ClickableLabel(QLabel):
    def __init__(self, click_callback: Optional[Callable] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._click_callback = click_callback

    def mousePressEvent(self, event):  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton and self._click_callback:
            self._click_callback(event)
        super().mousePressEvent(event)
