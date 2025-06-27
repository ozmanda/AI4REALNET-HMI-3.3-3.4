import sys
import numpy as np
from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout, QSizePolicy, QPushButton
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import Qt
from flatland.utils.rendertools import RenderTool
from utils.env_reference import EnvReference

class FlatlandWidget(QWidget):
    def __init__(self, env_ref: EnvReference, parent=None):
        super().__init__(parent)
        self.env_ref: EnvReference = env_ref
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(self.label)

        # Add button for enabling click registration
        self.register_button = QPushButton("Enable Click Registration")
        self.register_button.setStyleSheet("color: black;")
        self.register_button.setCheckable(True)
        self.register_button.clicked.connect(self.toggle_click_registration)
        layout.addWidget(self.register_button)

        self.setLayout(layout)

        # Store the last rendered image
        self._last_render = None

        # Flag for click registration mode
        self.click_registration_enabled = False

        # render the initial environment
        self.update_from_env()

    def update_from_env(self):
        """ Render the current environment and store the image."""
        self.renderer = RenderTool(self.env_ref.env, gl="PILSVG", screen_height=600, screen_width=1800)
        self.renderer.render_env(show=False, show_observations=False)
        img = self.renderer.get_image()
        self._last_render = img
        self._render_to_label()


    def resizeEvent(self, event):
        """Handle resize and scale the last render."""
        super().resizeEvent(event)
        self._render_to_label()


    def _render_to_label(self):
        """Render stored image to QLabel scaled to widget size, using RGB format and no channel swap."""
        if self._last_render is None:
            return
        img = self._last_render

        # Ensure image is uint8 and contiguous
        if img.dtype != np.uint8:
            img = img.astype(np.uint8)
        img = np.ascontiguousarray(img)

        # check channel format
        h, w, ch = img.shape
        if ch == 4:
            fmt = QImage.Format.Format_RGBA8888
        elif ch == 3:
            fmt = QImage.Format.Format_RGB888
        else:
            raise ValueError(f"Unexpected number of channels: {ch}")
        
        bytes_per_line = ch * w
        qimg = QImage(img.tobytes(), w, h, bytes_per_line, fmt)
        pixmap = QPixmap.fromImage(qimg)
        self.label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.label.setPixmap(pixmap.scaled(
            self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        ))


    def visualise_disturbance(self, disturbance_info: dict):
        """Visualise a disturbance in the environment."""
        # TODO: implement highlighting / visualisation of disturbances
        print(f"Flatlandwidget received disturbance info: {disturbance_info.get('type', 'Unknown')}")

    def toggle_click_registration(self):
        """Toggle click registration mode."""
        self.click_registration_enabled = self.register_button.isChecked()
        print(f"Click registration {'enabled' if self.click_registration_enabled else 'disabled'}")

    def mousePressEvent(self, event):
        """Handle mouse click events to register clicks."""
        if self.click_registration_enabled:
            click_x = event.position().x()
            click_y = event.position().y()

            # Map click position to grid position
            grid_width = self.env_ref.env.width
            grid_height = self.env_ref.env.height
            widget_width = self.width()
            widget_height = self.height()

            grid_x = int(click_x / widget_width * grid_width)
            grid_y = int(click_y / widget_height * grid_height)

            print(f"Click registered at grid position: ({grid_x}, {grid_y})")
