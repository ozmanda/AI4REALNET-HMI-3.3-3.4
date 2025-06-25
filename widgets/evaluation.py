from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit, QSizePolicy, QHBoxLayout, QFrame, QStyle, QDialog, QComboBox, QDialogButtonBox
from PyQt6.QtCore import Qt

from flatland.envs.rail_env import RailEnv

from utils.env_reference import EnvReference


class EvaluationWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        self.setFrameShape(QFrame.Shape.Box)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.eval_layout = QVBoxLayout(self)
        self.header_layout = QHBoxLayout()

        # Evaluation Icon and label
        eval_icon = QLabel()
        eval_icon.setPixmap(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation).pixmap(24, 24))
        eval_label = QLabel('<b>Evaluation</b>')
        eval_label.setTextFormat(Qt.TextFormat.RichText)

        # Evaluation refresh
        eval_refresh_btn = QPushButton()
        eval_refresh_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        eval_refresh_btn.setFixedSize(28, 28)
        eval_refresh_btn.clicked.connect(self._on_evaluation_refresh_clicked)

        self.header_layout.addWidget(eval_icon)
        self.header_layout.addWidget(eval_label)
        self.header_layout.addStretch(1)
        self.header_layout.addWidget(eval_refresh_btn)

        self.eval_layout.addLayout(self.header_layout)

        # Text Box
        self.eval_text = QTextEdit()
        self.eval_text.setPlaceholderText("Evaluation...")
        self.eval_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.eval_layout.addWidget(self.eval_text, stretch=1)
        self.setLayout(self.eval_layout)

    def set_environment(self, env_ref: EnvReference):
        """Set the environment for the evaluation widget."""
        self.env: EnvReference = env_ref


    def _on_evaluation_refresh_clicked(self):
        """Internal callback for evaluation refresh button. Clears the current output, reevaluates based on the environment and displays the results. """
        self.clear()
        results = self.update_evaluation()
        self.display_results(results)

    
    def update_evaluation(self):
        # Update the evaluation based on new data
        results = None
        return results

    
    def display_results(self, results):
        # Display the evaluation results in the widget
        pass

    
    def clear(self):
        # Clear the widget for new evaluations
        pass


class EvalElement(QFrame):
    def __init__(self):
        pass

    def init_ui(self):
        """ UI element which displays evaluation result and opens a EvalDetail for further investigation when the user clicks on it. """



class EvalDetail(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Evaluation Details")
        self.setMinimumWidth(300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)

        # Evaluation details text area
        self.details_text = QTextEdit()
        self.details_text.setPlaceholderText("Detailed evaluation results...")
        self.details_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.details_text, stretch=1)

        # Button box for closing the dialog
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)