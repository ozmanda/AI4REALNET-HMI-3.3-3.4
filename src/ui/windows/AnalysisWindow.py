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


class AnalysisWindow(QMainWindow):
    def __init__(
        self,
        viewer: "FlatlandViewer",
        handle: int,
        context: str,
        parent: Optional[QWidget] = None,
        payload: Optional[dict] = None,
        reflection_callback: Optional[Callable[[], None]] = None,
        on_close: Optional[Callable[[int], None]] = None,
    ):
        super().__init__(parent)
        self.viewer = viewer
        self.handle = handle
        self._context = context
        self._incident_payload = payload
        self._reflection_callback = reflection_callback
        self._on_close_callback = on_close
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMinimumSize(QSize(420, 340))

        central = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        self._heading_label = QLabel()
        self._heading_label.setWordWrap(True)
        self._heading_label.setStyleSheet("font-size:18px;font-weight:600;")

        self._subheading_label = QLabel()
        self._subheading_label.setWordWrap(True)
        self._subheading_label.setStyleSheet("color:#5a5a5a;")

        self._summary_widget = QWidget()
        self._summary_layout = QVBoxLayout()
        self._summary_layout.setContentsMargins(0, 0, 0, 0)
        self._summary_layout.setSpacing(10)
        self._summary_widget.setLayout(self._summary_layout)
        self._summary_labels: Dict[str, tuple[QLabel, QLabel]] = {}
        for key in ("risk", "actions", "impact"):
            title_label = QLabel()
            title_label.setStyleSheet("font-size:12px;color:#6c6c6c;text-transform:uppercase;")
            value_label = QLabel()
            value_label.setStyleSheet("font-size:18px;font-weight:600;")
            value_label.setWordWrap(True)
            block_widget = QWidget()
            block_layout = QVBoxLayout()
            block_layout.setContentsMargins(0, 0, 0, 0)
            block_layout.setSpacing(2)
            block_layout.addWidget(title_label)
            block_layout.addWidget(value_label)
            block_widget.setLayout(block_layout)
            self._summary_layout.addWidget(block_widget)
            self._summary_labels[key] = (title_label, value_label)

        self._impact_table = QTableWidget(0, 2, self)
        self._impact_table.setHorizontalHeaderLabels(["Train", "Delay"])
        header = self._impact_table.horizontalHeader()
        header.setStretchLastSection(True)
        self._impact_table.verticalHeader().setVisible(False)
        self._impact_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._impact_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._impact_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._impact_table.setMinimumHeight(140)
        self._impact_table.setStyleSheet(
            "background:#252525;color:#f0f0f0;gridline-color:#3a3a3a;"
        )
        header.setStyleSheet("color:#f0f0f0;background:#2d2d2d;")

        self._actions_title = QLabel("Actions Taken")
        self._actions_title.setStyleSheet("font-weight:600;")
        self._actions_table = QTableWidget(0, 3, self)
        self._actions_table.setHorizontalHeaderLabels(["Source", "Description", "Step"])
        actions_header = self._actions_table.horizontalHeader()
        actions_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        actions_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        actions_header.setStretchLastSection(True)
        self._actions_table.verticalHeader().setVisible(False)
        self._actions_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._actions_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._actions_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._actions_title.setVisible(False)
        self._actions_table.setVisible(False)

        self._reflection_button = QPushButton("Open Reflection")
        self._reflection_button.clicked.connect(self._on_reflection_clicked)
        self._reflection_button.setVisible(False)

        main_layout.addWidget(self._heading_label)
        main_layout.addWidget(self._subheading_label)
        main_layout.addWidget(self._summary_widget)
        main_layout.addWidget(self._impact_table)
        main_layout.addWidget(self._actions_title)
        main_layout.addWidget(self._actions_table)
        main_layout.addWidget(self._reflection_button)
        main_layout.addStretch()

        central.setLayout(main_layout)
        self.setCentralWidget(central)

        self._apply_context()

    def closeEvent(self, event):
        if self._on_close_callback is not None:
            self._on_close_callback(self.handle)
        else:
            self.viewer._on_analysis_window_close(self.handle)
        super().closeEvent(event)

    def set_context(self, context: str) -> None:
        self._context = context
        self._apply_context()

    def update_incident_payload(
        self, payload: dict, reflection_callback: Optional[Callable[[], None]]
    ) -> None:
        self._incident_payload = payload
        self._reflection_callback = reflection_callback
        self._context = "incident"
        self._apply_context()

    def _apply_context(self) -> None:
        (
            heading,
            subheading,
            window_title,
            summary,
            impacted_rows,
            actions,
            reflection_config,
        ) = self._context_data()
        self.setWindowTitle(window_title)
        self._heading_label.setText(heading)
        self._subheading_label.setText(subheading)
        self._populate_summary(summary)
        self._populate_impacted_table(impacted_rows)
        self._populate_actions(actions)
        self._configure_reflection_button(reflection_config)

    def _context_data(self) -> tuple[
        str,
        str,
        str,
        Dict[str, tuple[str, str]],
        List[tuple[str, str]],
        List[Dict[str, str]],
        Optional[dict],
    ]:
        if self._context == "incident":
            payload = self._incident_payload or {}
            heading = payload.get("heading", f"Incident Review - Train {self.handle}")
            subheading = payload.get(
                "subheading", "Post-incident summary and actions"
            )
            window_title = payload.get(
                "window_title", f"Incident Analysis - Train {self.handle}"
            )
            summary = payload.get(
                "summary",
                {
                    "risk": ("Risk Assessment", "Medium"),
                    "actions": ("Number of Actions", "0"),
                    "impact": ("Impacted Trains", "1"),
                },
            )
            impacted = payload.get(
                "impacted",
                [(f"Train {self.handle}", "Primary incident train")],
            )
            actions = payload.get("actions", [])
            reflection_config = {
                "label": payload.get("reflection_label", "Open Reflection"),
                "callback": self._reflection_callback,
            }
        elif self._context == "formulated":
            heading = "Your Action"
            subheading = "Operator-defined response overview"
            window_title = f"Formulated Solution Analysis - Train {self.handle}"
            summary = {
                "risk": ("Risk Assessment", "Medium"),
                "actions": ("Number of Actions", "4"),
                "impact": ("Impacted Trains", "2"),
            }
            impacted = [
                ("Train 2451", "2 min delay"),
                ("Train 3002", "90 sec delay"),
            ]
            actions = []
            reflection_config = None
        else:
            heading = "Alternative"
            subheading = "AI-suggested option overview"
            window_title = f"Generated Solution Analysis - Train {self.handle}"
            summary = {
                "risk": ("Risk Assessment", "Low"),
                "actions": ("Number of Actions", "3"),
                "impact": ("Impacted Trains", "2"),
            }
            impacted = [
                ("Train 630988", "30 sec delay"),
                ("Train 234909", "2 min delay"),
            ]
            actions = []
            reflection_config = None
        return (
            heading,
            subheading,
            window_title,
            summary,
            impacted,
            actions,
            reflection_config,
        )

    def _populate_summary(self, summary: Dict[str, tuple[str, str]]) -> None:
        for key, labels in self._summary_labels.items():
            title_label, value_label = labels
            title, value = summary.get(
                key, ("", "")
            )
            title_label.setText(title)
            value_label.setText(value)

    def _populate_impacted_table(self, rows: List[tuple[str, str]]) -> None:
        self._impact_table.setRowCount(len(rows))
        for row_index, (train, delay) in enumerate(rows):
            train_item = QTableWidgetItem(train)
            delay_item = QTableWidgetItem(delay)
            train_item.setFlags(train_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            delay_item.setFlags(delay_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._impact_table.setItem(row_index, 0, train_item)
            self._impact_table.setItem(row_index, 1, delay_item)
        self._impact_table.resizeColumnsToContents()

    def _populate_actions(self, actions: List[Dict[str, str]]) -> None:
        has_actions = bool(actions)
        self._actions_title.setVisible(has_actions)
        self._actions_table.setVisible(has_actions)
        if not has_actions:
            self._actions_table.setRowCount(0)
            return
        self._actions_table.setRowCount(len(actions))
        for row_index, action in enumerate(actions):
            source_item = QTableWidgetItem(action.get("source", ""))
            description_item = QTableWidgetItem(action.get("description", ""))
            step_item = QTableWidgetItem(action.get("step", ""))
            for item in (source_item, description_item, step_item):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._actions_table.setItem(row_index, 0, source_item)
            self._actions_table.setItem(row_index, 1, description_item)
            self._actions_table.setItem(row_index, 2, step_item)
        self._actions_table.resizeColumnsToContents()

    def _configure_reflection_button(self, config: Optional[dict]) -> None:
        if config is None or config.get("callback") is None:
            self._reflection_button.setVisible(False)
            self._reflection_callback = None
            return
        self._reflection_callback = config.get("callback")
        label = config.get("label", "Open Reflection")
        self._reflection_button.setText(label)
        self._reflection_button.setVisible(True)

    def _on_reflection_clicked(self) -> None:
        if self._reflection_callback is not None:
            self._reflection_callback()

