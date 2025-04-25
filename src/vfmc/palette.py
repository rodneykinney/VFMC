from enum import Enum
from typing import Dict, Tuple, List

from black.trans import defaultdict


class FaceletColors(Enum):
    WHITE = 0
    YELLOW = 1
    GREEN = 2
    BLUE = 3
    RED = 4
    ORANGE = 5
    HIDDEN = 6


class Visibility(Enum):
    GoodFace = 0
    BadFace = 1
    BadPieceGoodFace = 2
    UsedForCaseID = 3


_HIGH_VISIBILITY = 237
_MED_VISIBILITY = 110
_LOW_VISIBILITY = 51


class Palette:
    def __init__(
        self,
        colors: Dict[FaceletColors, Tuple],
        opacities: Dict[Visibility, int],
        hidden_color: Tuple,
    ):
        self.colors = colors
        self.opacities = opacities
        self.hidden_color = hidden_color

    def color_of(self, f: FaceletColors, v: Visibility) -> Tuple:
        if v not in self.opacities:
            return self.hidden_color
        return self.colors[f] + (self.opacities[v],)

    @staticmethod
    def names() -> List[str]:
        return ["bad", "all"]

    @staticmethod
    def by_name(name) -> "Palette":
        if name == "bad":
            return Palette.by_name("")
        elif name == "all":
            p = Palette.by_name("")
            p.opacities = dict((v, _HIGH_VISIBILITY) for v in Visibility)
            return p
        elif name == "test":
            p = Palette.by_name("")
            o = {
                Visibility.BadPieceGoodFace: _MED_VISIBILITY,
                Visibility.UsedForCaseID: _MED_VISIBILITY,
            }
            p.opacities.update(o)
            return p
        else:
            c = {
                FaceletColors.WHITE: (255, 255, 255),
                FaceletColors.YELLOW: (255, 255, 0),
                FaceletColors.GREEN: (0, 153, 0),
                FaceletColors.BLUE: (0, 0, 255),
                FaceletColors.RED: (255, 0, 0),
                FaceletColors.ORANGE: (255, 94, 51),  # (255, 204, 25),
            }
            o = {
                Visibility.BadFace: _HIGH_VISIBILITY,
                Visibility.UsedForCaseID: _HIGH_VISIBILITY,
            }
            return Palette(c, o, (255, 255, 255, _LOW_VISIBILITY))
