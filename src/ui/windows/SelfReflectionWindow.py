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



class SelfReflectionWindow(QMainWindow):
    QUESTIONS = [
        {"type": "radio", "question": "Did the solution arrive as expected?", "options": ["Yes", "No"]},
        {"type": "text", "question": "What happened?", "placeholder": "Add your notes here..."},
        {"type": "text", "question": "What would you change next time?", "placeholder": "Add your ideas here..."},
        {"type": "text", "question": "What general insights do you draw from this?", "placeholder": "Add your insights here..."},
        {"type": "text", "question": "How can you measure success?", "placeholder": "Add measures of success..."},
    ]

    def __init__(self, viewer: "FlatlandViewer", incident: dict):
        super().__init__(viewer)
        self.viewer = viewer
        self.incident = incident
        self.setWindowTitle(f"Self-Reflection - Train {incident['handle']}")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMinimumSize(QSize(420, 360))
        self._responses: Dict[int, str] = {}
        self._radio_groups: Dict[int, QButtonGroup] = {}
        self._text_inputs: Dict[int, QTextEdit] = {}
        self._logged = False
        self.stack = QStackedWidget()

        for index, question in enumerate(self.QUESTIONS):
            self.stack.addWidget(self._build_page(index, question))

        self.exit_button = QPushButton("Exit Reflection")
        self.exit_button.clicked.connect(self._on_exit_clicked)
        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self._on_next_click)

        central = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.stack)
        button_bar = QHBoxLayout()
        button_bar.addWidget(self.exit_button)
        button_bar.addStretch()
        button_bar.addWidget(self.next_button)
        layout.addLayout(button_bar)
        central.setLayout(layout)
        self.setCentralWidget(central)
        self._update_button_text()

    def _build_page(self, index: int, question: dict) -> QWidget:
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.Panel)
        frame.setFrameShadow(QFrame.Shadow.Raised)
        layout = QVBoxLayout()
        title = QLabel("Reflection")
        title.setStyleSheet("font-weight: bold; font-size: 16px;")
        subtitle = QLabel("Let's reflect")
        subtitle.setStyleSheet("color: #666;")
        question_label = QLabel(question["question"])
        question_label.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(8)
        layout.addWidget(question_label)
        layout.addSpacing(6)

        if question["type"] == "radio":
            button_group = QButtonGroup(self)
            option_layout = QVBoxLayout()
            for option in question["options"]:
                radio = QRadioButton(option)
                option_layout.addWidget(radio)
                button_group.addButton(radio)
            layout.addLayout(option_layout)
            self._radio_groups[index] = button_group
        else:
            text_edit = QTextEdit()
            text_edit.setPlaceholderText(question.get("placeholder", ""))
            text_edit.setMinimumHeight(100)
            layout.addWidget(text_edit)
            self._text_inputs[index] = text_edit

        layout.addStretch()
        frame.setLayout(layout)
        return frame

    def _on_next_click(self) -> None:
        self._collect_current_page()
        if self.stack.currentIndex() + 1 < self.stack.count():
            self.stack.setCurrentIndex(self.stack.currentIndex() + 1)
            self._update_button_text()
        else:
            self._finalize_and_close()

    def _on_exit_clicked(self) -> None:
        self._collect_current_page()
        self._finalize_and_close()

    def _collect_current_page(self) -> None:
        page_index = self.stack.currentIndex()
        question = self.QUESTIONS[page_index]
        if question["type"] == "radio":
            button_group = self._radio_groups.get(page_index)
            if button_group:
                checked = button_group.checkedButton()
                self._responses[page_index] = checked.text() if checked else ""
        else:
            text_edit = self._text_inputs.get(page_index)
            if text_edit:
                self._responses[page_index] = text_edit.toPlainText().strip()

    def _update_button_text(self) -> None:
        if self.stack.currentIndex() == self.stack.count() - 1:
            self.next_button.setText("Finish")
        else:
            self.next_button.setText("Next")

    def _finalize_and_close(self) -> None:
        if not self._logged:
            self.viewer.log_reflection(self.incident, dict(self._responses))
            self._logged = True
        self.close()

    def closeEvent(self, event):
        if not self._logged:
            self._collect_current_page()
            self.viewer.log_reflection(self.incident, dict(self._responses))
            self._logged = True
        self.viewer._on_reflection_window_close(self.incident["id"])
        super().closeEvent(event)
