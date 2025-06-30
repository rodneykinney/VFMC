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


class Palette:
    def __init__(
        self,
        colors: Dict[FaceletColors, Tuple],
        edge_visibility_mask: int,
        center_visibility_mask: int,
        corner_visibility_mask: int,
        hidden_color: Tuple,
        opacity: int,
    ):
        """Colors for drawing the cube"""
        self.colors = colors
        self.edge_visibility_mask = edge_visibility_mask
        self.center_visibility_mask = center_visibility_mask
        self.corner_visibility_mask = corner_visibility_mask
        self.hidden_color = hidden_color
        self.opacity = opacity

    def color_of_edge(self, f: FaceletColors, visibility: int) -> Tuple:
        if visibility & self.edge_visibility_mask == 0:
            return self.hidden_color
        c = self.colors[f]
        return self.colors[f] + (self.opacity,) if len(c) < 4 else c

    def color_of_center(self, f: FaceletColors, visibility: int) -> Tuple:
        if visibility & self.center_visibility_mask == 0:
            return self.hidden_color
        c = self.colors[f]
        return self.colors[f] + (self.opacity,) if len(c) < 4 else c

    def color_of_corner(self, f: FaceletColors, visibility: int) -> Tuple:
        if visibility & self.corner_visibility_mask == 0:
            return self.hidden_color
        c = self.colors[f]
        return self.colors[f] + (self.opacity,) if len(c) < 4 else c

    @staticmethod
    def by_name(name) -> "Palette":
        colors = dict(
            (FaceletColors(k), tuple(v)) for k, v in enumerate(preferences.colors)
        )
        bg = preferences.background_color
        h, o = (0, 51) if bg > 128 else (255, 51)
        hidden = (h, h, h, o)
        p = Palette(colors, 0, 255, 0, hidden, preferences.opacity)
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
        elif name == "finish":
            p.edge_visibility_mask = Visibility.All
            p.corner_visibility_mask = Visibility.All
        elif name == "insertions":
            p.edge_visibility_mask = Visibility.BadPiece
            p.corner_visibility_mask = Visibility.BadPiece
        elif name == "eo-case":
            p.center_visibility_mask = 0
            p.opacity = 255
            p.edge_visibility_mask = Visibility.BadPiece
            p.colors = dict((FaceletColors(i), (0, 0, 0)) for i in range(6))
        elif name == "cp-case":
            p.center_visibility_mask = 0
            p.opacity = 255
            p.corner_visibility_mask = Visibility.BadPiece
            p.colors = dict((FaceletColors(i), (0, 0, 0)) for i in range(6))
            p.colors.update(
                {
                    FaceletColors.BLUE: p.hidden_color,
                    FaceletColors.GREEN: p.hidden_color,
                }
            )
        elif name == "rzp-breaking":
            p.center_visibility_mask = 0
            p.opacity = 255
            p.corner_visibility_mask = Visibility.BadFace
            p.edge_visibility_mask = 0
            p.colors.update(
                {
                    FaceletColors.BLUE: (0, 0, 0),
                    FaceletColors.GREEN: (0, 0, 0),
                    FaceletColors.RED: (0, 0, 0),
                    FaceletColors.ORANGE: (0, 0, 0),
                    FaceletColors.YELLOW: (255, 255, 255),
                }
            )
        elif name == "co-case":
            p.center_visibility_mask = 0
            p.opacity = 255
            p.corner_visibility_mask = Visibility.BadFace
            p.colors[FaceletColors.ORANGE] = p.colors[FaceletColors.RED]
            p.colors[FaceletColors.BLUE] = p.colors[FaceletColors.GREEN]
            p.colors[FaceletColors.YELLOW] = p.colors[FaceletColors.WHITE]
        elif name == "dr-corner-case":
            p.center_visibility_mask = 0
            p.opacity = 200
            p.corner_visibility_mask = Visibility.BadPiece
            p.edge_visibility_mask = 0
        elif name == "htr-corner-case":
            p.center_visibility_mask = 0
            p.opacity = 255
            p.corner_visibility_mask = Visibility.BadFace
            p.colors[FaceletColors.ORANGE] = p.colors[FaceletColors.RED]
            p.colors[FaceletColors.BLUE] = p.colors[FaceletColors.GREEN]
        elif name == "htr-case":
            p.center_visibility_mask = 0
            p.opacity = 255
            p.edge_visibility_mask = Visibility.BadFace
            p.colors[FaceletColors.ORANGE] = p.colors[FaceletColors.RED]
            p.colors[FaceletColors.BLUE] = p.colors[FaceletColors.GREEN]
        elif name == "corner-edge-case":
            p.center_visibility_mask = 0
            p.opacity = 255
            p.corner_visibility_mask = Visibility.BadFace
            p.edge_visibility_mask = Visibility.BadFace
            p.colors[FaceletColors.ORANGE] = p.colors[FaceletColors.RED]
            p.colors[FaceletColors.BLUE] = p.colors[FaceletColors.GREEN]
        else:
            p.edge_visibility_mask = Visibility.All
            p.corner_visibility_mask = Visibility.All
        for opt in options[0]:
            p.edge_visibility_mask |= _VISIBILITY_NAMES.get(opt, 0)
        for opt in options[1]:
            p.corner_visibility_mask |= _VISIBILITY_NAMES.get(opt, 0)
        return p
