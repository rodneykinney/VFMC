# Rotation matrix for different faces
AXIS_ROTATIONS = {
    "f": ["u", "l", "d", "r"],
    "b": ["u", "r", "d", "l"],
    "r": ["u", "f", "d", "b"],
    "l": ["u", "b", "d", "f"],
    "u": ["f", "r", "b", "l"],
    "d": ["f", "l", "b", "r"],
}

OPPOSITES = {
    "f": "b",
    "b": "f",
    "r": "l",
    "l": "r",
    "u": "d",
    "d": "u",
}


# Default cube orientations for different steps
VARIANT_ORIENTATIONS = {
    "": {"": ("u", "f")},
    "eo": {
        "ud": ("b", "u"),
        "fb": ("u", "f"),
        "rl": ("u", "r"),
    },
    "*": {
        "ud": ("u", "f"),
        "fb": ("b", "u"),
        "rl": ("r", "f"),
        "*": ("u", "f"),
    },
}


class Orientation:
    def __init__(self, top: str, front: str):
        self.top = top
        self.front = front

    def x(self, ticks: int) -> "Orientation":
        rot = AXIS_ROTATIONS[self.right]
        return Orientation(
            top=rot[(rot.index(self.top) + ticks) % 4],
            front=rot[(rot.index(self.front) + ticks) % 4],
        )

    @property
    def right(self):
        rot = AXIS_ROTATIONS[self.top]
        return rot[(rot.index(self.front) + 1) % 4]

    def z(self, ticks: int) -> "Orientation":
        rot = AXIS_ROTATIONS[self.front]
        return Orientation(top=rot[(rot.index(self.top) + ticks) % 4], front=self.front)

    def y(self, ticks: int) -> "Orientation":
        rot = AXIS_ROTATIONS[self.top]
        return Orientation(top=self.top, front=rot[(rot.index(self.front) + ticks) % 4])

    def __repr__(self):
        return f"top={self.top}, front={self.front}"

    @staticmethod
    def default_for(kind, variant) -> "Orientation":
        d = VARIANT_ORIENTATIONS.get(kind, VARIANT_ORIENTATIONS.get("*"))
        return Orientation(*d.get(variant, d.get("*")))
