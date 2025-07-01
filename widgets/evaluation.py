from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit, QSizePolicy, QHBoxLayout, QFrame, QStyle, QDialog, QComboBox, QDialogButtonBox, QScrollArea, QGroupBox
from PyQt6.QtCore import Qt, pyqtSignal

from flatland.envs.rail_env import RailEnv

from utils.env_reference import EnvReference


class EvaluationWidget(QFrame):
    # Signals 
    request_evaluation = pyqtSignal()  # Signal to request evaluation refresh
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        self.setFrameShape(QFrame.Shape.Box)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Main layout
        self.eval_layout = QVBoxLayout(self)
        self.header_layout = QHBoxLayout()

        # Evaluation Icon and label
        eval_icon = QLabel()
        eval_icon.setPixmap(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation).pixmap(24, 24))
        eval_label = QLabel('<b>Evaluation</b>')
        eval_label.setTextFormat(Qt.TextFormat.RichText)

        # Evaluation clear button
        eval_clear_btn = QPushButton()
        eval_clear_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        eval_clear_btn.setFixedSize(28, 28)
        eval_clear_btn.clicked.connect(self.clear_solutions)  

        # Evaluation refresh
        eval_refresh_btn = QPushButton()
        eval_refresh_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        eval_refresh_btn.setFixedSize(28, 28)
        eval_refresh_btn.clicked.connect(self._on_evaluation_refresh_clicked)

        self.header_layout.addWidget(eval_icon)
        self.header_layout.addWidget(eval_label)
        self.header_layout.addStretch(1)
        self.header_layout.addWidget(eval_clear_btn)
        self.header_layout.addWidget(eval_refresh_btn)

        self.eval_layout.addLayout(self.header_layout)

        # Evaluation metrics box
        self.metrics_box = QGroupBox("Metrics")
        self.metrics_box.setVisible(False)  # Hidden by default
        self.metrics_layout = QVBoxLayout(self.metrics_box)
        self.eval_layout.addWidget(self.metrics_box)

        # Scrollable area for Solution widgets
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_content.setLayout(self.scroll_layout)

        self.scroll_area.setWidget(self.scroll_content)
        self.eval_layout.addWidget(self.scroll_area)

        self.setLayout(self.eval_layout)


    def display_results(self, evaluation: dict):
        """Display the evaluation metrics in the metrics box."""
        self.metrics_box.setVisible(True)
        # Clear existing metrics
        while self.metrics_layout.count():
            child = self.metrics_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Add new metrics
        for key, value in evaluation.items():
            metric_label = QLabel(f"<b>{key}:</b> {value}")
            metric_label.setTextFormat(Qt.TextFormat.RichText)
            self.metrics_layout.addWidget(metric_label)

    def add_solution(self, solution_details: dict):
        """Add a Solution widget to the scrollable area."""
        solution_widget = Solution(solution_details, parent=self)
        self.scroll_layout.addWidget(solution_widget)

    def clear_solutions(self):
        """Clear all Solution widgets from the scrollable area."""
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def set_environment(self, env_ref: EnvReference):
        """Set the environment for the evaluation widget."""
        self.env: EnvReference = env_ref


    def _on_evaluation_refresh_clicked(self):
        """Internal callback for evaluation refresh button. Clears the current output, reevaluates based on the environment and displays the results. """
        self.request_evaluation.emit()  # Emit signal to request evaluation refresh

    
    def update_evaluation(self):
        # Update the evaluation based on new data
        results = []  # Replace with actual logic to generate results
        return results

    
    def clear(self):
        # Clear the widget for new evaluations
        pass


class EvalElement(QFrame):
    def __init__(self):
        pass

    def init_ui(self):
        """ UI element which displays evaluation result and opens a EvalDetail for further investigation when the user clicks on it. """


class Solution(QFrame):
    # Signal to emit acceptance or rejection
    solution_accepted = pyqtSignal(bool)

    def __init__(self, solution_details: dict, parent=None):
        super().__init__(parent)

        self.solution_details = solution_details

        # Layout: box with description, opens dialog box with details when clicked
        self.setFrameShape(QFrame.Shape.Box)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)

        # Display the description
        description_label = QLabel(f"<b>{solution_details.get('Description', 'No Description')}</b>")
        description_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(description_label)

        # Connect click event to open dialog
        self.mousePressEvent = self.open_details_dialog

    def open_details_dialog(self, event=None):
        """Open a dialog box displaying the full solution details."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Solution Details")
        dialog.setMinimumWidth(400)

        dialog_layout = QVBoxLayout(dialog)

        # Add details to the dialog
        for key, value in self.solution_details.items():
            detail_label = QLabel(f"<b>{key}:</b> {value}")
            detail_label.setTextFormat(Qt.TextFormat.RichText)
            dialog_layout.addWidget(detail_label)

        # Buttons for Accept, Reject, and Adjust
        button_layout = QHBoxLayout()

        accept_button = QPushButton("Accept")
        accept_button.clicked.connect(lambda: (self.solution_accepted.emit(True), dialog.accept()))
        button_layout.addWidget(accept_button)

        reject_button = QPushButton("Reject")
        reject_button.clicked.connect(lambda: (self.solution_accepted.emit(False), dialog.accept()))
        button_layout.addWidget(reject_button)

        adjust_button = QPushButton("Adjust")
        adjust_button.clicked.connect(self._open_adjust_dialog)
        button_layout.addWidget(adjust_button)

        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        button_layout.addWidget(close_button)

        dialog_layout.addLayout(button_layout)

        dialog.exec()

    def _open_adjust_dialog(self):
        """Open a dialog for adjusting the solution."""
        adjust_dialog = EvalDetail(self)
        adjust_dialog.details_text.setText("Adjust the solution details here...")
        adjust_dialog.exec()


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