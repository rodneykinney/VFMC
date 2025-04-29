from enum import Enum
import functools
from linecache import cache
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
    IRRELEVANT = 0
    BAD = 1
    GOOD_ON_BAD = 2
    RELEVANT = 3


_HIGH_VISILIBITY = 237
_MEDIUM_VISIBILITY = 110
_LOW_VISIBILITY = 51

opacity_names = {
    "high": _HIGH_VISILIBITY,
    "med": _MEDIUM_VISIBILITY,
    "low": _LOW_VISIBILITY,
    "none": 0,
}

vis_names = {
    "irrelevant": Visibility.IRRELEVANT,
    "relevant": Visibility.RELEVANT,
    "bad": Visibility.BAD,
    "good_on_bad": Visibility.GOOD_ON_BAD,
}


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

    def configure(self, d):
        o = dict((vis_names[k], opacity_names[v]) for k, v in d.items())
        o = {}
        for k, v in d.items():
            vis = vis_names[k]
            if v == "none":
                if vis in self.opacities:
                    del self.opacities[vis]
            else:
                o[vis] = opacity_names[v]
        self.opacities.update(o)

    def color_of(self, f: FaceletColors, v: Visibility) -> Tuple:
        if v not in self.opacities:
            return self.hidden_color
        return self.colors[f] + (self.opacities[v],)

    @staticmethod
    def names() -> List[str]:
        return ["bad", "all"]

    @staticmethod
    def _default() -> "Palette":
        c = {
            FaceletColors.WHITE: (255, 255, 255),
            FaceletColors.YELLOW: (255, 255, 0),
            FaceletColors.GREEN: (0, 153, 0),
            FaceletColors.BLUE: (0, 0, 255),
            FaceletColors.RED: (255, 0, 0),
            FaceletColors.ORANGE: (255, 94, 51),  # (255, 204, 25),
        }
        o = {
            Visibility.BAD: _HIGH_VISILIBITY,
        }
        return Palette(c, o, (255, 255, 255, _LOW_VISIBILITY))

    @staticmethod
    @functools.lru_cache(maxsize=None)
    def by_name(name) -> "Palette":
        if name == "eo":
            return Palette._default()
        elif name == "dr":
            p = Palette._default()
            return p
        elif name == "htr":
            p = Palette._default()
            p.opacities.update(
                {
                    Visibility.RELEVANT: _HIGH_VISILIBITY,
                }
            )
            return p
        elif name == "all":
            p = Palette._default()
            p.opacities.update(
                {
                    Visibility.GOOD_ON_BAD: _HIGH_VISILIBITY,
                    Visibility.RELEVANT: _HIGH_VISILIBITY,
                    Visibility.IRRELEVANT: _HIGH_VISILIBITY,
                }
            )
            return p
        else:
            return Palette._default()
