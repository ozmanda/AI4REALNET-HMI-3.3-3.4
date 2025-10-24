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
    QStyle,
)

if TYPE_CHECKING:
    from .AnalysisWindow import AnalysisWindow
    from .SolutionGenerationWindow import SolutionGenerationWindow
    from .FormulateSolutionWindow import FormulateSolutionWindow
    from src.ui.flatland_viewer import FlatlandViewer

class SolutionWindow(QMainWindow):
    def __init__(self, viewer: "FlatlandViewer", handle: int):
        super().__init__(viewer)
        self.viewer = viewer
        self.handle = handle
        self.analysis_window: Optional[AnalysisWindow] = None
        self.generation_window: Optional["SolutionGenerationWindow"] = None
        self.formulation_window: Optional["FormulateSolutionWindow"] = None
        self.setWindowTitle(f"Solutions for Train {handle}")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMinimumSize(QSize(360, 220))
        self.info_label = QLabel(alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.info_label.setWordWrap(True)
        execute_btn = QPushButton(" Solution Generation")
        execute_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogListView))
        execute_btn.clicked.connect(self._on_generate_clicked)
        analyse_btn = QPushButton(" Formulate Solution")
        analyse_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder))
        analyse_btn.clicked.connect(self._on_formulate_clicked)
        button_row = QHBoxLayout()
        button_row.addWidget(execute_btn)
        button_row.addWidget(analyse_btn)
        button_row.addStretch()
        layout = QVBoxLayout()
        layout.addWidget(self.info_label)
        layout.addSpacing(12)
        layout.addLayout(button_row)
        layout.addStretch()
        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)
        self.refresh()

    def refresh(self) -> None:
        if sip.isdeleted(self.info_label):
            return
        try:
            self.info_label.setText(self.viewer.format_malfunction_summary(self.handle))
        except RuntimeError:
            pass

    def closeEvent(self, event):
        if self.generation_window is not None and not sip.isdeleted(self.generation_window):
            try:
                self.generation_window.close()
            except RuntimeError:
                pass
            self.generation_window = None
        if self.formulation_window is not None and not sip.isdeleted(self.formulation_window):
            try:
                self.formulation_window.close()
            except RuntimeError:
                pass
            self.formulation_window = None
        if self.analysis_window is not None and not sip.isdeleted(self.analysis_window):
            try:
                self.analysis_window.close()
            except RuntimeError:
                pass
            self.analysis_window = None
        self.viewer._on_solution_window_close(self.handle)
        super().closeEvent(event)

    def _on_generate_clicked(self) -> None:
        window = self.viewer._open_solution_generation(self.handle, self)
        if window is not None:
            self.generation_window = window

    def _on_formulate_clicked(self) -> None:
        window = self.viewer._open_formulate_solution(self.handle, self)
        if window is not None:
            self.formulation_window = window
