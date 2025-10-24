import sys
import time
import random
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple, Set, Any, Iterable
from itertools import product

from PyQt6 import sip
from PyQt6.QtCore import QPoint, QSize, Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QPushButton,
    QStyle,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QRadioButton,
    QButtonGroup,
    QStackedWidget,
    QLineEdit,
    QFileDialog,
    QFormLayout,
    QSpinBox,
    QDoubleSpinBox,
    QMessageBox,
    QAbstractItemView,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QDialog,
    QDialogButtonBox,
    QComboBox,
)

from PIL import Image, ImageDraw, ImageFont

from flatland.envs.malfunction_generators import MalfunctionParameters, ParamMalfunctionGen
from flatland.envs.rail_env import RailEnv
from flatland.envs.rail_env_action import RailEnvActions
from flatland.envs.rail_generators import sparse_rail_generator
from flatland.envs.line_generators import sparse_line_generator
from flatland.envs.observations import GlobalObsForRailEnv
from flatland.envs.step_utils.states import TrainState
from flatland.utils.rendertools import RenderTool

from src.utils.environments.scenario_loader import load_scenario_from_json
from src.utils.graph.ConflictPredictor import ConflictPredictor

STEP_INTERVAL_MS = 500
DEFAULT_MALFUNCTION_RATE = 1 / 40
DEFAULT_MALFUNCTION_MIN = 4
DEFAULT_MALFUNCTION_MAX = 8
SCENARIO_DIRECTORY = Path(r"C:\Users\ma1198656\OneDrive - FHNW\Dokumente\VSCode\AI4REALNET-T3.4\src\environments")


@dataclass
class SimulationConfig:
    model_path: Optional[str]
    scenario_path: Optional[str]
    width: int
    height: int
    agents: int
    malfunction_rate: float
    malfunction_min: int
    malfunction_max: int


class ClickableLabel(QLabel):
    def __init__(self, click_callback, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._click_callback = click_callback

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._click_callback:
            self._click_callback(event)
        super().mousePressEvent(event)


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


class ConflictResolutionDialog(QDialog):
    COLOR_INFO = [
        ((255, 0, 0, 140), "Red"),
        ((0, 90, 255, 140), "Blue"),
    ]
    PREVIEW_COLORS = [info[0] for info in COLOR_INFO]

    def __init__(self, viewer: "FlatlandViewer", conflicts: List[Dict[str, Any]], parent: Optional[QWidget] = None):
        super().__init__(parent or viewer)
        self.viewer = viewer
        self._conflicts: List[Dict[str, Any]] = conflicts
        self._button_groups: Dict[int, QButtonGroup] = {}
        self._delay_controls: Dict[int, QSpinBox] = {}
        self._current_handles: Tuple[int, ...] = tuple()
        self._suggestion: Optional[Dict[int, int]] = None
        self.setModal(True)
        self.setWindowTitle("Route Conflict Detected")
        self.resize(QSize(520, 420))

        layout = QVBoxLayout()
        description_label = QLabel("The following trains are attempting to use overlapping track segments.")
        description_label.setWordWrap(True)
        layout.addWidget(description_label)

        self._conflict_list = QListWidget()
        self._conflict_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._conflict_list.itemSelectionChanged.connect(self._on_conflict_selected)
        layout.addWidget(self._conflict_list)

        self._options_container = QWidget()
        self._options_layout = QVBoxLayout()
        self._options_layout.setContentsMargins(0, 0, 0, 0)
        self._options_layout.setSpacing(6)
        self._options_container.setLayout(self._options_layout)
        layout.addWidget(self._options_container)

        self._suggestion_label = QLabel()
        self._suggestion_label.setWordWrap(True)
        self._suggestion_label.setStyleSheet("color:#1c7c54;")
        layout.addWidget(self._suggestion_label)

        self._resolution_label = QLabel()
        self._resolution_label.setWordWrap(True)
        self._resolution_label.setStyleSheet("color:#444444;")
        layout.addWidget(self._resolution_label)

        self._status_label = QLabel()
        self._status_label.setStyleSheet("color:#c0392b;")
        layout.addWidget(self._status_label)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self._apply_selection)
        button_box.rejected.connect(self.reject)
        self._suggestion_button = button_box.addButton("Apply Suggestion", QDialogButtonBox.ButtonRole.ActionRole)
        self._suggestion_button.clicked.connect(self._apply_suggestion)
        self._suggestion_button.setVisible(False)
        layout.addWidget(button_box)
        self.setLayout(layout)

        self._populate_conflict_list()
        if self._conflicts:
            self._conflict_list.setCurrentRow(0)
        else:
            self.viewer.clear_preview_paths()

    def closeEvent(self, event):
        self.viewer.clear_preview_paths()
        self.viewer.clear_conflict_focus()
        super().closeEvent(event)

    def _populate_conflict_list(self) -> None:
        self._conflict_list.blockSignals(True)
        self._conflict_list.clear()
        for conflict in self._conflicts:
            agents = conflict.get("agents", ())
            parts: List[str] = []
            for idx, handle in enumerate(agents):
                color_name = self._color_name_for_index(idx)
                suffix = f" ({color_name})" if color_name else ""
                parts.append(f"Train {handle}{suffix}")
            text = " vs ".join(parts) if parts else "Unknown trains"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, conflict)
            self._conflict_list.addItem(item)
        self._conflict_list.blockSignals(False)

    def _collect_decisions(self) -> Tuple[Dict[int, int], Dict[int, int]]:
        selections: Dict[int, int] = {}
        for handle, group in self._button_groups.items():
            selected_id = group.checkedId()
            if selected_id >= 0:
                selections[handle] = selected_id
        delays: Dict[int, int] = {}
        for handle, spin in self._delay_controls.items():
            value = max(0, int(spin.value()))
            delays[handle] = value
        return selections, delays

    def _on_delay_changed(self, _value: int) -> None:
        self._update_resolution_preview()

    def _color_name_for_index(self, idx: int) -> str:
        if idx < len(self.COLOR_INFO):
            return self.COLOR_INFO[idx][1]
        return ""

    def _create_color_chip(self, color: Tuple[int, int, int, int]) -> QLabel:
        chip = QLabel()
        chip.setFixedSize(14, 14)
        r, g, b, a = color
        chip.setStyleSheet(
            f"background-color: rgba({r}, {g}, {b}, {a});"
            "border:1px solid rgba(0,0,0,120);"
            "border-radius:3px;"
        )
        return chip

    def _update_resolution_preview(self) -> None:
        if not self._button_groups:
            self._resolution_label.clear()
            return
        selections, delays = self._collect_decisions()
        if not selections and not any(value > 0 for value in delays.values()):
            self._resolution_label.setStyleSheet("color:#444444;")
            self._resolution_label.setText("Adjust routes or delays to preview conflict status.")
            return
        resolved, conflicts = self.viewer.preview_conflict_resolution(selections, delays)
        if resolved:
            self._resolution_label.setStyleSheet("color:#1c7c54;")
            self._resolution_label.setText("Selected routes and delays resolve the current conflict.")
            self._status_label.clear()
        else:
            count = len(conflicts)
            suffix = "conflict" if count == 1 else "conflicts"
            self._resolution_label.setStyleSheet("color:#c27c1c;")
            self._resolution_label.setText(f"{count} {suffix} still detected with the current selection.")

    def _apply_selection(self) -> None:
        selections, delays = self._collect_decisions()
        success, conflicts = self.viewer.apply_path_selection(selections, delays)
        if success:
            self.viewer.clear_preview_paths()
            self.viewer.clear_conflict_focus()
            self.viewer.ensure_simulation_running()
            self.accept()
        else:
            self._status_label.setText("Selected routes still lead to conflicts. Please choose different paths.")
            self.viewer.refresh_conflict_state()
            self._update_resolution_preview()

    def _apply_suggestion(self) -> None:
        if not self._suggestion:
            return
        for handle, index in self._suggestion.items():
            group = self._button_groups.get(handle)
            if group is None:
                continue
            button = group.button(index)
            if button is not None:
                button.setChecked(True)
        self._apply_selection()

    def _on_conflict_selected(self) -> None:
        self.viewer.clear_preview_paths()
        self._button_groups.clear()
        self._delay_controls.clear()
        for i in reversed(range(self._options_layout.count())):
            item = self._options_layout.takeAt(i)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._suggestion_label.clear()
        self._suggestion_button.setVisible(False)
        self._status_label.clear()
        self._resolution_label.clear()
        self._resolution_label.setStyleSheet("color:#444444;")

        items = self._conflict_list.selectedItems()
        if not items:
            self.viewer.clear_conflict_focus()
            return
        conflict = items[0].data(Qt.ItemDataRole.UserRole)
        if not conflict:
            self.viewer.clear_conflict_focus()
            return
        handles = tuple(conflict.get("agents", ()))
        self._current_handles = handles
        if handles:
            self.viewer.set_conflict_focus(handles)
        else:
            self.viewer.clear_conflict_focus()
        self._suggestion = self.viewer.suggest_conflict_free_solution(list(handles), [conflict])
        if self._suggestion:
            suggestion_text = self.viewer.describe_suggestion(self._suggestion)
            self._suggestion_label.setText(suggestion_text)
            self._suggestion_button.setVisible(True)
        else:
            self._suggestion_button.setVisible(False)

        for idx, handle in enumerate(handles):
            color = self.PREVIEW_COLORS[idx % len(self.PREVIEW_COLORS)]
            color_name = self._color_name_for_index(idx)
            header_row = QWidget()
            header_layout = QHBoxLayout()
            header_layout.setContentsMargins(0, 0, 0, 0)
            header_layout.setSpacing(6)
            color_chip = self._create_color_chip(color)
            if color_name:
                color_chip.setToolTip(f"{color_name} path highlight")
            header_layout.addWidget(color_chip, 0, Qt.AlignmentFlag.AlignVCenter)
            header_text = f"Train {handle} route options"
            if color_name:
                header_text += f" ({color_name})"
            header_label = QLabel(header_text + ":")
            header_label.setStyleSheet("font-weight:600;color:#f0f0f0;")
            header_layout.addWidget(header_label, 0, Qt.AlignmentFlag.AlignVCenter)
            header_layout.addStretch()
            header_row.setLayout(header_layout)
            self._options_layout.addWidget(header_row)
            options = self.viewer.get_path_options(handle)
            button_group = QButtonGroup(self)
            button_group.setExclusive(True)
            self._button_groups[handle] = button_group
            current_index = self.viewer.get_current_path_index(handle)
            if not options:
                info_label = QLabel("No alternative routes available.")
                info_label.setStyleSheet("color:#a0a0a0; font-style: italic;")
                self._options_layout.addWidget(info_label)
                continue
            for option in options:
                radio = QRadioButton(option["label"])
                option_index = option["index"]
                radio.setChecked(option_index == current_index)
                def _handler(checked: bool, h=handle, idx=option_index, col=color):
                    if checked:
                        self.viewer.set_preview_path(h, idx, col)
                        self._update_resolution_preview()
                radio.toggled.connect(_handler)
                button_group.addButton(radio, option_index)
                self._options_layout.addWidget(radio)
            self.viewer.set_preview_path(handle, current_index, color)

            delay_container = QVBoxLayout()
            delay_container.setContentsMargins(24, 2, 0, 0)
            delay_container.setSpacing(2)
            delay_row = QHBoxLayout()
            delay_row.setContentsMargins(0, 0, 0, 0)
            delay_row.setSpacing(6)
            delay_label = QLabel("Add delay (steps):")
            delay_label.setStyleSheet("color:#dcdcdc;")
            delay_spin = QSpinBox()
            delay_spin.setRange(0, 20)
            delay_spin.setValue(0)
            delay_spin.setToolTip("Number of steps to hold before the train resumes movement.")
            delay_spin.valueChanged.connect(self._on_delay_changed)
            self._delay_controls[handle] = delay_spin
            delay_row.addWidget(delay_label)
            delay_row.addWidget(delay_spin)
            delay_row.addStretch()
            delay_container.addLayout(delay_row)

            hold_remaining = self.viewer.get_agent_hold_remaining(handle)
            cumulative_delay = self.viewer.get_agent_cumulative_delay(handle)
            status_parts: List[str] = []
            if hold_remaining > 0:
                status_parts.append(f"Hold pending: {hold_remaining} step{'s' if hold_remaining != 1 else ''}")
            status_parts.append(f"Total applied: {cumulative_delay} step{'s' if cumulative_delay != 1 else ''}")
            status_label = QLabel(" | ".join(status_parts))
            status_label.setWordWrap(True)
            status_label.setStyleSheet("color:#a0a0a0; font-size:11px;")
            delay_container.addWidget(status_label)
            self._options_layout.addLayout(delay_container)

            if idx < len(handles) - 1:
                self._options_layout.addSpacing(8)

        self._update_resolution_preview()

    def update_conflicts(self, conflicts: List[Dict[str, Any]]) -> None:
        self._conflicts = conflicts
        self._populate_conflict_list()
        if conflicts:
            self._conflict_list.setCurrentRow(0)
        else:
            self.viewer.clear_preview_paths()
            self.viewer.clear_conflict_focus()


class FlatlandViewer(QMainWindow):
    """Viewer window that renders the Flatland environment and tracks malfunctions."""

    def __init__(
        self,
        env: RailEnv,
        step_interval_ms: int = STEP_INTERVAL_MS,
        model_path: Optional[str] = None,
        config: Optional[SimulationConfig] = None,
    ):
        super().__init__()
        self._env = env
        self._step_interval_ms = max(1, step_interval_ms)
        self._model_path = model_path
        self._simulation_config = config
        self.setWindowTitle("Flatland Multi-Agent Viewer")
        self.resize(QSize(1000, 700))
        self._display_label = ClickableLabel(self._handle_display_click)
        self._display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._display_label.setMinimumSize(400, 300)
        self._sidebar_header = QLabel("Malfunction Monitor")
        self._sidebar_header.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self._sidebar_header.setStyleSheet("font-weight: bold;")
        self._sidebar_on_title = QLabel("On-map malfunctions:")
        self._sidebar_on_title.setStyleSheet("font-weight: bold;")
        self._sidebar_on_label = QLabel("None")
        self._sidebar_on_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._sidebar_on_label.setWordWrap(True)
        self._sidebar_off_title = QLabel("Off-map malfunctions:")
        self._sidebar_off_title.setStyleSheet("font-weight: bold;")
        self._sidebar_off_label = QLabel("None")
        self._sidebar_off_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._sidebar_off_label.setWordWrap(True)
        self._end_button = QPushButton(" End Simulation")
        self._end_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self._end_button.clicked.connect(self._on_end_simulation)
        self._pause_button = QPushButton()
        self._pause_button.setCheckable(True)
        self._pause_button.toggled.connect(self._on_toggle_pause)
        self._restart_button = QPushButton(" Restart Simulation")
        self._restart_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self._restart_button.clicked.connect(self._on_restart_simulation)
        self._set_pause_button_appearance(paused=False)

        sidebar_layout = QVBoxLayout()
        sidebar_layout.addWidget(self._sidebar_header)
        sidebar_layout.addSpacing(8)
        sidebar_layout.addWidget(self._sidebar_on_title)
        sidebar_layout.addWidget(self._sidebar_on_label)
        sidebar_layout.addSpacing(8)
        sidebar_layout.addWidget(self._sidebar_off_title)
        sidebar_layout.addWidget(self._sidebar_off_label)
        sidebar_layout.addSpacing(12)
        sidebar_layout.addWidget(self._end_button)
        sidebar_layout.addWidget(self._restart_button)
        sidebar_layout.addWidget(self._pause_button)
        sidebar_layout.addStretch()

        sidebar_frame = QFrame()
        sidebar_frame.setFrameShape(QFrame.Shape.StyledPanel)
        sidebar_frame.setLayout(sidebar_layout)
        sidebar_frame.setMinimumWidth(220)

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self._display_label, stretch=1)
        main_layout.addWidget(sidebar_frame, stretch=0)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self._env.reset()
        self._renderer = RenderTool(self._env, gl="PILSVG", screen_width=1280, screen_height=720)
        self._renderer.reset()
        self._renderer.set_new_rail()
        self._step_count = self._get_env_step_count()
        self._last_frame: Optional[np.ndarray] = None
        self._episode_done = False
        self._is_paused = False
        self._manual_pause = False
        self._malfunctioned_handles: set[int] = set()
        self._last_malfunction_state = self._get_current_malfunction_state()
        self._movable_actions = [
            RailEnvActions.MOVE_FORWARD,
            RailEnvActions.MOVE_LEFT,
            RailEnvActions.MOVE_RIGHT,
            RailEnvActions.DO_NOTHING,
        ]
        self._last_highlight_rects: Dict[int, tuple[float, float, float, float]] = {}
        self._annotation_font = ImageFont.load_default()
        self._malfunction_start_steps: Dict[int, int] = {}
        self._incident_history: List[dict] = []
        self._incident_actions: Dict[int, List[dict]] = {}
        self._solution_windows: Dict[int, SolutionWindow] = {}
        self._solution_generation_windows: Dict[int, "SolutionGenerationWindow"] = {}
        self._formulate_windows: Dict[int, "FormulateSolutionWindow"] = {}
        self._analysis_windows: Dict[int, AnalysisWindow] = {}
        self._train_info_windows: Dict[int, "TrainInfoWindow"] = {}
        self._incident_analysis_windows: Dict[int, AnalysisWindow] = {}
        self._solution_window_count = 0
        self._incident_window: Optional[IncidentListWindow] = None
        self._reflection_windows: Dict[int, SelfReflectionWindow] = {}
        self._reflection_history: List[dict] = []
        self._last_agent_rects: Dict[int, tuple[float, float, float, float]] = {}
        self._conflict_dialog: Optional[ConflictResolutionDialog] = None
        self._conflict_predictor: Optional[ConflictPredictor] = None
        self._agent_cell_paths: Dict[int, List[Tuple[int, int]]] = {}
        self._agent_progress: Dict[int, int] = {}
        self._conflict_highlight_cells: Dict[Tuple[int, int], int] = {}
        self._conflict_agents: Set[int] = set()
        self._path_preview_cells: Dict[int, Tuple[List[Tuple[int, int]], Tuple[int, int, int, int]]] = {}
        self._agent_hold_steps_remaining: Dict[int, int] = {}
        self._agent_delay_plan: Dict[int, int] = {}
        self._held_agents_last_step: List[int] = []
        self._active_conflicts: List[Dict[str, Any]] = []
        self._focused_conflicts: List[Dict[str, Any]] = []
        self._conflict_focus_handles: Optional[Set[int]] = None
        self._active_conflict_signature: Optional[Tuple] = None
        self._resume_after_conflict: bool = False
        self._update_frame()
        self._timer = QTimer(self)
        self._timer.setInterval(self._step_interval_ms)
        self._timer.timeout.connect(self._on_timer_tick)
        self._timer.start()
        self._sidebar_timer = QTimer(self)
        self._sidebar_timer.setInterval(500)
        self._sidebar_timer.timeout.connect(self._on_sidebar_timer)
        self._sidebar_timer.start()
        self._update_sidebar()
        self._ensure_distance_map_ready()
        self._step_count = self._get_env_step_count()
        self._setup_conflict_predictor(show_dialog=False)
        self._evaluate_conflicts(show_dialog=True, force_dialog=True)

    def _ensure_distance_map_ready(self) -> None:
        distance_map = getattr(self._env, "distance_map", None)
        if distance_map is None:
            return
        try:
            distance_map.reset(self._env.agents, self._env.rail)
        except Exception:
            pass

    def _get_env_step_count(self) -> int:
        value = getattr(self._env, "_elapsed_steps", 0)
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def _planned_action_for_handle(self, handle: int) -> RailEnvActions:
        agent = self._env.agents[handle]
        path = self._agent_cell_paths.get(handle)
        if not path or len(path) < 2:
            return RailEnvActions.DO_NOTHING
        position = self._get_agent_position(handle)
        if position is None:
            position = agent.initial_position
        if position is None:
            return RailEnvActions.DO_NOTHING
        index = self._agent_progress.get(handle)
        if index is None:
            index = self._locate_position_index(path, position)
            if index is None:
                return RailEnvActions.DO_NOTHING
            self._agent_progress[handle] = index
        if index >= len(path) - 1:
            return RailEnvActions.DO_NOTHING
        next_cell = path[index + 1]
        desired_dir = self._direction_from_positions(position, next_cell)
        if desired_dir is None:
            return RailEnvActions.DO_NOTHING
        current_dir = agent.direction
        if current_dir is None:
            current_dir = getattr(agent, "initial_direction", None)
        if current_dir is None:
            return RailEnvActions.DO_NOTHING
        return self._action_for_direction_change(current_dir, desired_dir)

    def _setup_conflict_predictor(self, show_dialog: bool) -> None:
        self._close_conflict_dialog()
        self._conflict_predictor = ConflictPredictor(self._env)
        self._conflict_predictor.update_agents()
        self._rebuild_agent_plans()
        self._evaluate_conflicts(show_dialog=show_dialog, force_dialog=False)

    def _rebuild_agent_plans(self, handles: Optional[List[int]] = None) -> None:
        if self._conflict_predictor is None:
            return
        self._agent_cell_paths = {}
        self._agent_progress = {}
        if handles is None:
            handles = list(self._env.get_agent_handles())
        for handle in handles:
            cells = self._conflict_predictor.agent_cell_path(handle)
            if not cells:
                continue
            self._agent_cell_paths[handle] = cells
            position = self._get_agent_position(handle)
            if position is None:
                position = self._env.agents[handle].initial_position
            index = self._locate_position_index(cells, position)
            if index is None:
                index = 0
            self._agent_progress[handle] = index

    def _locate_position_index(self, cells: List[Tuple[int, int]], position: Optional[tuple[int, int]]) -> Optional[int]:
        if position is None:
            return None
        if isinstance(position, list):
            position = tuple(position)
        for idx, cell in enumerate(cells):
            if cell == position:
                return idx
        return None

    def _sync_agent_progress(self) -> None:
        for handle, cells in self._agent_cell_paths.items():
            position = self._get_agent_position(handle)
            if position is None:
                position = self._env.agents[handle].initial_position
            if position is None:
                continue
            index = self._locate_position_index(cells, position)
            if index is not None:
                self._agent_progress[handle] = index

    @staticmethod
    def _direction_from_positions(current: Tuple[int, int], nxt: Tuple[int, int]) -> Optional[int]:
        dr = nxt[0] - current[0]
        dc = nxt[1] - current[1]
        if dr == -1 and dc == 0:
            return 0
        if dr == 0 and dc == 1:
            return 1
        if dr == 1 and dc == 0:
            return 2
        if dr == 0 and dc == -1:
            return 3
        return None

    @staticmethod
    def _action_for_direction_change(current_dir: int, desired_dir: int) -> RailEnvActions:
        delta = (desired_dir - current_dir) % 4
        if delta == 0:
            return RailEnvActions.MOVE_FORWARD
        if delta == 1:
            return RailEnvActions.MOVE_RIGHT
        if delta == 3:
            return RailEnvActions.MOVE_LEFT
        return RailEnvActions.MOVE_FORWARD

    def _on_timer_tick(self) -> None:
        if self._episode_done or self._is_paused:
            self._update_frame()
            return
        dones = self._step_environment()
        self._episode_done = dones.get("__all__", False)
        if self._episode_done:
            self._timer.stop()
        self._update_frame()

    def _step_environment(self) -> Dict[int | str, bool]:
        agent_handles = self._env.get_agent_handles()
        if not agent_handles:
            return {"__all__": True}
        actions = self._sample_actions(agent_handles)
        _, _, dones, _ = self._env.step(actions)
        self._decrement_hold_steps()
        self._sync_agent_progress()
        self._step_count = self._get_env_step_count()
        self._detect_malfunctions()
        self._evaluate_conflicts(show_dialog=True)
        return dones

    def _sample_actions(self, agent_handles) -> Dict[int, RailEnvActions]:
        actions: Dict[int, RailEnvActions] = {}
        self._sync_agent_progress()
        held_this_step: List[int] = []
        for handle in agent_handles:
            agent = self._env.agents[handle]
            if agent.state == TrainState.DONE:
                self._agent_hold_steps_remaining.pop(handle, None)
                actions[handle] = RailEnvActions.DO_NOTHING
                continue
            hold_remaining = self._agent_hold_steps_remaining.get(handle, 0)
            if hold_remaining > 0:
                actions[handle] = RailEnvActions.DO_NOTHING
                held_this_step.append(handle)
                continue
            if agent.malfunction_handler.in_malfunction:
                actions[handle] = RailEnvActions.DO_NOTHING
                continue
            actions[handle] = self._planned_action_for_handle(handle)
        self._held_agents_last_step = held_this_step
        return actions

    def _decrement_hold_steps(self) -> None:
        if not self._held_agents_last_step:
            return
        for handle in self._held_agents_last_step:
            remaining = self._agent_hold_steps_remaining.get(handle)
            if remaining is None:
                continue
            new_remaining = remaining - 1
            if new_remaining > 0:
                self._agent_hold_steps_remaining[handle] = new_remaining
            else:
                self._agent_hold_steps_remaining.pop(handle, None)
        self._held_agents_last_step = []

    def _get_current_malfunction_state(self) -> Dict[int, bool]:
        return {
            handle: self._env.agents[handle].malfunction_handler.in_malfunction
            for handle in self._env.get_agent_handles()
        }

    def _detect_malfunctions(self) -> None:
        current_state = self._get_current_malfunction_state()
        current_handles = {
            handle for handle, is_malfunction in current_state.items() if is_malfunction
        }
        newly_malfunctioning = [
            handle for handle in current_handles
            if not self._last_malfunction_state.get(handle, False)
        ]
        now_monotonic = time.monotonic()
        now_wall = time.time()
        for handle in newly_malfunctioning:
            self._malfunction_start_steps.setdefault(handle, self._step_count)
            agent_state = self._env.agents[handle].state
            is_on_map = agent_state.is_on_map_state() if hasattr(agent_state, "is_on_map_state") else agent_state in (
                TrainState.MOVING,
                TrainState.STOPPED,
                TrainState.MALFUNCTION,
            )
            incident = {
                "id": len(self._incident_history),
                "handle": handle,
                "start_time": now_monotonic,
                "wall_time": now_wall,
                "start_step": self._step_count,
                "on_map": is_on_map,
            }
            self._incident_history.append(incident)
            self._incident_actions.setdefault(incident["id"], [])
        for handle in list(self._malfunction_start_steps.keys()):
            if handle not in current_handles:
                self._malfunction_start_steps.pop(handle, None)
        self._malfunctioned_handles = current_handles
        self._last_malfunction_state = current_state
        self._update_sidebar()

    def _update_frame(self) -> None:
        self._renderer.render_env(show=False, show_observations=False)
        frame = self._renderer.get_image()
        if frame is None:
            return
        if frame.dtype != np.uint8:
            frame = frame.astype(np.uint8)
        frame = np.ascontiguousarray(frame)
        frame = self._annotate_frame(frame)
        self._last_frame = frame
        self._push_frame_to_label(frame)

    def resizeEvent(self, event):  # type: ignore[override]
        super().resizeEvent(event)
        if self._last_frame is not None:
            self._push_frame_to_label(self._last_frame)

    def _push_frame_to_label(self, frame: np.ndarray) -> None:
        height, width, channels = frame.shape
        if channels == 4:
            fmt = QImage.Format.Format_RGBA8888
        elif channels == 3:
            fmt = QImage.Format.Format_RGB888
        else:
            raise ValueError(f"Unexpected channel count: {channels}")
        bytes_per_line = channels * width
        q_image = QImage(frame.data, width, height, bytes_per_line, fmt)
        pixmap = QPixmap.fromImage(q_image)
        scaled = pixmap.scaled(
            self._display_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        label_width = self._display_label.width()
        label_height = self._display_label.height()
        offset_x = (label_width - scaled.width()) / 2
        offset_y = (label_height - scaled.height()) / 2
        self._update_highlight_rects(scaled.width(), scaled.height(), offset_x, offset_y)
        self._display_label.setPixmap(scaled)

    def _annotate_frame(self, frame: np.ndarray) -> np.ndarray:
        if self._env.width == 0 or self._env.height == 0:
            return frame
        original_channels = frame.shape[2]
        image = Image.fromarray(frame).convert("RGBA")
        draw = ImageDraw.Draw(image)
        img_width, img_height = image.size
        cell_width = img_width / self._env.width
        cell_height = img_height / self._env.height
        border_thickness = max(1, int(min(cell_width, cell_height) * 0.12))
        self._draw_station_labels(draw, cell_width, cell_height, img_width, img_height)
        self._draw_path_previews(draw, cell_width, cell_height)
        self._draw_conflict_overlays(draw, cell_width, cell_height)
        self._draw_agent_annotations(draw, cell_width, cell_height, img_width, img_height, border_thickness)
        self._draw_step_counter(draw, img_width, img_height)
        annotated = image.convert("RGB") if original_channels == 3 else image
        return np.array(annotated)

    def _draw_station_labels(
        self,
        draw: ImageDraw.ImageDraw,
        cell_width: float,
        cell_height: float,
        img_width: float,
        img_height: float,
    ) -> None:
        stations = getattr(self._env, "stations", None)
        if not stations:
            return
        for station in stations:
            position: Optional[tuple[int, int]] = None
            label: Optional[str] = None
            if isinstance(station, dict):
                row = station.get("r")
                col = station.get("c")
                if row is None or col is None:
                    continue
                position = (row, col)
                label = station.get("name")
                station_id = station.get("id")
                if not label and station_id is not None:
                    label = f"Station {station_id}"
            elif isinstance(station, (list, tuple)) and len(station) >= 3:
                row, col, station_id = station[:3]
                position = (row, col)
                label = f"Station {station_id}"
            if position is None:
                continue
            if not label:
                label = f"({position[0]}, {position[1]})"
            row, col = position
            left = col * cell_width
            top = row * cell_height
            text_width, text_height = self._measure_text(draw, label)
            padding = 3
            background_rect = [
                left + padding,
                max(0, top - text_height - padding * 2),
                min(img_width, left + padding + text_width + padding * 2),
                max(0, top - padding),
            ]
            self._draw_text_with_background(
                draw,
                label,
                (background_rect[0], background_rect[1]),
                background_rect,
                fill=(255, 255, 255, 230),
                background=(0, 0, 0, 170),
            )

    def _draw_conflict_overlays(
        self,
        draw: ImageDraw.ImageDraw,
        cell_width: float,
        cell_height: float,
    ) -> None:
        if not self._conflict_highlight_cells:
            return
        outline_width = max(2, int(min(cell_width, cell_height) * 0.12))
        for (row, col), count in self._conflict_highlight_cells.items():
            left = col * cell_width
            top = row * cell_height
            right = left + cell_width
            bottom = top + cell_height
            draw.rectangle(
                [left, top, right, bottom],
                outline=(255, 0, 0, 255),
                width=outline_width,
            )

    def _draw_path_previews(
        self,
        draw: ImageDraw.ImageDraw,
        cell_width: float,
        cell_height: float,
    ) -> None:
        if not self._path_preview_cells:
            return
        handle_colors = {handle: color for handle, (_, color) in self._path_preview_cells.items()}
        cell_handles: Dict[Tuple[int, int], Set[int]] = {}
        for handle, (cells, _) in self._path_preview_cells.items():
            for row, col in cells:
                cell_handles.setdefault((row, col), set()).add(handle)
        overlap_color = (128, 0, 128, 160)
        for (row, col), handles in cell_handles.items():
            if not handles:
                continue
            if len(handles) > 1:
                fill_color = overlap_color
            else:
                handle = next(iter(handles))
                fill_color = handle_colors.get(handle)
                if fill_color is None:
                    continue
            left = col * cell_width
            top = row * cell_height
            right = left + cell_width
            bottom = top + cell_height
            inset = min(cell_width, cell_height) * 0.25
            if inset > 0:
                left += inset
                top += inset
                right -= inset
                bottom -= inset
                if right <= left or bottom <= top:
                    left = col * cell_width
                    top = row * cell_height
                    right = left + cell_width
                    bottom = top + cell_height
            draw.rectangle(
                [left, top, right, bottom],
                fill=fill_color,
            )

    def _draw_agent_annotations(
        self,
        draw: ImageDraw.ImageDraw,
        cell_width: float,
        cell_height: float,
        img_width: float,
        img_height: float,
        border_thickness: int,
    ) -> None:
        for handle in self._env.get_agent_handles():
            pos = self._get_agent_position(handle)
            if pos is None:
                continue
            row, col = pos
            left = col * cell_width
            top = row * cell_height
            right = left + cell_width
            bottom = top + cell_height
            outline = None
            if handle in self._malfunctioned_handles:
                outline = (255, 0, 0, 255)
            elif handle in self._conflict_agents:
                outline = (255, 165, 0, 255)
            if outline is not None:
                draw.rectangle(
                    [left, top, right, bottom],
                    outline=outline,
                    width=border_thickness,
                )
            text = str(handle)
            text_width, text_height = self._measure_text(draw, text)
            padding = 3
            background_rect = [
                left + padding,
                top + padding,
                min(img_width, left + padding + text_width + padding * 2),
                min(img_height, top + padding + text_height + padding * 2),
            ]
            self._draw_text_with_background(
                draw,
                text,
                (background_rect[0], background_rect[1]),
                background_rect,
                fill=(255, 255, 255, 230),
                background=(0, 0, 0, 180),
            )

    def _draw_text_with_background(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        position: tuple[float, float],
        background_rect: List[float],
        fill: tuple[int, int, int, int],
        background: tuple[int, int, int, int],
    ) -> None:
        rect = [int(val) for val in background_rect]
        draw.rectangle(rect, fill=background)
        draw.text((int(position[0]), int(position[1])), text, font=self._annotation_font, fill=fill)

    def _measure_text(self, draw: ImageDraw.ImageDraw, text: str) -> tuple[int, int]:
        if hasattr(draw, "textbbox"):
            bbox = draw.textbbox((0, 0), text, font=self._annotation_font)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            return int(width), int(height)
        width, height = draw.textsize(text, font=self._annotation_font)
        return int(width), int(height)

    def _get_agent_position(self, handle: int) -> Optional[tuple[int, int]]:
        agent = self._env.agents[handle]
        return agent.position or agent.old_position

    def _update_highlight_rects(self, scaled_width: float, scaled_height: float, offset_x: float, offset_y: float) -> None:
        self._last_agent_rects = {}
        self._last_highlight_rects = {}
        if scaled_width <= 0 or scaled_height <= 0 or not self._env.width or not self._env.height:
            return
        cell_w = scaled_width / self._env.width
        cell_h = scaled_height / self._env.height
        for handle in self._env.get_agent_handles():
            pos = self._get_agent_position(handle)
            if pos is None:
                continue
            row, col = pos
            x = offset_x + col * cell_w
            y = offset_y + row * cell_h
            rect = (x, y, cell_w, cell_h)
            self._last_agent_rects[handle] = rect
            if handle in self._malfunctioned_handles:
                self._last_highlight_rects[handle] = rect

    def _filter_conflicts(self, conflicts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        focus = self._conflict_focus_handles
        if not focus:
            return list(conflicts)
        filtered: List[Dict[str, Any]] = []
        for conflict in conflicts:
            agents = tuple(conflict.get("agents", ()))
            if not agents:
                continue
            agent_set = set(agents)
            if agent_set and agent_set.issubset(focus) and len(agent_set) >= 2:
                filtered.append(conflict)
        return filtered

    def _update_conflict_overlays(self, conflicts: List[Dict[str, Any]]) -> None:
        relevant_conflicts = self._filter_conflicts(conflicts)
        self._focused_conflicts = relevant_conflicts
        self._conflict_highlight_cells = {}
        self._conflict_agents = set()
        for conflict in relevant_conflicts:
            cells: Set[Tuple[int, int]] = set()
            resource_id = conflict.get("resource_id")
            if isinstance(resource_id, tuple) and resource_id:
                if resource_id[0] == "cells":
                    cells.update(resource_id[1])
            for edge_key in ("edge_A", "edge_B"):
                edge = conflict.get(edge_key)
                if edge and self._conflict_predictor is not None:
                    u, v, key = edge
                    attr = self._conflict_predictor.graph.graph[u][v][key]["attr"]
                    resources = attr.get("resources", [])
                    cells.add(u)
                    cells.add(v)
                    cells.update(cell for cell, _ in resources)
            for cell in cells:
                self._conflict_highlight_cells[cell] = self._conflict_highlight_cells.get(cell, 0) + 1
            agents = conflict.get("agents", ())
            for agent in agents:
                self._conflict_agents.add(agent)
        self._update_frame()

    def _draw_step_counter(self, draw: ImageDraw.ImageDraw, img_width: float, img_height: float) -> None:
        text_parts = [f"Step {self._step_count}"]
        if self._episode_done:
            text_parts.append("Finished")
        elif self._is_paused:
            text_parts.append("Paused")
        text = " | ".join(text_parts)
        padding = 6
        text_width, text_height = self._measure_text(draw, text)
        left = padding
        top = padding
        background_rect = [
            left - padding,
            top - padding,
            min(img_width, left + text_width + padding),
            min(img_height, top + text_height + padding),
        ]
        self._draw_text_with_background(
            draw,
            text,
            (left, top),
            background_rect,
            fill=(255, 255, 255, 240),
            background=(0, 0, 0, 180),
        )

    def set_conflict_focus(self, handles: Iterable[int]) -> None:
        focus_set = {int(handle) for handle in handles if handle is not None}
        if not focus_set:
            self.clear_conflict_focus()
            return
        if self._conflict_focus_handles == focus_set:
            return
        self._conflict_focus_handles = focus_set
        self._update_conflict_overlays(self._active_conflicts)

    def clear_conflict_focus(self) -> None:
        if self._conflict_focus_handles is None:
            return
        self._conflict_focus_handles = None
        self._update_conflict_overlays(self._active_conflicts)

    def _evaluate_conflicts(self, show_dialog: bool = False, force_dialog: bool = False) -> None:
        if self._conflict_predictor is None:
            return
        self._conflict_predictor.update_agents()
        self._conflict_predictor.conflict_matrix()
        conflicts = list(self._conflict_predictor.detected_conflicts)
        self._active_conflicts = conflicts
        self._update_conflict_overlays(conflicts)
        signature = tuple(
            sorted(
                (
                    conflict.get("resource_id"),
                    tuple(sorted(conflict.get("agents", ())))
                )
                for conflict in conflicts
            )
        ) if conflicts else None
        if conflicts:
            should_notify = show_dialog and (
                force_dialog
                or signature != self._active_conflict_signature
                or self._conflict_dialog is None
            )
            if should_notify:
                self._active_conflict_signature = signature
                self._notify_conflicts(conflicts)
            else:
                self._active_conflict_signature = signature
        else:
            self._active_conflict_signature = None
            self._conflict_agents.clear()
            self._conflict_highlight_cells.clear()
            self._close_conflict_dialog()
            self._resume_after_conflict_if_needed()

    def _notify_conflicts(self, conflicts: List[Dict[str, Any]]) -> None:
        self._pause_for_conflict_dialog()
        self._close_conflict_dialog()
        dialog = ConflictResolutionDialog(self, conflicts, self)
        dialog.finished.connect(self._on_conflict_dialog_closed)
        self._conflict_dialog = dialog
        dialog.show()

    def _pause_for_conflict_dialog(self) -> None:
        if self._episode_done:
            return
        if not self._is_paused:
            self._timer.stop()
            self._resume_after_conflict = not self._manual_pause
            self._is_paused = True

    def _resume_after_conflict_if_needed(self) -> None:
        if self._resume_after_conflict and not self._episode_done:
            self._is_paused = False
            self._timer.start()
        self._resume_after_conflict = False

    def ensure_simulation_running(self) -> None:
        if self._episode_done or self._manual_pause:
            return
        self._is_paused = False
        if not self._timer.isActive():
            self._timer.start()

    def _close_conflict_dialog(self) -> None:
        if self._conflict_dialog is not None and not sip.isdeleted(self._conflict_dialog):
            try:
                self._conflict_dialog.finished.disconnect(self._on_conflict_dialog_closed)  # type: ignore[arg-type]
            except Exception:
                pass
            try:
                self._conflict_dialog.close()
            except RuntimeError:
                pass
        self._conflict_dialog = None

    def _on_conflict_dialog_closed(self, result: int) -> None:
        self.clear_preview_paths()
        self._conflict_dialog = None
        if not self._active_conflicts:
            self.clear_conflict_focus()
            self.ensure_simulation_running()
            self._resume_after_conflict_if_needed()

    def describe_conflicts(self, conflicts: List[Dict[str, Any]]) -> str:
        if not conflicts:
            return "No conflicts detected."
        lines = []
        for conflict in conflicts:
            agents = conflict.get("agents", ())
            agent_text = " and ".join(str(a) for a in agents) if agents else "Unknown trains"
            resource_id = conflict.get("resource_id")
            if isinstance(resource_id, tuple) and resource_id and resource_id[0] == "cells":
                cells = sorted(resource_id[1])
                cell_text = ", ".join(f"({r},{c})" for r, c in cells)
            else:
                cell_text = str(resource_id)
            interval = conflict.get("interval_A")
            time_text = ""
            if isinstance(interval, tuple):
                time_text = f" between t={interval[0]:.1f} and t={interval[1]:.1f}"
            lines.append(f"Trains {agent_text} share track segment {cell_text}{time_text}.")
        return "\n".join(lines)

    def get_path_options(self, handle: int) -> List[Dict[str, Any]]:
        if self._conflict_predictor is None:
            return []
        path_ids = self._conflict_predictor.get_available_paths(handle)
        options: List[Dict[str, Any]] = []
        for idx, path_id in enumerate(path_ids):
            cells = self._conflict_predictor.path_cells(path_id)
            steps = max(0, len(cells) - 1)
            label = f"Option {idx + 1}: {steps} steps"
            options.append({"index": idx, "label": label})
        return options

    def get_current_path_index(self, handle: int) -> int:
        if self._conflict_predictor is None:
            return 0
        return self._conflict_predictor.get_selected_path_index(handle)

    def get_agent_hold_remaining(self, handle: int) -> int:
        return self._agent_hold_steps_remaining.get(handle, 0)

    def get_agent_cumulative_delay(self, handle: int) -> int:
        return self._agent_delay_plan.get(handle, 0)

    def describe_suggestion(self, suggestion: Dict[int, int]) -> str:
        if not suggestion:
            return "No conflict-free alternative could be found automatically."
        parts = [f"Train {handle} ? option {index + 1}" for handle, index in suggestion.items()]
        return "Suggested conflict-free combination: " + ", ".join(parts)

    def suggest_conflict_free_solution(self, handles: List[int], conflicts: List[Dict[str, Any]]) -> Dict[int, int]:
        if self._conflict_predictor is None:
            return {}
        path_spaces: Dict[int, List[int]] = {}
        for handle in handles:
            options = self._conflict_predictor.get_available_paths(handle)
            if not options:
                return {}
            path_spaces[handle] = list(range(min(len(options), 4)))
        for combination in product(*(path_spaces[h] for h in handles)):
            overrides = {handle: idx for handle, idx in zip(handles, combination)}
            _, conflicts_after = self._conflict_predictor.evaluate_selection(overrides)
            if not conflicts_after:
                return overrides
        return {}

    def preview_conflict_resolution(self, selections: Dict[int, int], delays: Dict[int, int]) -> Tuple[bool, List[Dict[str, Any]]]:
        if self._conflict_predictor is None:
            return True, []
        delay_overrides: Dict[int, int] = dict(self._agent_delay_plan)
        for handle, value in delays.items():
            additional = max(0, int(value))
            if additional > 0:
                delay_overrides[handle] = delay_overrides.get(handle, 0) + additional
            elif handle not in delay_overrides:
                delay_overrides[handle] = 0
        delay_overrides = {h: v for h, v in delay_overrides.items() if v > 0}
        _, conflicts = self._conflict_predictor.evaluate_selection(selections, delay_overrides=delay_overrides)
        filtered = self._filter_conflicts(conflicts)
        return not filtered, filtered

    def apply_path_selection(self, selections: Dict[int, int], delays: Optional[Dict[int, int]] = None) -> Tuple[bool, List[Dict[str, Any]]]:
        if self._conflict_predictor is None:
            return True, []
        changed = False
        for handle, index in selections.items():
            if self._conflict_predictor.get_selected_path_index(handle) != index:
                self._conflict_predictor.select_agent_path(handle, index)
                changed = True
        self._update_agent_delays(delays or {})
        if changed:
            self._rebuild_agent_plans()
        self._evaluate_conflicts(show_dialog=False)
        filtered_conflicts = self._filter_conflicts(self._active_conflicts)
        resolved = not filtered_conflicts
        return resolved, filtered_conflicts

    def _update_agent_delays(self, delays: Dict[int, int]) -> None:
        if not delays and not self._agent_delay_plan:
            return
        for handle, value in delays.items():
            steps = max(0, int(value))
            if steps > 0:
                cumulative = self._agent_delay_plan.get(handle, 0) + steps
                self._agent_delay_plan[handle] = cumulative
                self._agent_hold_steps_remaining[handle] = steps
                if self._conflict_predictor is not None:
                    self._conflict_predictor.set_agent_delay(handle, cumulative)
            else:
                self._agent_hold_steps_remaining.pop(handle, None)
                if handle not in self._agent_delay_plan and self._conflict_predictor is not None:
                    self._conflict_predictor.clear_agent_delay(handle)

    def refresh_conflict_state(self, conflicts: Optional[List[Dict[str, Any]]] = None) -> None:
        if conflicts is not None:
            self._active_conflicts = conflicts
        base_conflicts = self._active_conflicts
        self._update_conflict_overlays(base_conflicts)
        if base_conflicts:
            signature = tuple(
                sorted(
                    (
                        conflict.get("resource_id"),
                        tuple(sorted(conflict.get("agents", ())))
                    )
                    for conflict in base_conflicts
                )
            )
            self._active_conflict_signature = signature
            if self._conflict_dialog is not None and not sip.isdeleted(self._conflict_dialog):
                try:
                    self._conflict_dialog.update_conflicts(base_conflicts)
                except RuntimeError:
                    pass
        else:
            self._active_conflict_signature = None
            if self._conflict_dialog is not None and not sip.isdeleted(self._conflict_dialog):
                try:
                    self._conflict_dialog.update_conflicts([])
                except RuntimeError:
                    pass

    def set_preview_path(self, agent_handle: int, path_index: int, color: Tuple[int, int, int, int]) -> None:
        if self._conflict_predictor is None:
            return
        path_ids = self._conflict_predictor.get_available_paths(agent_handle)
        if path_index < 0 or path_index >= len(path_ids):
            return
        cells = self._conflict_predictor.path_cells(path_ids[path_index])
        self._path_preview_cells[agent_handle] = (cells, color)
        self._update_frame()

    def clear_preview_paths(self) -> None:
        if self._path_preview_cells:
            self._path_preview_cells.clear()
            self._update_frame()
    def _on_sidebar_timer(self) -> None:
        self._update_sidebar()
        for handle, window in list(self._solution_windows.items()):
            try:
                window.refresh()
            except RuntimeError:
                self._solution_windows.pop(handle, None)
        for handle, window in list(self._train_info_windows.items()):
            if sip.isdeleted(window):
                self._train_info_windows.pop(handle, None)
                continue
            try:
                window.refresh()
            except RuntimeError:
                self._train_info_windows.pop(handle, None)
        for incident_id, window in list(self._incident_analysis_windows.items()):
            if sip.isdeleted(window):
                self._incident_analysis_windows.pop(incident_id, None)
                continue
            incident = next((item for item in self._incident_history if item["id"] == incident_id), None)
            if incident is None:
                self._incident_analysis_windows.pop(incident_id, None)
                continue
            payload = self._build_incident_analysis_payload(
                incident, self.get_incident_actions(incident_id)
            )
            callback = lambda iid=incident_id: self._open_self_reflection(iid)
            try:
                window.update_incident_payload(payload, callback)
            except RuntimeError:
                self._incident_analysis_windows.pop(incident_id, None)
        self._refresh_incident_window()

    def _update_sidebar(self) -> None:
        if not self._malfunctioned_handles:
            self._sidebar_on_label.setText("None")
            self._sidebar_off_label.setText("None")
            return
        on_lines = []
        off_lines = []
        for handle in sorted(self._malfunctioned_handles):
            start_step = self._malfunction_start_steps.get(handle)
            elapsed_steps = (
                self._step_count - start_step if start_step is not None else None
            )
            elapsed_text = (
                f"{elapsed_steps} step{'s' if elapsed_steps != 1 else ''}"
                if elapsed_steps is not None and elapsed_steps >= 0
                else "N/A"
            )
            entry = f"Train {handle}: {elapsed_text}"
            agent_state = self._env.agents[handle].state
            is_on_map = agent_state.is_on_map_state() if hasattr(agent_state, "is_on_map_state") else agent_state in (
                TrainState.MOVING,
                TrainState.STOPPED,
                TrainState.MALFUNCTION,
            )
            if is_on_map:
                on_lines.append(entry)
            else:
                off_lines.append(entry)
        self._sidebar_on_label.setText("\n".join(on_lines) if on_lines else "None")
        self._sidebar_off_label.setText("\n".join(off_lines) if off_lines else "None")

    def _refresh_incident_window(self) -> None:
        if self._incident_window is None or sip.isdeleted(self._incident_window):
            return
        try:
            self._incident_window.refresh()
        except RuntimeError:
            self._incident_window = None

    def get_incidents(self) -> List[dict]:
        return list(self._incident_history)

    def log_reflection(self, incident: dict, responses: Dict[int, str]) -> None:
        log_entry = {
            "incident": incident,
            "responses": responses,
            "logged_at": time.time(),
        }
        self._reflection_history.append(log_entry)
        print("[Reflection]", log_entry)

    def record_solution_action(self, handle: int, source: str, description: str) -> None:
        if not description:
            return
        incident = next(
            (item for item in reversed(self._incident_history) if item["handle"] == handle),
            None,
        )
        if incident is None:
            return
        incident_id = incident["id"]
        actions = self._incident_actions.setdefault(incident_id, [])
        entry = {
            "source": source,
            "description": description,
            "step": f"Step {self._step_count}",
        }
        actions.append(entry)

    def get_incident_actions(self, incident_id: int) -> List[dict]:
        return list(self._incident_actions.get(incident_id, []))

    def _build_incident_analysis_payload(self, incident: dict, actions: List[dict]) -> dict:
        handle = incident["handle"]
        impacted = [(f"Train {handle}", "Primary incident train")]
        summary = {
            "risk": ("Risk Assessment", "Medium"),
            "actions": ("Number of Actions", str(len(actions))),
            "impact": ("Impacted Trains", str(len(impacted))),
        }
        action_rows = [
            {
                "source": action.get("source", ""),
                "description": action.get("description", ""),
                "step": action.get("step", ""),
            }
            for action in actions
        ]
        heading = f"Incident Review - Train {handle}"
        subheading = "Post-incident summary and actions"
        window_title = f"Incident Analysis - Train {handle}"
        return {
            "heading": heading,
            "subheading": subheading,
            "window_title": window_title,
            "summary": summary,
            "impacted": impacted,
            "actions": action_rows,
            "reflection_label": "Open Reflection",
        }

    def _on_end_simulation(self) -> None:
        if self._episode_done:
            return
        self._close_conflict_dialog()
        self.clear_preview_paths()
        self.clear_conflict_focus()
        self._episode_done = True
        self._is_paused = True
        self._manual_pause = False
        self._timer.stop()
        self._end_button.setEnabled(False)
        self._pause_button.blockSignals(True)
        self._pause_button.setChecked(False)
        self._pause_button.blockSignals(False)
        self._set_pause_button_appearance(paused=False)
        self._pause_button.setEnabled(False)
        self._sidebar_header.setText("Malfunction Monitor (Simulation Ended)")
        self._agent_hold_steps_remaining.clear()
        self._agent_delay_plan.clear()
        self._update_frame()
        self._open_incident_list()

    def _set_pause_button_appearance(self, paused: bool) -> None:
        if paused:
            text = " Resume Simulation"
            icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        else:
            text = " Pause Simulation"
            icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause)
        self._pause_button.setText(text)
        self._pause_button.setIcon(icon)

    def _on_toggle_pause(self, checked: bool) -> None:
        self._manual_pause = checked
        self._set_pause_button_appearance(paused=checked)
        if checked:
            self._is_paused = True
            self._timer.stop()
        else:
            if self._solution_window_count == 0 and not self._episode_done:
                self._is_paused = False
                self._timer.start()
            else:
                self._is_paused = True
                self._timer.stop()

    def _on_restart_simulation(self) -> None:
        self._timer.stop()
        self._manual_pause = True
        self._close_all_auxiliary_windows()
        self._manual_pause = False
        self._pause_button.blockSignals(True)
        self._pause_button.setChecked(False)
        self._pause_button.blockSignals(False)
        self._pause_button.setEnabled(True)
        self._set_pause_button_appearance(paused=False)
        self._end_button.setEnabled(True)
        self._sidebar_header.setText("Malfunction Monitor")
        self._episode_done = False
        self._is_paused = False
        self._solution_window_count = 0
        self._malfunction_start_steps.clear()
        self._malfunctioned_handles.clear()
        self._last_highlight_rects = {}
        self._last_agent_rects = {}
        self._incident_history.clear()
        self._incident_actions.clear()
        self._reflection_history.clear()
        self._env.reset()
        self._renderer.reset()
        self._renderer.set_new_rail()
        self._last_malfunction_state = self._get_current_malfunction_state()
        self._ensure_distance_map_ready()
        self._step_count = self._get_env_step_count()
        self._update_frame()
        self._update_sidebar()
        self._setup_conflict_predictor(show_dialog=False)
        self._timer.start()

    def _close_all_auxiliary_windows(self) -> None:
        for windows in (
            self._solution_windows,
            self._solution_generation_windows,
            self._formulate_windows,
            self._analysis_windows,
            self._train_info_windows,
            self._incident_analysis_windows,
        ):
            for window in list(windows.values()):
                self._close_window(window)
            windows.clear()
        for window in list(self._reflection_windows.values()):
            self._close_window(window)
        self._reflection_windows.clear()
        self._incident_window = self._close_window(self._incident_window)

    @staticmethod
    def _close_window(window):
        if window is None or sip.isdeleted(window):
            return None
        try:
            window.close()
        except RuntimeError:
            pass
        return None

    def _open_incident_list(self) -> None:
        if self._incident_window is not None and not sip.isdeleted(self._incident_window):
            self._incident_window.raise_()
            self._incident_window.activateWindow()
            self._incident_window.refresh()
            return
        self._incident_window = IncidentListWindow(self)
        self._incident_window.show()

    def _open_incident_analysis(self, incident_id: int) -> Optional[AnalysisWindow]:
        incident = next((item for item in self._incident_history if item["id"] == incident_id), None)
        if incident is None:
            return None
        actions = self.get_incident_actions(incident_id)
        payload = self._build_incident_analysis_payload(incident, actions)
        callback = lambda iid=incident_id: self._open_self_reflection(iid)
        window = self._incident_analysis_windows.get(incident_id)
        if window is not None and not sip.isdeleted(window):
            window.update_incident_payload(payload, callback)
            window.raise_()
            window.activateWindow()
            return window
        window = AnalysisWindow(
            self,
            incident["handle"],
            "incident",
            parent=self,
            payload=payload,
            reflection_callback=callback,
            on_close=lambda _handle, iid=incident_id: self._on_incident_analysis_close(iid),
        )
        self._incident_analysis_windows[incident_id] = window
        window.show()
        return window

    def _on_incident_window_close(self) -> None:
        self._incident_window = None

    def _on_incident_analysis_close(self, incident_id: int) -> None:
        self._incident_analysis_windows.pop(incident_id, None)

    def _open_self_reflection(self, incident_id: int) -> None:
        window = self._reflection_windows.get(incident_id)
        if window is not None and not sip.isdeleted(window):
            window.raise_()
            window.activateWindow()
            return
        self._reflection_windows.pop(incident_id, None)
        incident = next((item for item in self._incident_history if item["id"] == incident_id), None)
        if incident is None:
            return
        window = SelfReflectionWindow(self, incident)
        self._reflection_windows[incident_id] = window
        window.show()

    def _on_reflection_window_close(self, incident_id: int) -> None:
        self._reflection_windows.pop(incident_id, None)

    def format_malfunction_summary(self, handle: int) -> str:
        agent = self._env.agents[handle]
        origin = self._describe_station(agent.initial_position)
        destination = self._describe_station(agent.target)
        remaining_steps = agent.malfunction_handler.malfunction_down_counter
        expected_delay_seconds = remaining_steps * (self._step_interval_ms / 1000.0)
        start_step = self._malfunction_start_steps.get(handle)
        elapsed_steps = (
            self._step_count - start_step if start_step is not None else None
        )
        delay_text = f"{expected_delay_seconds:.1f}s (~{remaining_steps} step{'s' if remaining_steps != 1 else ''})"
        if elapsed_steps is not None and elapsed_steps >= 0:
            elapsed_text = f"{elapsed_steps} step{'s' if elapsed_steps != 1 else ''}"
        else:
            elapsed_text = "N/A"
        return (
            f"Train {handle}: {origin} -> {destination}\n"
            f"  Expected delay: {delay_text}\n"
            f"  Active for: {elapsed_text}"
        )

    def _describe_station(self, position: Optional[tuple[int, int]]) -> str:
        if position is None:
            return "Unknown"
        stations = getattr(self._env, "stations", None)
        if stations:
            for station in stations:
                if isinstance(station, dict):
                    row = station.get("r")
                    col = station.get("c")
                    if row == position[0] and col == position[1]:
                        name = station.get("name")
                        identifier = station.get("id")
                        if name:
                            return f"{name} ({identifier})" if identifier is not None else name
                        if identifier is not None:
                            return f"Station {identifier}"
                elif isinstance(station, (list, tuple)) and len(station) >= 3:
                    row, col, identifier = station[:3]
                    if row == position[0] and col == position[1]:
                        return f"Station {identifier}"
        row, col = position
        return f"({row}, {col})"

    def get_train_details(self, handle: int) -> dict:
        if handle < 0 or handle >= len(self._env.agents):
            return {}
        agent = self._env.agents[handle]
        train_type = getattr(agent, "agent_type", None)
        if hasattr(train_type, "name"):
            train_type_text = train_type.name.replace("_", " ").title()
        else:
            train_type_text = str(train_type) if train_type is not None else "Unknown"
        identifier = str(getattr(agent, "handle", handle))
        state = getattr(agent, "state", None)


        state_text = getattr(state, "name", str(state)) if state is not None else "Unknown"
        current_position = agent.position or getattr(agent, "old_position", None) or agent.initial_position
        direction = getattr(agent, "direction", None)
        speed = getattr(agent, "speed_counter", 0)
        speed_text = f"{speed:.2f} cells/step" if isinstance(speed, (int, float)) else "Unknown"
        origin_text = self._describe_station(agent.initial_position)
        target_text = self._describe_station(agent.target)
        waypoint_rows = self._extract_agent_waypoints(agent)
        if not waypoint_rows:
            self._ensure_distance_map_ready()
            waypoint_rows = self._fallback_waypoints(handle)
        next_waypoint = "N/A"
        for row in waypoint_rows:
            if row.get("role") != "Origin":
                next_waypoint = row.get("position", "N/A")
                break
        if next_waypoint == "N/A" and waypoint_rows:
            next_waypoint = waypoint_rows[0].get("position", "N/A")
        details = {
            "train_type": train_type_text,
            "identifier": identifier,
            "state": state_text,
            "current_position": self._format_position(current_position),
            "current_direction": self._direction_to_text(direction),
            "speed": speed_text,
            "origin": origin_text,
            "target": target_text,
            "next_waypoint": next_waypoint,
            "waypoints": waypoint_rows,
        }
        return details

    def _extract_agent_waypoints(self, agent) -> List[Dict[str, str]]:
        waypoint_groups = getattr(agent, "waypoints", None)
        if not waypoint_groups:
            return []
        earliest = list(getattr(agent, "waypoints_earliest_departure", []) or [])
        latest = list(getattr(agent, "waypoints_latest_arrival", []) or [])
        rows: List[Dict[str, str]] = []
        total = len(waypoint_groups)
        for index, group in enumerate(waypoint_groups):
            waypoint = group[0] if group else None
            position = getattr(waypoint, "position", None) if waypoint else None
            direction = getattr(waypoint, "direction", None) if waypoint else None
            role = "Waypoint"
            if index == 0:
                role = "Origin"
            elif index == total - 1:
                role = "Target"
            earliest_val = earliest[index] if index < len(earliest) else None
            latest_val = latest[index] if index < len(latest) else None
            rows.append(
                {
                    "index": index + 1,
                    "role": role,
                    "position": self._format_position(position),
                    "direction": self._direction_to_text(direction),
                    "earliest": self._format_time_window(earliest_val),
                    "latest": self._format_time_window(latest_val),
                }
            )
        return rows

    def _fallback_waypoints(self, handle: int) -> List[Dict[str, str]]:
        waypoint_pairs = self._compute_waypoints(handle)
        rows: List[Dict[str, str]] = []
        total = len(waypoint_pairs)
        for index, (position, direction) in enumerate(waypoint_pairs, start=1):
            role = "Waypoint"
            if index == 1:
                role = "Origin"
            elif index == total:
                role = "Target"
            rows.append(
                {
                    "index": index,
                    "role": role,
                    "position": self._format_position(position),
                    "direction": self._direction_to_text(direction),
                    "earliest": "N/A",
                    "latest": "N/A",
                }
            )
        return rows

    def _compute_waypoints(self, handle: int) -> List[tuple[tuple[int, int], Optional[int]]]:
        distance_map = getattr(self._env, "distance_map", None)
        if distance_map is None:
            return []
        try:
            paths = distance_map.get_shortest_paths(agent_handle=handle)
        except TypeError:
            paths = distance_map.get_shortest_paths()
        waypoints = None
        if isinstance(paths, dict):
            waypoints = paths.get(handle)
        elif isinstance(paths, list):
            waypoints = paths
        if not waypoints:
            return []
        result: List[tuple[tuple[int, int], Optional[int]]] = []
        for waypoint in waypoints:
            position = getattr(waypoint, "position", None)
            direction = getattr(waypoint, "direction", None)
            if position is None:
                continue
            result.append((position, direction))
        return result

    @staticmethod
    def _direction_to_text(direction: Optional[int]) -> str:
        mapping = {
            0: "North",
            1: "East",
            2: "South",
            3: "West",
        }
        if direction is None:
            return "N/A"
        return mapping.get(int(direction), str(direction))

    @staticmethod
    def _format_position(position: Optional[tuple[int, int]]) -> str:
        if position is None:
            return "Unknown"
        row, col = position
        return f"({row}, {col})"

    @staticmethod
    def _format_time_window(value: Optional[int]) -> str:
        if value is None:
            return "N/A"
        suffix = " step" if value == 1 else " steps"
        return f"{value}{suffix}"

    def _handle_display_click(self, event) -> None:
        pos = event.position()
        x = pos.x()
        y = pos.y()
        for handle in sorted(self._malfunctioned_handles):
            rect = self._last_highlight_rects.get(handle)
            if rect is None:
                continue
            rx, ry, rw, rh = rect
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                self._open_solution_window(handle)
                return
        for handle, rect in self._last_agent_rects.items():
            if rect is None:
                continue
            rx, ry, rw, rh = rect
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                self._open_train_info(handle)
                return

    def _open_solution_window(self, handle: int) -> None:
        window = self._solution_windows.get(handle)
        if window is not None and not sip.isdeleted(window):
            window.raise_()
            window.activateWindow()
            return
        self._solution_windows.pop(handle, None)
        window = SolutionWindow(self, handle)
        self._solution_windows[handle] = window
        self._on_solution_window_open()
        window.show()

    def _open_train_info(self, handle: int) -> Optional[TrainInfoWindow]:
        window = self._train_info_windows.get(handle)
        if window is not None and not sip.isdeleted(window):
            window.raise_()
            window.activateWindow()
            window.refresh()
            return window
        window = TrainInfoWindow(self, handle)
        self._train_info_windows[handle] = window
        window.show()
        return window

    def _on_train_info_close(self, handle: int) -> None:
        self._train_info_windows.pop(handle, None)

    def _on_solution_window_open(self) -> None:
        if self._solution_window_count == 0 and not self._episode_done:
            self._timer.stop()
        self._solution_window_count += 1
        self._is_paused = True

    def _on_solution_window_close(self, handle: int) -> None:
        self._solution_windows.pop(handle, None)
        self._solution_generation_windows.pop(handle, None)
        self._formulate_windows.pop(handle, None)
        self._analysis_windows.pop(handle, None)
        self._solution_window_count = max(0, self._solution_window_count - 1)
        if self._solution_window_count == 0:
            self._is_paused = self._manual_pause
            if not self._episode_done and not self._is_paused:
                self._timer.start()
            else:
                self._timer.stop()

    def _open_analysis_window(
        self, handle: int, parent: QWidget, context: str
    ) -> Optional[AnalysisWindow]:
        window = self._analysis_windows.get(handle)
        if window is not None and not sip.isdeleted(window):
            window.setParent(parent)
            window.set_context(context)
            window.raise_()
            window.activateWindow()
            return window
        window = AnalysisWindow(self, handle, context, parent=parent)
        self._analysis_windows[handle] = window
        window.show()
        return window

    def _on_analysis_window_close(self, handle: int) -> None:
        self._analysis_windows.pop(handle, None)

    def _open_solution_generation(self, handle: int, parent: QWidget) -> Optional["SolutionGenerationWindow"]:
        window = self._solution_generation_windows.get(handle)
        if window is not None and not sip.isdeleted(window):
            window.raise_()
            window.activateWindow()
            return window
        window = SolutionGenerationWindow(self, handle, parent=parent)
        self._solution_generation_windows[handle] = window
        window.show()
        return window

    def _on_solution_generation_close(self, handle: int) -> None:
        self._solution_generation_windows.pop(handle, None)

    def _open_formulate_solution(self, handle: int, parent: QWidget) -> Optional["FormulateSolutionWindow"]:
        window = self._formulate_windows.get(handle)
        if window is not None and not sip.isdeleted(window):
            window.raise_()
            window.activateWindow()
            return window
        window = FormulateSolutionWindow(self, handle, parent=parent)
        self._formulate_windows[handle] = window
        window.show()
        return window

    def _on_formulate_solution_close(self, handle: int) -> None:
        self._formulate_windows.pop(handle, None)

    def get_solution_suggestions(self, handle: int) -> List[str]:
        random.seed(handle)
        base_solutions = [
            "Reroute via alternate track",
            "Apply speed reduction",
            "Deploy maintenance crew",
            "Hold train and coordinate crossing",
            "Request manual override",
        ]
        return base_solutions


class StartWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simulation Setup")
        self.setMinimumSize(QSize(520, 420))
        self.viewer: Optional[FlatlandViewer] = None
        self.model_path_edit = QLineEdit()
        self.model_path_edit.setPlaceholderText("Optional agent model file")
        model_browse_btn = QPushButton("Browse...")
        model_browse_btn.clicked.connect(self._browse_model_file)
        self.scenario_path_edit = QLineEdit()
        self.scenario_path_edit.setPlaceholderText("Optional scenario JSON file")
        self.scenario_combo = QComboBox()
        self._populate_scenario_combo()
        self.scenario_combo.currentIndexChanged.connect(self._on_scenario_combo_changed)
        scenario_browse_btn = QPushButton("Browse...")
        scenario_browse_btn.clicked.connect(self._browse_scenario_file)
        self.scenario_path_edit.editingFinished.connect(
            lambda: self._sync_combo_to_path(Path(text) if (text := self.scenario_path_edit.text().strip()) else None)
        )
        self.width_spin = QSpinBox()
        self.width_spin.setRange(10, 120)
        self.width_spin.setValue(35)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(10, 120)
        self.height_spin.setValue(28)
        self.agents_spin = QSpinBox()
        self.agents_spin.setRange(1, 50)
        self.agents_spin.setValue(8)
        self.mal_rate_spin = QDoubleSpinBox()
        self.mal_rate_spin.setDecimals(3)
        self.mal_rate_spin.setSingleStep(0.01)
        self.mal_rate_spin.setRange(0.0, 1.0)
        self.mal_rate_spin.setValue(DEFAULT_MALFUNCTION_RATE)
        self.mal_min_spin = QSpinBox()
        self.mal_min_spin.setRange(1, 200)
        self.mal_min_spin.setValue(DEFAULT_MALFUNCTION_MIN)
        self.mal_max_spin = QSpinBox()
        self.mal_max_spin.setRange(1, 200)
        self.mal_max_spin.setValue(DEFAULT_MALFUNCTION_MAX)
        form_layout = QFormLayout()
        form_layout.addRow("Agent model:", self._make_file_row(self.model_path_edit, model_browse_btn))
        form_layout.addRow("Scenario file:", self._make_file_row(self.scenario_path_edit, scenario_browse_btn))
        form_layout.addRow("Available scenarios:", self.scenario_combo)
        form_layout.addRow("Width:", self.width_spin)
        form_layout.addRow("Height:", self.height_spin)
        form_layout.addRow("Agents:", self.agents_spin)
        form_layout.addRow("Malfunction rate:", self.mal_rate_spin)
        form_layout.addRow("Malfunction min duration:", self.mal_min_spin)
        form_layout.addRow("Malfunction max duration:", self.mal_max_spin)
        self.start_button = QPushButton("Start Simulation")
        self.start_button.clicked.connect(self._on_start_clicked)
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #b00;")
        central_layout = QVBoxLayout()
        central_layout.addLayout(form_layout)
        central_layout.addStretch()
        central_layout.addWidget(self.start_button, alignment=Qt.AlignmentFlag.AlignRight)
        central_layout.addWidget(self.status_label)
        central = QWidget()
        central.setLayout(central_layout)
        self.setCentralWidget(central)

    def _make_file_row(self, line_edit: QLineEdit, browse_button: QPushButton) -> QWidget:
        row_widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(line_edit)
        layout.addWidget(browse_button)
        row_widget.setLayout(layout)
        return row_widget

    def _browse_model_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select agent model", "", "Model files (*.pt *.pth *.onnx *.h5);;All files (*)")
        if path:
            self.model_path_edit.setText(path)

    def _browse_scenario_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select scenario", "", "Scenario files (*.json);;All files (*)")
        if path:
            self.scenario_path_edit.setText(path)
            self._sync_combo_to_path(Path(path))
        else:
            # ensure combo reflects manual edits
            self._sync_combo_to_path(Path(self.scenario_path_edit.text().strip()))

    def _populate_scenario_combo(self) -> None:
        self.scenario_combo.blockSignals(True)
        self.scenario_combo.clear()
        self.scenario_combo.addItem("Select a bundled scenario...", "")
        if SCENARIO_DIRECTORY.exists():
            for file in sorted(SCENARIO_DIRECTORY.glob("*.json")):
                self.scenario_combo.addItem(file.name, str(file))
        self.scenario_combo.blockSignals(False)

    def _on_scenario_combo_changed(self, index: int) -> None:
        if index < 0:
            return
        path = self.scenario_combo.itemData(index)
        if path:
            self.scenario_path_edit.setText(path)

    def _sync_combo_to_path(self, path: Optional[Path]) -> None:
        if path is None:
            self.scenario_combo.setCurrentIndex(0)
            return
        try:
            normalized = str(path.resolve())
        except Exception:
            self.scenario_combo.setCurrentIndex(0)
            return
        for idx in range(self.scenario_combo.count()):
            data = self.scenario_combo.itemData(idx)
            if data and Path(data).resolve() == Path(normalized):
                self.scenario_combo.setCurrentIndex(idx)
                return
        # if not present, leave combo at custom state

    def _on_start_clicked(self) -> None:
        model_path = self.model_path_edit.text().strip() or None
        scenario_text = self.scenario_path_edit.text().strip()
        scenario_path = scenario_text or None
        if scenario_path is None:
            data = self.scenario_combo.currentData()
            if data:
                scenario_path = str(data)
                self.scenario_path_edit.setText(scenario_path)
        self.status_label.clear()
        if scenario_path and not Path(scenario_path).exists():
            QMessageBox.critical(self, "Invalid scenario", "The selected scenario file does not exist.")
            return
        if model_path and not Path(model_path).exists():
            QMessageBox.critical(self, "Invalid model", "The selected model file does not exist.")
            return
        config = SimulationConfig(
            model_path=model_path,
            scenario_path=scenario_path,
            width=self.width_spin.value(),
            height=self.height_spin.value(),
            agents=self.agents_spin.value(),
            malfunction_rate=self.mal_rate_spin.value() or DEFAULT_MALFUNCTION_RATE,
            malfunction_min=self.mal_min_spin.value(),
            malfunction_max=self.mal_max_spin.value(),
        )
        env = self._build_environment(config)
        viewer = FlatlandViewer(env, step_interval_ms=STEP_INTERVAL_MS, model_path=config.model_path, config=config)
        viewer.show()
        self.viewer = viewer
        self.close()

    def _build_environment(self, config: SimulationConfig) -> RailEnv:
        if config.scenario_path:
            from flatland.envs.malfunction_effects_generators import MalfunctionEffectsGenerator
            env = load_scenario_from_json(config.scenario_path)
            malfunction_parameters = MalfunctionParameters(
                malfunction_rate=config.malfunction_rate,
                min_duration=config.malfunction_min,
                max_duration=config.malfunction_max,
            )
            env.malfunction_generator = ParamMalfunctionGen(malfunction_parameters)
            env.malfunction_process_data = env.malfunction_generator.get_process_data()
            env.effects_generator = MalfunctionEffectsGenerator(env.malfunction_generator)
            env.reset()
            return env
        return create_parameterized_env(
            width=config.width,
            height=config.height,
            number_of_agents=config.agents,
            malfunction_rate=config.malfunction_rate,
            malfunction_min=config.malfunction_min,
            malfunction_max=config.malfunction_max,
        )


def create_parameterized_env(
    width: int,
    height: int,
    number_of_agents: int,
    malfunction_rate: float,
    malfunction_min: int,
    malfunction_max: int,
) -> RailEnv:
    observation_builder = GlobalObsForRailEnv()
    rail_generator = sparse_rail_generator(
        max_num_cities=4,
        max_rails_between_cities=2,
        max_rail_pairs_in_city=2,
    )
    speed_ratio_map = {1.0: 1.0}
    line_generator = sparse_line_generator(speed_ratio_map)
    malfunction_parameters = MalfunctionParameters(
        malfunction_rate=malfunction_rate,
        min_duration=malfunction_min,
        max_duration=malfunction_max,
    )
    malfunction_generator = ParamMalfunctionGen(malfunction_parameters)
    env = RailEnv(
        width=width,
        height=height,
        number_of_agents=number_of_agents,
        rail_generator=rail_generator,
        line_generator=line_generator,
        malfunction_generator=malfunction_generator,
        obs_builder_object=observation_builder,
    )
    from flatland.envs.malfunction_effects_generators import MalfunctionEffectsGenerator
    env.malfunction_process_data = malfunction_generator.get_process_data()
    env.effects_generator = MalfunctionEffectsGenerator(env.malfunction_generator)
    env.reset()
    return env


def create_large_multiplayer_env() -> RailEnv:
    return create_parameterized_env(
        width=35,
        height=28,
        number_of_agents=8,
        malfunction_rate=DEFAULT_MALFUNCTION_RATE,
        malfunction_min=DEFAULT_MALFUNCTION_MIN,
        malfunction_max=DEFAULT_MALFUNCTION_MAX,
    )


def main() -> int:
    app = QApplication(sys.argv)
    start_window = StartWindow()
    start_window.show()
    return app.exec()


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
        if isinstance(parent, SolutionWindow):
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
        if isinstance(parent, SolutionWindow):
            parent.generation_window = None
        self.viewer._on_solution_generation_close(self.handle)
        super().closeEvent(event)


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
        if isinstance(parent, SolutionWindow):
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


if __name__ == "__main__":
    sys.exit(main())

