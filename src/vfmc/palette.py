from enum import Enum
from typing import Dict, Tuple

from vfmc.prefs import preferences, RecognitionOptionNames


class Visibility:
    """Bit mask to describe facelets while solving a step"""

    Any = 1
    BadFace = 2
    BadPiece = 4
    BottomColor = 8
    TopColor = 16
    All = 255


# Map of preference keys to Visibility bit mask
_VISIBILITY_NAMES = {
    RecognitionOptionNames.BAD_FACES: Visibility.BadFace,
    RecognitionOptionNames.BAD_PIECES: Visibility.BadPiece,
    RecognitionOptionNames.TOP_COLOR: Visibility.TopColor,
    RecognitionOptionNames.BOTTOM_COLOR: Visibility.BottomColor,
    RecognitionOptionNames.ALL: Visibility.All,
}


class FaceletColors(Enum):
    WHITE = 0
    YELLOW = 1
    GREEN = 2
    BLUE = 3
    RED = 4
    ORANGE = 5
    HIDDEN = 6


class Palette:
    def __init__(
        self,
        colors: Dict[FaceletColors, Tuple],
        edge_visibility_mask: int,
        corner_visibility_mask: int,
        hidden_color: Tuple,
        opacity: int,
    ):
        """Colors for drawing the cube"""
        self.colors = colors
        self.edge_visibility_mask = edge_visibility_mask
        self.corner_visibility_mask = corner_visibility_mask
        self.hidden_color = hidden_color
        self.opacity = opacity

    def color_of_edge(self, f: FaceletColors, visibility: int) -> Tuple:
        if visibility & self.edge_visibility_mask == 0:
            return self.hidden_color
        return self.colors[f] + (self.opacity,)

    def color_of_corner(self, f: FaceletColors, visibility: int) -> Tuple:
        if visibility & self.corner_visibility_mask == 0:
            return self.hidden_color
        return self.colors[f] + (self.opacity,)

    @staticmethod
    def by_name(name) -> "Palette":
        colors = dict(
            (FaceletColors(k), tuple(v)) for k, v in enumerate(preferences.colors)
        )
        bg = preferences.background_color
        h = 0 if bg > 128 else 255
        hidden = (h, h, h, 51)
        p = Palette(colors, 0, 0, hidden, preferences.opacity)
        options = [], []
        if name == "eo":
            options = (
                preferences.recognition.eo_edges,
                preferences.recognition.eo_corners,
            )
        elif name == "dr":
            options = (
                preferences.recognition.dr_edges,
                preferences.recognition.dr_corners,
            )
        elif name == "htr":
            options = (
                preferences.recognition.htr_edges,
                preferences.recognition.htr_corners,
            )
        elif name == "fr":
            options = (
                preferences.recognition.fr_edges,
                preferences.recognition.fr_corners,
            )
        elif name == "slice":
            p.edge_visibility_mask = Visibility.BadPiece
            p.corner_visibility_mask = Visibility.BadPiece
        else:
            p.edge_visibility_mask = Visibility.All
            p.corner_visibility_mask = Visibility.All
        for opt in options[0]:
            p.edge_visibility_mask |= _VISIBILITY_NAMES.get(opt, 0)
        for opt in options[1]:
            p.corner_visibility_mask |= _VISIBILITY_NAMES.get(opt, 0)
        return p
