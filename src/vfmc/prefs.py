import json
import logging
import os
import sys
from dataclasses import dataclass, field, asdict
from functools import cached_property
from pathlib import Path
from typing import List, Tuple

from PyQt5.QtWidgets import (
    QDialog,
    QWidget,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QCheckBox,
    QDialogButtonBox,
    QSlider,
)
from PyQt5.QtCore import Qt

# Factory-default cube face colors
_DEFAULT_COLORS = [
    (255, 255, 255),
    (255, 255, 0),
    (0, 153, 0),
    (0, 0, 255),
    (255, 0, 0),
    (255, 94, 51),  # (255, 204, 25),
]


class RecognitionOptionNames:
    BAD_FACES = "bad faces"
    BAD_PIECES = "bad pieces"
    TOP_COLOR = "top color"
    BOTTOM_COLOR = "bottom color"
    ALL = "all"


@dataclass
class RecognitionOptions:
    """Preference setting for drawing the cube while solving different steps"""

    eo_edges: List[str]
    eo_corners: List[str]
    dr_edges: List[str]
    dr_corners: List[str]
    htr_edges: List[str]
    htr_corners: List[str]
    fr_edges: List[str]
    fr_corners: List[str]

    @staticmethod
    def default() -> "RecognitionOptions":
        return RecognitionOptions(
            eo_edges=[RecognitionOptionNames.BAD_PIECES],
            eo_corners=[],
            dr_edges=[
                RecognitionOptionNames.BAD_FACES,
            ],
            dr_corners=[RecognitionOptionNames.BAD_FACES],
            htr_edges=[RecognitionOptionNames.BAD_FACES],
            htr_corners=[
                RecognitionOptionNames.BAD_FACES,
                RecognitionOptionNames.BOTTOM_COLOR,
            ],
            fr_edges=[RecognitionOptionNames.BAD_FACES],
            fr_corners=[RecognitionOptionNames.BAD_FACES],
        )

    @staticmethod
    def minimal() -> "RecognitionOptions":
        return RecognitionOptions(
            eo_edges=[RecognitionOptionNames.BAD_PIECES],
            eo_corners=[],
            dr_edges=[RecognitionOptionNames.BAD_FACES],
            dr_corners=[RecognitionOptionNames.BAD_FACES],
            htr_edges=[RecognitionOptionNames.BAD_FACES],
            htr_corners=[RecognitionOptionNames.BAD_FACES],
            fr_edges=[RecognitionOptionNames.BAD_FACES],
            fr_corners=[RecognitionOptionNames.BAD_FACES],
        )


@dataclass
class Preferences:
    """Top-level preferences object"""

    opacity: int = 237
    background_color: int = 77
    colors: List[Tuple] = field(default_factory=lambda: _DEFAULT_COLORS)
    recognition: RecognitionOptions = field(default_factory=RecognitionOptions.default)
    listeners: List = field(default_factory=list)

    def save(self):
        prefs_path = Preferences.get_preferences_path()
        prefs_path.parent.mkdir(parents=True, exist_ok=True)

        prefs = {
            "opacity": self.opacity,
            "recognition": asdict(self.recognition),
            "colors": self.colors,
            "background": self.background_color,
        }

        try:
            with open(prefs_path, "w") as f:
                json.dump(prefs, f)
        except Exception as e:
            logging.error(f"Error saving preferences: {e}")

    def add_listener(self, callback):
        self.listeners.append(callback)

    def notify(self):
        for listener in self.listeners:
            listener()

    @staticmethod
    def load() -> "Preferences":
        # Get the preferences file path
        prefs_path = Preferences.get_preferences_path()

        if prefs_path.exists():
            try:
                with open(prefs_path, "r") as f:
                    prefs = json.load(f)
                    recognition = asdict(RecognitionOptions.default())
                    recognition.update(prefs.get("recognition", {}))
                    opacity = prefs.get("opacity", 237)
                    colors = prefs.get("colors", [])
                    if len(colors) != len(_DEFAULT_COLORS):
                        colors = _DEFAULT_COLORS
                    bg = prefs.get("background", 77)
                    return Preferences(
                        opacity=opacity,
                        colors=colors,
                        recognition=RecognitionOptions(**recognition),
                        background_color=bg,
                    )
            except Exception as e:
                logging.error(f"Error loading preferences: {e}")
                return Preferences()
        else:
            return Preferences()

    @staticmethod
    def get_preferences_path() -> Path:
        return app_dir() / "preferences.json"


class PreferencesDialog(QDialog):
    """Dialog for modifying preferences"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setWindowModality(Qt.NonModal)
        self.setMinimumWidth(300)

        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(self.colors_widget)
        layout.addWidget(self.eo_widget)
        layout.addWidget(self.dr_widget)
        layout.addWidget(self.htr_widget)
        layout.addWidget(self.fr_widget)

        def close():
            preferences.save()
            self.hide()

        button_box = QDialogButtonBox(QDialogButtonBox.Save)
        button_box.accepted.connect(close)
        layout.addWidget(button_box)

    def piece_options(
        self, name: str, target_list: List[str], options: List[str], forced: List[str]
    ) -> QCheckBox:
        boxes = []

        def update():
            target_list.clear()
            for b in boxes:
                if b.isChecked():
                    target_list.append(b.objectName())
            preferences.notify()

        group = QGroupBox(name)
        layout = QHBoxLayout()
        group.setLayout(layout)
        for option in options:
            box = QCheckBox(option)
            box.setObjectName(option)
            box.setChecked(option in target_list or option in forced)
            box.setEnabled(option not in forced)
            box.stateChanged.connect(update)
            boxes.append(box)
            layout.addWidget(box)
        layout.addWidget(QWidget(), 1)
        return group

    def step_options(
        self,
        name: str,
        edge_target: List[str],
        edge_options: List[str],
        edge_disabled: List[str],
        corner_target: List[str],
        corner_options: List[str],
        corner_disabled: List[str],
    ) -> QGroupBox:
        group = QGroupBox(name)
        layout = QHBoxLayout()
        group.setLayout(layout)
        layout.addWidget(
            self.piece_options("Edges", edge_target, edge_options, edge_disabled)
        )
        layout.addWidget(
            self.piece_options(
                "Corners", corner_target, corner_options, corner_disabled
            )
        )
        return group

    @cached_property
    def colors_widget(self) -> QWidget:
        group = QGroupBox("Colors")
        layout = QHBoxLayout()
        group.setLayout(layout)
        layout.addWidget(self.cube_colors_widget)
        layout.addWidget(self.opacity_widget)
        layout.addWidget(self.background_widget)
        return group

    @cached_property
    def cube_colors_widget(self) -> QWidget:
        group = QGroupBox("Cube")
        layout = QHBoxLayout()
        group.setLayout(layout)

        col = [QVBoxLayout(), QVBoxLayout(), QVBoxLayout()]
        for c in col:
            layout.addLayout(c)

        color_names = ["U", "D", "F", "B", "R", "L"]
        color_buttons = []
        for i, color in enumerate(preferences.colors):
            color_button = QWidget()
            color_button.setFixedSize(30, 30)
            color_button.setStyleSheet(
                f"background-color: rgb({color[0]}, {color[1]}, {color[2]}); border: 1px solid black;"
            )
            color_button.setCursor(Qt.PointingHandCursor)
            color_button.setToolTip(color_names[i])

            # Store the index for the clicked callback
            color_button.index = i

            # Connect mouse press event via installEventFilter
            color_button.mousePressEvent = lambda event, idx=i: self._show_color_dialog(
                idx
            )

            color_buttons.append(color_button)
            col[int(i / 2)].addWidget(color_button)

        def reset():
            preferences.colors = _DEFAULT_COLORS
            for i, c in enumerate(preferences.colors):
                color_buttons[i].setStyleSheet(
                    f"background-color: rgb({c[0]}, {c[1]}, {c[2]}); border: 1px solid black;"
                )
            preferences.notify()

        reset_button = QPushButton("Reset")
        layout.addWidget(reset_button)
        reset_button.clicked.connect(reset)

        layout.addWidget(self.background_widget)

        layout.addStretch(1)

        return group

    def _show_color_dialog(self, index):
        """Show a color dialog for selecting the color at the specified index"""
        from PyQt5.QtWidgets import QColorDialog
        from PyQt5.QtGui import QColor

        # Store a reference to self inside the color picker
        # This helps maintain the parent relationship
        self._current_color_picker = QColorDialog(self)

        # Set up the dialog with current color
        current_color = preferences.colors[index]
        initial_color = QColor(current_color[0], current_color[1], current_color[2])
        self._current_color_picker.setCurrentColor(initial_color)
        self._current_color_picker.setWindowTitle(f"Select Color {index+1}")

        # Define callback for when a color is selected
        def on_color_selected(color):
            if color.isValid():
                # Update the color in preferences
                new_color = (color.red(), color.green(), color.blue())
                preferences.colors[index] = new_color

                # Update the button appearance
                for button in self.findChildren(QWidget):
                    if hasattr(button, "index") and button.index == index:
                        button.setStyleSheet(
                            f"background-color: rgb({new_color[0]}, {new_color[1]}, {new_color[2]}); border: 1px solid black;"
                        )
                        break

                # Notify listeners about the change
                preferences.notify()

        # Connect signal and show the dialog
        self._current_color_picker.colorSelected.connect(on_color_selected)
        self._current_color_picker.finished.connect(lambda: self.activateWindow())
        self._current_color_picker.setModal(False)  # Make it non-modal
        self._current_color_picker.show()

    @cached_property
    def eo_widget(self) -> QWidget:
        minimal = RecognitionOptions.minimal()
        return self.step_options(
            "EO Recognition",
            preferences.recognition.eo_edges,
            [RecognitionOptionNames.BAD_PIECES, RecognitionOptionNames.ALL],
            minimal.eo_edges,
            preferences.recognition.eo_corners,
            [RecognitionOptionNames.ALL],
            minimal.eo_corners,
        )

    @cached_property
    def dr_widget(self) -> QWidget:
        minimal = RecognitionOptions.minimal()
        return self.step_options(
            "DR Recognition",
            preferences.recognition.dr_edges,
            [
                RecognitionOptionNames.BAD_FACES,
                RecognitionOptionNames.BAD_PIECES,
                RecognitionOptionNames.ALL,
            ],
            minimal.dr_edges,
            preferences.recognition.dr_corners,
            [
                RecognitionOptionNames.BAD_FACES,
                RecognitionOptionNames.BAD_PIECES,
                RecognitionOptionNames.ALL,
            ],
            minimal.dr_corners,
        )

    @cached_property
    def htr_widget(self) -> QWidget:
        minimal = RecognitionOptions.minimal()
        return self.step_options(
            "HTR Recognition",
            preferences.recognition.htr_edges,
            [
                RecognitionOptionNames.BAD_FACES,
                RecognitionOptionNames.BAD_PIECES,
                RecognitionOptionNames.TOP_COLOR,
                RecognitionOptionNames.BOTTOM_COLOR,
                RecognitionOptionNames.ALL,
            ],
            minimal.htr_edges,
            preferences.recognition.htr_corners,
            [
                RecognitionOptionNames.BAD_FACES,
                RecognitionOptionNames.BAD_PIECES,
                RecognitionOptionNames.TOP_COLOR,
                RecognitionOptionNames.BOTTOM_COLOR,
                RecognitionOptionNames.ALL,
            ],
            minimal.htr_corners,
        )

    @cached_property
    def fr_widget(self) -> QWidget:
        minimal = RecognitionOptions.minimal()
        return self.step_options(
            "FR Recognition",
            preferences.recognition.fr_edges,
            [
                RecognitionOptionNames.BAD_FACES,
                RecognitionOptionNames.BAD_PIECES,
                RecognitionOptionNames.ALL,
            ],
            minimal.fr_edges,
            preferences.recognition.fr_corners,
            [
                RecognitionOptionNames.BAD_FACES,
                RecognitionOptionNames.BAD_PIECES,
                RecognitionOptionNames.ALL,
            ],
            minimal.fr_corners,
        )

    @cached_property
    def background_widget(self) -> QWidget:
        group = QGroupBox("Background Color")
        layout = QHBoxLayout()
        group.setLayout(layout)
        slider = QSlider(Qt.Horizontal)
        layout.addWidget(slider)
        layout.addStretch(1)
        slider.setMinimum(0)
        slider.setMaximum(255)
        slider.setValue(preferences.background_color)

        def update():
            preferences.background_color = slider.value()
            preferences.notify()

        slider.valueChanged.connect(update)

        return group

    @cached_property
    def opacity_widget(self) -> QWidget:
        group = QGroupBox("Transparency")
        layout = QHBoxLayout()
        group.setLayout(layout)
        slider = QSlider(Qt.Horizontal)
        layout.addWidget(slider)
        layout.addStretch(1)
        slider.setMinimum(0)
        slider.setMaximum(75)
        slider.setValue(255 - preferences.opacity)

        def update():
            preferences.opacity = 255 - slider.value()
            preferences.notify()

        slider.valueChanged.connect(update)

        return group


_dialog = None


def show_dialog(parent):
    """Show preferences dialog and apply settings if accepted"""
    global _dialog
    if _dialog is None or not _dialog.isVisible():
        # Create a new dialog if it doesn't exist or isn't visible
        _dialog = PreferencesDialog(parent)
    _dialog.show()
    _dialog.raise_()  # Bring to front
    _dialog.activateWindow()  # Set as active window


def app_dir() -> Path:
    """Return platform-appropriate application home directory"""
    if sys.platform == "darwin":  # macOS
        return Path.home() / "Library" / "Preferences" / "vfmc"
    elif sys.platform == "win32":  # Windows
        return Path(os.environ.get("APPDATA", str(Path.home()))) / "vfmc"
    else:  # Linux/Unix
        return Path.home() / ".config" / "vfmc"


# Preferences as saved by the user
preferences = Preferences.load()
