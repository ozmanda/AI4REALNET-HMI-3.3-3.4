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
from .SolutionWindow import SolutionWindow


class FormulateSolutionWindow(QMainWindow):
    def __init__(self, viewer: "FlatlandViewer", handle: int, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.viewer = viewer
        self.handle = handle
        self.setWindowTitle(f"Formulate Solution - Train {handle}")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMinimumSize(QSize(360, 280))
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Describe your solution approach...")
        execute_btn = QPushButton("Execute")
        execute_btn.clicked.connect(self._on_execute)
        analyse_btn = QPushButton("Analyse")
        analyse_btn.clicked.connect(self._on_analyse)
        button_row = QHBoxLayout()
        button_row.addWidget(execute_btn)
        button_row.addWidget(analyse_btn)
        button_row.addStretch()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Draft a solution for the operator:"))
        layout.addWidget(self.text_edit)
        layout.addLayout(button_row)
        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

    def _on_execute(self) -> None:
        text = self.text_edit.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Execute", "Please formulate a solution first.")
            return
        self.viewer.record_solution_action(self.handle, "Formulated Solution", text)
        print(f"[Simulation] Execute formulated solution for train {self.handle}: {text}")
        parent = self.parent()
        self.close()
        if parent is not None and parent.__class__.__name__ == "SolutionWindow":
            parent.close()

    def _on_analyse(self) -> None:
        text = self.text_edit.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Analyse", "Please formulate a solution first.")
            return
        window = self.viewer._open_analysis_window(self.handle, self, "formulated")
        if window is not None:
            print(f"[Simulation] Analyse formulated solution for train {self.handle}: {text}")

    def closeEvent(self, event):
        self.viewer._on_formulate_solution_close(self.handle)
        super().closeEvent(event)
