import sys
import numpy as np
from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QPushButton, QSizePolicy
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import Qt
from PIL import Image
from flatland.utils.rendertools import RenderTool
from flatland.envs.rail_env import RailEnv
from utils.env_reference import EnvReference

class FlatlandWidget(QWidget):
    def __init__(self, env_ref: EnvReference, parent=None):
        super().__init__(parent)
        self.env_ref: EnvReference = env_ref
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

        # Store the last rendered image
        self._last_render = None

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