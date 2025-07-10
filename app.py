import sys
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QSlider, QFrame, QSizePolicy, QStyle
)
from widgets import evaluation
from widgets.flatland_widget import FlatlandWidget
from widgets.action_token_selector import ActionTokenSelector
from widgets.disturbances import DisturbanceWidget
from widgets.evaluation import EvaluationWidget
from widgets.human_input import HumanInputWidget

from utils.env_reference import FlatlandEnvReference

from flatland.envs.rail_env import RailEnv 
from utils.env_small import small_flatland_env 
from test_data.test_disturbances import small_test_disturbances
from utils.controller_reference import ControllerRef


# HMI Main Window
class MainWindow(QMainWindow):
    def __init__(self, env: RailEnv, agent: ControllerRef):
        super().__init__()
        self.setWindowTitle("AI4REALNET Co-Learning HMI")
        self.setMinimumSize(1000, 600)
        self.env_ref: FlatlandEnvReference = FlatlandEnvReference()
        self.env_ref.env = env
        self.init_ui()
        self.agent_ref = agent

    def init_ui(self):
        # Top label: Sector Name, Time, etc.
        sector_label = QLabel('<b><span style="color:red">Sector</span> Name, Time, etc.</b>')
        sector_label.setTextFormat(Qt.TextFormat.RichText)
        sector_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Map/Video area replaced with FlatlandWidget
        self.env_ref.env.reset() # TODO: move this to environment handling
        
        self.flatland_widget = FlatlandWidget(self.env_ref)
        self.flatland_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        map_frame = QFrame()
        map_frame.setFrameShape(QFrame.Shape.Box)
        map_frame.setStyleSheet("background: #f8f8f8;")
        map_layout = QVBoxLayout(map_frame)
        map_layout.setContentsMargins(0, 0, 0, 0)
        map_layout.addWidget(self.flatland_widget, stretch=1)
        map_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Play button and slider in a horizontal layout
        # TODO: move button and slider to class with environment access
        play_btn = QPushButton()
        play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        play_btn.setIconSize(QSize(48, 48))
        play_btn.setFixedSize(60, 60)
        play_btn.setStyleSheet("border-radius:30px;background:rgba(0,0,0,0.3);")
        play_btn.clicked.connect(self.on_play_clicked)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(0)
        slider.setMaximum(100)
        slider.valueChanged.connect(self.on_slider_changed)
        slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        play_slider_layout = QHBoxLayout()
        play_slider_layout.addWidget(play_btn)
        play_slider_layout.addWidget(slider)

        # Human input widget for action tokens
        tokens_frame = HumanInputWidget(self.env_ref)
        tokens_frame.tokens_signal.connect(self.handle_received_tokens)  # Connect signal to handle received tokens

        # Left main layout (map, slider, tokens)
        left_layout = QVBoxLayout()
        left_layout.addWidget(sector_label)
        left_layout.addWidget(map_frame, stretch=10)
        left_layout.addLayout(play_slider_layout, stretch=0)
        left_layout.addWidget(tokens_frame, stretch=2)  

        # Right panel: Disturbances and Evaluation
        right_panel = QVBoxLayout()
        
        # Disturbances
        self.disturbances_widget = DisturbanceWidget()
        self.disturbances_widget.disturbance_selected.connect(self.flatland_widget.visualise_disturbance)  # Connect disturbance selection to FlatlandWidget for visualisation
        self.disturbances_widget.solution_generation.connect(self.handle_solution_generation_request)
        disturbances = small_test_disturbances()  # Load test disturbances
        for disturbance in disturbances:
            self.disturbances_widget.add_disturbance(disturbance)

        # Evaluation
        self.evaluation_widget = EvaluationWidget()
        self.evaluation_widget.request_evaluation.connect(self.handle_evaluation_request)  # Connect evaluation request signal
        
        # Add to right panel
        right_panel.addWidget(self.disturbances_widget, stretch=1)
        right_panel.addWidget(self.evaluation_widget, stretch=1)
        right_panel.minimumSize = QSize(512, 0)  # Minimum width for the right panel

        # Main layout
        main_layout = QHBoxLayout()
        main_layout.addLayout(left_layout, 3)
        main_layout.addLayout(right_panel, 1)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    # Button slots (to be filled in)
    def on_play_clicked(self): # TODO: move to class with slider and FlatlandWidget
        print("Play button clicked")


    def on_slider_changed(self, value): # TODO: move to class with slider and FlatlandWidget
        print(f"Slider changed: {value}")


    def on_bulb_clicked(self):
        print("Bulb button clicked")


    def handle_received_tokens(self, tokens: dict):
        """Handle received action tokens from the HumanInputWidget."""
        print(f"Received tokens: {tokens}")


    def handle_evaluation_request(self):
        """Handle evaluation request from the user."""
        evaluation_results: dict = {
            'Environment': self.env_ref.get_environment_info(),
            'Metrics': self.env_ref.get_metrics()
            }
        self.evaluation_widget.display_results(evaluation_results)


    def handle_solution_generation_request(self, disturbance_ID: str):
        """Handle solution generation request for a disturbance."""
        # add solution generation logic here
        solution_details = {
            'Description': f"Solution for disturbance: {disturbance_ID}",
            'Details': "Further details about the solution can be added here.",
            'Actions': ["Action 1", "Action 2", "Action 3"]
            } 
        self.evaluation_widget.add_solution(solution_details)

if __name__ == "__main__":
    # Initialize Flatland environment
    env = small_flatland_env()
    app = QApplication(sys.argv)
    window = MainWindow(env)
    window.show()
    sys.exit(app.exec())