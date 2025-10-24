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

class IncidentListWindow(QMainWindow):
    def __init__(self, viewer: "FlatlandViewer"):
        super().__init__(viewer)
        self.viewer = viewer
        self.setWindowTitle("Incidents")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMinimumSize(QSize(420, 320))
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        info_label = QLabel("Double-click an incident to review analysis and open reflection.")
        info_label.setWordWrap(True)
        layout = QVBoxLayout()
        layout.addWidget(info_label)
        layout.addWidget(self.list_widget)
        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)
        self.refresh()

    def refresh(self) -> None:
        incidents = self.viewer.get_incidents()
        self.list_widget.clear()
        if not incidents:
            item = QListWidgetItem("No incidents recorded.")
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.list_widget.addItem(item)
            self.list_widget.setEnabled(False)
            return
        self.list_widget.setEnabled(True)
        for incident in incidents:
            timestamp = time.strftime("%H:%M:%S", time.localtime(incident["wall_time"]))
            status = "on-map" if incident.get("on_map", False) else "off-map"
            item = QListWidgetItem(f"Train {incident['handle']} - {status} - {timestamp}")
            item.setData(Qt.ItemDataRole.UserRole, incident["id"])
            self.list_widget.addItem(item)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        incident_id = item.data(Qt.ItemDataRole.UserRole)
        if incident_id is None:
            return
        self.viewer._open_incident_analysis(incident_id)

    def closeEvent(self, event):
        self.viewer._on_incident_window_close()
        super().closeEvent(event)
