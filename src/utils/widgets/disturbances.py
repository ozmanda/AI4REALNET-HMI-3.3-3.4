from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit, QSizePolicy, QHBoxLayout, QFrame, QStyle, QDialog, QComboBox, QDialogButtonBox
from PyQt6.QtCore import Qt, pyqtSignal

class DisturbanceWidget(QFrame):
    disturbance_selected = pyqtSignal(dict)  # Emits the disturbance type when clicked
    solution_generation = pyqtSignal(str)  # Emits the disturbance ID when a solution generation is requested
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.Box)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.dist_layout = QVBoxLayout(self)

        # Header
        self._init_header()

        # Disturbance area 
        self.disturbance_area = QVBoxLayout()
        self.dist_layout.addLayout(self.disturbance_area)

        # Placeholder text box
        self.dist_text = QTextEdit()
        self.dist_text.setPlaceholderText("Disturbances log...")
        self.dist_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.dist_layout.addWidget(self.dist_text, stretch=1)

    def _init_header(self):
        self.header_layout = QHBoxLayout()
        self.dist_icon = QLabel()
        self.dist_icon.setPixmap(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical).pixmap(24, 24))

        self.dist_label = QLabel("<b>Disturbances</b>")
        self.dist_label.setTextFormat(Qt.TextFormat.RichText)

        self.dist_note_btn = QPushButton()
        self.dist_note_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self.dist_note_btn.setFixedSize(28, 28)
        self.dist_note_btn.clicked.connect(self._on_emergency_clicked) # Connect to emergency scenario chooser

        self.header_layout.addWidget(self.dist_icon)
        self.header_layout.addWidget(self.dist_label)
        self.header_layout.addStretch(1)
        self.header_layout.addWidget(self.dist_note_btn)

        self.dist_layout.addLayout(self.header_layout)


    def _on_emergency_clicked(self):
        """Internal callback for emergency button."""
        # TODO: implement emergency scenario selection
        chooser = EmergencyPlanChooser(self)
        result = chooser.exec()

        if result == QDialog.DialogCode.Accepted:
            selected_plan = chooser.get_selected_plan()
            current_text = self.dist_text.toPlainText()
            current_text = f'{current_text}\n' if not current_text.endswith('\n') else current_text
            if selected_plan:
                self.dist_text.append(f"Emergency Plan Selected: {selected_plan}\n")
            else:
                self.dist_text.append("No Emergency Plan Selected\n") 


    def add_disturbance(self, disturbance_info: dict):
        """Add a disturbance to the widget."""
        disturbance_object = DisturbanceObject(disturbance_info, self)
        disturbance_object.disturbance_selected.connect(self._on_disturbance_clicked)
        self.dist_layout.addWidget(disturbance_object)

    def _on_disturbance_clicked(self, disturbance_info: dict):
        self.disturbance_selected.emit(disturbance_info)
        dialog = DisturbanceDetailDialog(disturbance_info)
        dialog.solution_generated.connect(self._handle_solution_generation)
        dialog.exec()

    def _handle_solution_generation(self, disturbance_ID: str):
        self.dist_text.append(f"Generating solution for disturbance ID: {disturbance_ID}...\n")
        self.solution_generation.emit(disturbance_ID)


class DisturbanceObject(QWidget):
    """ Object to visualise and interact with disturbances in the environment. """
    disturbance_selected = pyqtSignal(dict)  # Emits the disturbance type when clicked
    def __init__(self, disturbance_info: dict, parent=None):
        super().__init__(parent)
        self.disturbance_info = disturbance_info
        self.disturbance_type = disturbance_info.get("type", "Unknown")
        self.description = disturbance_info.get("description", "No description provided")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        # self.setStyleSheet("background-color: #eee; border: 1px solid #aaa;")

        self.icon_label = QLabel()
        self.icon_label.setPixmap(self._get_icon(self.disturbance_type).pixmap(24, 24))

        self.text_label = QLabel(f"<b>{self.disturbance_type}</b>")
        self.text_label.setTextFormat(Qt.TextFormat.RichText)

        self.desc_label = QLabel(self.description)
        self.desc_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.desc_label.setStyleSheet("padding: 2px 4px;")

        self.info_btn = QPushButton()
        self.info_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogHelpButton))
        self.info_btn.setFixedSize(24, 24)
        self.info_btn.clicked.connect(self._on_clicked)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)
        layout.addWidget(self.desc_label)
        layout.addStretch(1)
        layout.addWidget(self.info_btn)

    def _on_clicked(self):
        # Emit signal when clicked
        self.disturbance_selected.emit(self.disturbance_info)

    def _get_icon(self, disturbance_type):
        if "Train" in disturbance_type:
            return self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp)
        elif "Maintenance" in disturbance_type:
            return self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning)
        elif "Signal" in disturbance_type:
            return self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserStop)
        return self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
    

class DisturbanceDetailDialog(QDialog):
    # Signals 
    solution_generated = pyqtSignal(str)  
    def __init__(self, disturbance_info: dict, parent=None):
        super().__init__(parent)
        self.disturbance_ID = disturbance_info.get('ID', '0000')
        self.setWindowTitle(f"<b>{self.disturbance_ID}</b> {disturbance_info.get('type', 'Unknown Type')} Details")
        self.setMinimumWidth(300)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"<b>Details for:</b> {disturbance_info.get('ID', '0000')}"))

        self.solution_btn = QPushButton("Generate Solution")
        self.solution_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowRight))
        self.solution_btn.clicked.connect(self._on_solution)

        layout.addWidget(self.solution_btn)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        layout.addWidget(self.close_btn)

    def _on_solution(self):
        # Placeholder logic
        self.solution_generated.emit(str(self.disturbance_ID))
        self.close()


class EmergencyPlanChooser(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choose Emergency Plan")
        self.setMinimumWidth(300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.selected_plan = None

        layout = QVBoxLayout(self)

        self.label = QLabel("Emergency Plan Selection")
        layout.addWidget(self.label)

        self.combo = QComboBox()
        self.combo.addItems(["Plan A", "Plan B", "Plan C"]) # TODO: flexible plan loading from config / scenario
        layout.addWidget(self.combo)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.setLayout(layout)


    def get_selected_plan(self):
        """Get the selected emergency plan."""
        return self.combo.currentText() if self.combo.currentText() else None