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


class FaceletColor(Enum):
    WHITE = 0
    YELLOW = 1
    GREEN = 2
    BLUE = 3
    RED = 4
    ORANGE = 5


class Palette:
    def __init__(
        self,
        colors: Dict[FaceletColor, Tuple],
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
        self.hidden_opacity = 0
        self.hidden_saturation = 0

    def set_hidden_render(self, opacity, saturation):
        self.hidden_opacity = opacity
        self.hidden_saturation = saturation

    def color_of_edge(self, f: FaceletColor, visibility: int) -> Tuple:
        if visibility & self.edge_visibility_mask == 0:
            return self.color_when_hidden(f)
        c = self.colors[f]
        return self.colors[f] + (self.opacity,) if len(c) < 4 else c

    def color_when_hidden(self, f: FaceletColor) -> Tuple:
        if self.hidden_opacity == 0:
            return self.hidden_color
        else:
            r,g,b = self.colors[f]
            grey = (r+g+b) / 3
            sat = 1 - min(r,g,b) / max(r,g,b)
            new_sat = sat * self.hidden_saturation
            r = grey + new_sat * (r - grey)
            g = grey + new_sat * (g - grey)
            b = grey + new_sat * (b - grey)
            c = (r,g,b,self.hidden_opacity)
            return c

    def color_of_center(self, f: FaceletColor, visibility: int) -> Tuple:
        if visibility & self.center_visibility_mask == 0:
            return self.color_when_hidden(f)
        c = self.colors[f]
        return self.colors[f] + (self.opacity,) if len(c) < 4 else c

    def color_of_corner(self, f: FaceletColor, visibility: int) -> Tuple:
        if visibility & self.corner_visibility_mask == 0:
            return self.color_when_hidden(f)
        c = self.colors[f]
        return self.colors[f] + (self.opacity,) if len(c) < 4 else c

    @staticmethod
    def by_name(name) -> "Palette":
        colors = dict(
            (FaceletColor(k), tuple(v)) for k, v in enumerate(preferences.colors)
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
            p.colors = dict((FaceletColor(i), (0, 0, 0)) for i in range(6))
        elif name == "cp-case":
            p.center_visibility_mask = 0
            p.opacity = 255
            p.corner_visibility_mask = Visibility.BadPiece
            p.colors = dict((FaceletColor(i), (0, 0, 0)) for i in range(6))
            p.colors.update(
                {
                    FaceletColor.BLUE: p.hidden_color,
                    FaceletColor.GREEN: p.hidden_color,
                }
            )
        elif name == "co-case":
            p.center_visibility_mask = 0
            p.opacity = 255
            p.corner_visibility_mask = Visibility.BadFace
            p.colors[FaceletColor.ORANGE] = p.colors[FaceletColor.RED]
            p.colors[FaceletColor.BLUE] = p.colors[FaceletColor.GREEN]
            p.colors[FaceletColor.YELLOW] = p.colors[FaceletColor.WHITE]
        elif name == "htr-corner-case":
            p.center_visibility_mask = 0
            p.opacity = 255
            p.corner_visibility_mask = Visibility.BadFace
            p.colors[FaceletColor.ORANGE] = p.colors[FaceletColor.RED]
            p.colors[FaceletColor.BLUE] = p.colors[FaceletColor.GREEN]
        elif name == "htr-case":
            p.center_visibility_mask = 0
            p.opacity = 255
            p.edge_visibility_mask = Visibility.BadFace
            p.colors[FaceletColor.ORANGE] = p.colors[FaceletColor.RED]
            p.colors[FaceletColor.BLUE] = p.colors[FaceletColor.GREEN]
        elif name == "corner-edge-case":
            p.center_visibility_mask = 0
            p.opacity = 255
            p.corner_visibility_mask = Visibility.BadFace
            p.edge_visibility_mask = Visibility.BadFace
            p.colors[FaceletColor.ORANGE] = p.colors[FaceletColor.RED]
            p.colors[FaceletColor.BLUE] = p.colors[FaceletColor.GREEN]
        else:
            p.edge_visibility_mask = Visibility.All
            p.corner_visibility_mask = Visibility.All
        for opt in options[0]:
            p.edge_visibility_mask |= _VISIBILITY_NAMES.get(opt, 0)
        for opt in options[1]:
            p.corner_visibility_mask |= _VISIBILITY_NAMES.get(opt, 0)
        return p
