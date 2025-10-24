from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from flatland.envs.malfunction_generators import MalfunctionParameters, ParamMalfunctionGen
from flatland.envs.rail_env import RailEnv
from flatland.envs.rail_generators import sparse_rail_generator
from flatland.envs.line_generators import sparse_line_generator
from flatland.envs.observations import GlobalObsForRailEnv

from src.config.simulation import (
    DEFAULT_MALFUNCTION_MAX,
    DEFAULT_MALFUNCTION_MIN,
    DEFAULT_MALFUNCTION_RATE,
    SCENARIO_DIRECTORY,
    STEP_INTERVAL_MS,
    SimulationConfig,
)
from src.ui.flatland_viewer import FlatlandViewer
from src.utils.environments.scenario_loader import load_scenario_from_json

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
