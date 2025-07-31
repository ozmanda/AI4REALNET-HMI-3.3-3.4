import os
import sys
import numpy as np
from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout, QSizePolicy, QPushButton, QHBoxLayout
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import Qt
from flatland.utils.rendertools import RenderTool
from src.utils.env_reference import FlatlandEnvReference
from src.utils.flatland_railway_extension.RailroadSwitchCluster import RailroadSwitchCluster
from src.utils.flatland_railway_extension.RailroadSwitchAnalyser import RailroadSwitchAnalyser
from matplotlib import pyplot as plt
from PIL import Image

class FlatlandWidget(QWidget):
    def __init__(self, env_ref: FlatlandEnvReference, parent=None):
        super().__init__(parent)
        self.env_ref: FlatlandEnvReference = env_ref
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(self.label)

        # Add button for track / switch selection and track/switch view
        self.env_view_buttons()
        self.click_registration_enabled = False
        layout.addWidget(self.view_buttons_widget)
        self.setLayout(layout)

        # Store the last rendered image
        self._last_render = {'env': None, 'track': None, 'switch': None}
        self.render_type = 'env'

        # render the initial environment
        self.update_from_env()

    def update_from_env(self):
        """ Render the current environment and store the image."""
        self.railroad_cluster: RailroadSwitchCluster = RailroadSwitchCluster(RailroadSwitchAnalyser(self.env_ref.env))
        track_image, switch_image = self.railroad_cluster.do_debug_plot()
        self.renderer = RenderTool(self.env_ref.env, gl="PILSVG", screen_height=600, screen_width=1800)
        self.renderer.render_env(show=False, show_observations=False)
        img = self.renderer.get_image()
        # Save the rendered image to "flatland_env.png"
        Image.fromarray(img).save(os.path.join(os.getcwd(), 'src', 'imgs', 'flatland_env.png'))
        self._last_render['env'] = img
        self._last_render['track'] = track_image
        self._last_render['switch'] = switch_image
        self._render_to_label()


    def resizeEvent(self, event):
        """Handle resize and scale the last render."""
        super().resizeEvent(event)
        self._render_to_label()


    def _render_to_label(self):
        """Render stored image to QLabel scaled to widget size, using RGB format and no channel swap."""
        if self._last_render[self.render_type] is None:
            return
        img = self._last_render[self.render_type]

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
            self.label.width(), self.label.height(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        ))


    def visualise_disturbance(self, disturbance_info: dict):
        """Visualise a disturbance in the environment."""
        # TODO: implement highlighting / visualisation of disturbances
        print(f"Flatlandwidget received disturbance info: {disturbance_info.get('type', 'Unknown')}")

    def toggle_infrastructure_selection(self):
        """ Toggle infrastructure selection mode."""
        if self.infrastructure_selection_button.isChecked():
            if self.render_type != 'env':
                self.render_type = 'env'
                self._render_to_label()
            self.train_selection_button.setChecked(False)
            self.track_view_button.setChecked(False)
            self.switch_view_button.setChecked(False)
        self.click_registration_enabled = self.infrastructure_selection_button.isChecked()
        self.update_button_styles()
        print(f"Click registration {'enabled' if self.click_registration_enabled else 'disabled'}")

    
    def toggle_train_selection(self):
        """ Toggle train selection mode."""
        if self.train_selection_button.isChecked():
            self.infrastructure_selection_button.setChecked(False)
            self.track_view_button.setChecked(False)
            self.switch_view_button.setChecked(False)   
        self.click_registration_enabled = self.train_selection_button.isChecked()
        self.update_button_styles()         
        print("Train selection mode toggled (not implemented yet)")


    def toggle_trackID_view(self):
        """ Toggle track ID view mode."""
        if self.track_view_button.isChecked():
            self.infrastructure_selection_button.setChecked(False)
            self.train_selection_button.setChecked(False)
            self.switch_view_button.setChecked(False)
            if self.render_type != 'track':
                self.render_type = 'track'
                self._render_to_label()
        else:
            if self.render_type != 'env':
                self.render_type = 'env'
                self._render_to_label()
        self.click_registration_enabled = self.track_view_button.isChecked()
        self.update_button_styles()
        print("Track ID view mode toggled (not implemented yet)")


    def toggle_switchID_view(self):
        """ Toggle switch ID view mode."""
        if self.switch_view_button.isChecked():
            self.infrastructure_selection_button.setChecked(False)
            self.train_selection_button.setChecked(False)
            self.track_view_button.setChecked(False)
            if self.render_type != 'switch':
                self.render_type = 'switch'
                self._render_to_label()
        else:
            if self.render_type != 'env':
                self.render_type = 'env'
                self._render_to_label()
        self.click_registration_enabled = self.switch_view_button.isChecked()
        self.update_button_styles()
        print("Switch ID view mode toggled (not implemented yet)")


    def mousePressEvent(self, event):
        """Handle mouse click events to register clicks."""
        if self.click_registration_enabled:
            click_x = event.position().x()
            click_y = event.position().y()

            # Get the actual dimensions of the image displayed within the QLabel
            pixmap = self.label.pixmap()
            if pixmap is None:
                print("No image loaded in QLabel.")
                return

            pixmap_width = pixmap.width()
            pixmap_height = pixmap.height()

            # Calculate the top-left corner of the image within the QLabel
            label_width = self.label.width()
            label_height = self.label.height()

            image_x_offset = (label_width - pixmap_width) // 2 if label_width > pixmap_width else 0
            image_y_offset = (label_height - pixmap_height) // 2 if label_height > pixmap_height else 0

            # Adjust click coordinates to account for the image's position within the QLabel
            adjusted_x = click_x - image_x_offset
            adjusted_y = click_y - image_y_offset

            # Ensure the click is within the image bounds
            if not (0 <= adjusted_x < pixmap_width and 0 <= adjusted_y < pixmap_height):
                print("Click outside the image bounds.")
                return

            # Map adjusted coordinates to grid position
            grid_width = self.env_ref.env.width
            grid_height = self.env_ref.env.height

            grid_x = int(adjusted_x / pixmap_width * grid_width)
            grid_y = int(adjusted_y / pixmap_height * grid_height)

            print(f"Click registered at grid position: ({grid_x}, {grid_y})")
    

    def env_view_buttons(self):
        """Create buttons for environment view actions."""
        # Wrap view_buttons in a QWidget
        self.view_buttons_widget = QWidget()
        self.view_buttons: QHBoxLayout = QHBoxLayout()
        self.infrastructure_selection_button = QPushButton("Select Track/Switch")
        self.infrastructure_selection_button.setCheckable(True)
        self.infrastructure_selection_button.clicked.connect(self.toggle_infrastructure_selection)
        self.infrastructure_selection_button.setStyleSheet("color: black;")

        self.train_selection_button = QPushButton("Select Train")
        self.train_selection_button.setCheckable(True)
        self.train_selection_button.clicked.connect(self.toggle_train_selection)
        self.train_selection_button.setStyleSheet("color: black;")

        self.track_view_button = QPushButton("Track ID View")
        self.track_view_button.setCheckable(True)
        self.track_view_button.clicked.connect(self.toggle_trackID_view)
        self.track_view_button.setStyleSheet("color: black;")

        self.switch_view_button = QPushButton("Switch ID View")
        self.switch_view_button.setCheckable(True)
        self.switch_view_button.clicked.connect(self.toggle_switchID_view)
        self.switch_view_button.setStyleSheet("color: black;")

        self.view_buttons.addWidget(self.infrastructure_selection_button)
        self.view_buttons.addWidget(self.train_selection_button)
        self.view_buttons.addWidget(self.track_view_button)
        self.view_buttons.addWidget(self.switch_view_button)

        self.view_buttons_widget.setLayout(self.view_buttons)

        # Update button styles based on initial checked state

    def update_button_styles(self):
        """Update the styles of the buttons based on their checked state."""
        for button in [self.infrastructure_selection_button, self.train_selection_button, self.track_view_button, self.switch_view_button]:
            if button.isChecked():
                button.setStyleSheet("color: black; background-color: lightgray;")
            else:
                button.setStyleSheet("color: black;")
