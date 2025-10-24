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


class TrainInfoWindow(QMainWindow):
    def __init__(self, viewer: "FlatlandViewer", handle: int):
        super().__init__(viewer)
        self.viewer = viewer
        self.handle = handle
        self.setWindowTitle(f"Train {handle} Details")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMinimumSize(QSize(380, 360))

        central = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        title = QLabel(f"Train {handle}")
        title.setStyleSheet("font-size:18px;font-weight:600;")
        layout.addWidget(title)

        self._info_form = QFormLayout()
        self._info_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._info_form.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
        self._labels: Dict[str, QLabel] = {}
        for key in (
            "train_type",
            "identifier",
            "state",
            "current_position",
            "current_direction",
            "speed",
            "origin",
            "target",
            "next_waypoint",
        ):
            label = QLabel()
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self._labels[key] = label
        self._info_form.addRow("Train Type:", self._labels["train_type"])
        self._info_form.addRow("Identifier:", self._labels["identifier"])
        self._info_form.addRow("Status:", self._labels["state"])
        self._info_form.addRow("Current Position:", self._labels["current_position"])
        self._info_form.addRow("Current Direction:", self._labels["current_direction"])
        self._info_form.addRow("Speed:", self._labels["speed"])
        self._info_form.addRow("Origin:", self._labels["origin"])
        self._info_form.addRow("Target:", self._labels["target"])
        self._info_form.addRow("Next Waypoint:", self._labels["next_waypoint"])
        layout.addLayout(self._info_form)

        waypoints_title = QLabel("Waypoints")
        waypoints_title.setStyleSheet("font-weight:600;")
        layout.addWidget(waypoints_title)

        self._waypoint_table = QTableWidget(0, 6, self)
        self._waypoint_table.setHorizontalHeaderLabels(
            ["#", "Role", "Position", "Direction", "Earliest Departure", "Latest Arrival"]
        )
        header = self._waypoint_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        self._waypoint_table.verticalHeader().setVisible(False)
        self._waypoint_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._waypoint_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._waypoint_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self._waypoint_table)

        layout.addStretch()
        central.setLayout(layout)
        self.setCentralWidget(central)
        self.refresh()

    def refresh(self) -> None:
        details = self.viewer.get_train_details(self.handle)
        self._labels["train_type"].setText(details.get("train_type", "Unknown"))
        self._labels["identifier"].setText(details.get("identifier", "N/A"))
        self._labels["state"].setText(details.get("state", "Unknown"))
        self._labels["current_position"].setText(details.get("current_position", "Unknown"))
        self._labels["current_direction"].setText(details.get("current_direction", "Unknown"))
        self._labels["speed"].setText(details.get("speed", "Unknown"))
        self._labels["origin"].setText(details.get("origin", "Unknown"))
        self._labels["target"].setText(details.get("target", "Unknown"))
        self._labels["next_waypoint"].setText(details.get("next_waypoint", "N/A"))
        self._populate_waypoints(details.get("waypoints", []))

    def _populate_waypoints(self, rows: List[Dict[str, str]]) -> None:
        self._waypoint_table.setRowCount(len(rows))
        for idx, entry in enumerate(rows):
            index_item = QTableWidgetItem(str(entry.get("index", idx + 1)))
            role_item = QTableWidgetItem(entry.get("role", ""))
            position_item = QTableWidgetItem(entry.get("position", ""))
            direction_item = QTableWidgetItem(entry.get("direction", ""))
            earliest_item = QTableWidgetItem(entry.get("earliest", ""))
            latest_item = QTableWidgetItem(entry.get("latest", ""))
            for item in (
                index_item,
                role_item,
                position_item,
                direction_item,
                earliest_item,
                latest_item,
            ):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._waypoint_table.setItem(idx, 0, index_item)
            self._waypoint_table.setItem(idx, 1, role_item)
            self._waypoint_table.setItem(idx, 2, position_item)
            self._waypoint_table.setItem(idx, 3, direction_item)
            self._waypoint_table.setItem(idx, 4, earliest_item)
            self._waypoint_table.setItem(idx, 5, latest_item)
        self._waypoint_table.resizeColumnsToContents()

    def closeEvent(self, event):
        self.viewer._on_train_info_close(self.handle)
        super().closeEvent(event)
