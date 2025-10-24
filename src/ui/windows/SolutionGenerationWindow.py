from __future__ import annotations

import time
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Tuple

from PyQt6 import sip
from PyQt6.QtCore import QPoint, QSize, Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QComboBox,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QHeaderView,
    QMessageBox,
    QStyle
)
if TYPE_CHECKING:
    from src.ui.flatland_viewer import FlatlandViewer
class SolutionGenerationWindow(QMainWindow):
    def __init__(self, viewer: "FlatlandViewer", handle: int, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.viewer = viewer
        self.handle = handle
        self.setWindowTitle(f"Solution Options - Train {handle}")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMinimumSize(QSize(360, 280))
        self.list_widget = QListWidget()
        self.list_widget.addItems(self.viewer.get_solution_suggestions(handle))
        self.execute_btn = QPushButton("Execute")
        self.execute_btn.clicked.connect(self._on_execute)
        self.analyse_btn = QPushButton("Analyse")
        self.analyse_btn.clicked.connect(self._on_analyse)
        button_row = QHBoxLayout()
        button_row.addWidget(self.execute_btn)
        button_row.addWidget(self.analyse_btn)
        button_row.addStretch()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Select a solution and choose an action:"))
        layout.addWidget(self.list_widget)
        layout.addLayout(button_row)
        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

    def _selected_text(self) -> Optional[str]:
        item = self.list_widget.currentItem()
        return item.text() if item is not None else None

    def _on_execute(self) -> None:
        text = self._selected_text()
        if text is None:
            QMessageBox.information(self, "Execute", "Please select a solution first.")
            return
        self.viewer.record_solution_action(self.handle, "Generated Solution", text)
        print(f"[Simulation] Execute generated solution for train {self.handle}: {text}")
        parent = self.parent()
        self.close()
        if parent is not None and parent.__class__.__name__ == "SolutionWindow":
            parent.close()

    def _on_analyse(self) -> None:
        text = self._selected_text()
        if text is None:
            QMessageBox.information(self, "Analyse", "Please select a solution first.")
            return
        window = self.viewer._open_analysis_window(self.handle, self, "generated")
        if window is not None:
            print(f"[Simulation] Analyse generated solution for train {self.handle}: {text}")
    def closeEvent(self, event):
        parent = self.parent()
        if parent is not None and parent.__class__.__name__ == "SolutionWindow":
            setattr(parent, "generation_window", None)
        self.viewer._on_solution_generation_close(self.handle)
        super().closeEvent(event)
