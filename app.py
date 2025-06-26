import sys
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QSlider, QFrame, QSizePolicy, QStyle
)
from widgets.flatland_widget import FlatlandWidget
from widgets.action_token_selector import ActionTokenSelector
from widgets.disturbances import DisturbanceWidget
from widgets.evaluation import EvaluationWidget

from utils.env_reference import EnvReference

from flatland.envs.rail_env import RailEnv 
from utils.env_small import small_flatland_env 
from test_data.test_disturbances import small_test_disturbances


# HMI Main Window
class MainWindow(QMainWindow):
    def __init__(self, env: RailEnv):
        super().__init__()
        self.setWindowTitle("AI4REALNET Co-Learning HMI")
        self.setMinimumSize(1000, 600)
        self.env_ref: EnvReference = EnvReference()
        self.env_ref.env = env
        self.init_ui()

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

        # Token area with lightbulb and delete button
        # TODO: Nest action token selector inside of a frame
        tokens_frame = QFrame()
        tokens_frame.setFrameShape(QFrame.Shape.Box)
        tokens_layout = QHBoxLayout(tokens_frame)
        bulb_btn = QPushButton()
        bulb_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        bulb_btn.setFixedSize(32, 32)
        bulb_btn.clicked.connect(self.on_bulb_clicked) # TODO: move with token widget class, rename & connect to environment.
        self.token_selector = ActionTokenSelector(env.get_agent_handles())
        delete_btn = QPushButton()
        delete_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        delete_btn.setFixedSize(32, 32)
        delete_btn.clicked.connect(self.on_delete_clicked)
        tokens_layout.addWidget(bulb_btn)
        tokens_layout.addWidget(self.token_selector, stretch=1)
        tokens_layout.addWidget(delete_btn)
        tokens_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        tokens_frame.setMinimumWidth(256) 

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
        disturbances = small_test_disturbances()  # Load test disturbances
        for disturbance in disturbances:
            print(disturbance)
            self.disturbances_widget.add_disturbance(disturbance)

        # Evaluation
        self.evaluation_widget = EvaluationWidget()
        
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

    def on_delete_clicked(self): # TODO: move into token class with other functions
        self.token_selector.clear_tokens()
        print("Delete button clicked")


if __name__ == "__main__":
    # Initialize Flatland environment
    env = small_flatland_env()
    app = QApplication(sys.argv)
    window = MainWindow(env)
    window.show()
    sys.exit(app.exec())