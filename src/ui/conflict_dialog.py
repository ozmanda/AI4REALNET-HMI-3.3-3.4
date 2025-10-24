from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Any
from src.ui.flatland_viewer import FlatlandViewer

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

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
