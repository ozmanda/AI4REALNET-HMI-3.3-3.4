from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit, QSizePolicy, QHBoxLayout, QFrame, QStyle, QDialog, QComboBox, QDialogButtonBox
from PyQt6.QtCore import Qt

class DisturbanceWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.Box)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.dist_layout = QVBoxLayout(self)

        # Header
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

        # Text box
        self.dist_text = QTextEdit()
        self.dist_text.setPlaceholderText("Disturbances...")
        self.dist_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.dist_layout.addWidget(self.dist_text, stretch=1)


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