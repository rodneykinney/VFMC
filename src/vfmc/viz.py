import math
import numpy as np
from PyQt5.QtCore import QTimer, Qt, QEvent
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QPolygon

from vfmc.attempt import Attempt, Orientation, AXIS_ROTATIONS
from vfmc.palette import FaceletColors, Visibility, Palette
from vfmc.prefs import preferences
from pyquaternion import Quaternion

# X coordinate of cube facelets
# U + L + F + R + B + D
facelet_x = (
    [-1, 0, 1, -1, 0, 1, -1, 0, 1]
    + [-1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5]
    + [-1, 0, 1, -1, 0, 1, -1, 0, 1]
    + [1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5]
    + [1, 0, -1, 1, 0, -1, 1, 0, -1]
    + [-1, 0, 1, -1, 0, 1, -1, 0, 1]
)

# Y coordinate of cube facelets
# U + L + F + R + B + D
facelet_y = (
    [1, 1, 1, 0, 0, 0, -1, -1, -1]
    + [1, 0, -1, 1, 0, -1, 1, 0, -1]
    + [-1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5]
    + [-1, 0, 1, -1, 0, 1, -1, 0, 1]
    + [1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5]
    + [-1, -1, -1, 0, 0, 0, 1, 1, 1]
)

# Z coordinate of cube facelets
# U + L + F + R + B + D
facelet_z = (
    [1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5]
    + [1, 1, 1, 0, 0, 0, -1, -1, -1]
    + [1, 1, 1, 0, 0, 0, -1, -1, -1]
    + [1, 1, 1, 0, 0, 0, -1, -1, -1]
    + [1, 1, 1, 0, 0, 0, -1, -1, -1]
    + [-1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5]
)

# Coordinates of the facelet in different plains, relative to the facelet center
FACELET_VERTICES = {
    "xy": [
        np.array([-0.48, -0.48, 0.0]),
        np.array([0.48, -0.48, 0.0]),
        np.array([0.48, 0.48, 0.0]),
        np.array([-0.48, 0.48, 0.0]),
    ],
    "xz": [
        np.array([-0.48, 0.0, -0.48]),
        np.array([0.48, 0.0, -0.48]),
        np.array([0.48, 0.0, 0.48]),
        np.array([-0.48, 0.0, 0.48]),
    ],
    "yz": [
        np.array([0.0, -0.48, -0.48]),
        np.array([0.0, 0.48, -0.48]),
        np.array([0.0, 0.48, 0.48]),
        np.array([0.0, -0.48, 0.48]),
    ],
}

# Plane in which each facelet exists
# U + L + F + R + B + D
FACELET_AXIS = (
    ["xy"] * 9 + ["yz"] * 9 + ["xz"] * 9 + ["yz"] * 9 + ["xz"] * 9 + ["xy"] * 9
)

# Colors of the corner pieces, for orientation 0,1,2
CORNER_PIECE_COLORS = [
    (FaceletColors.WHITE, FaceletColors.ORANGE, FaceletColors.BLUE),
    (FaceletColors.WHITE, FaceletColors.BLUE, FaceletColors.RED),
    (FaceletColors.WHITE, FaceletColors.RED, FaceletColors.GREEN),
    (FaceletColors.WHITE, FaceletColors.GREEN, FaceletColors.ORANGE),
    (FaceletColors.YELLOW, FaceletColors.ORANGE, FaceletColors.GREEN),
    (FaceletColors.YELLOW, FaceletColors.GREEN, FaceletColors.RED),
    (FaceletColors.YELLOW, FaceletColors.RED, FaceletColors.BLUE),
    (FaceletColors.YELLOW, FaceletColors.BLUE, FaceletColors.ORANGE),
]

# Index of the facelet (orientation 0,1,2) for each of the corners
CORNER_POSITION_FACELETS = [
    (0, 9, 38),  # UBL
    (2, 36, 29),  # UBR
    (8, 27, 20),  # UFR
    (6, 18, 11),  # UFL
    (45, 17, 24),  # DFL
    (47, 26, 33),  # DFR
    (53, 35, 42),  # DBR
    (51, 44, 15),  # DBL
]

# Colors of the edge pieces, for orientation 0,1
EDGE_PIECE_COLORS = [
    (FaceletColors.WHITE, FaceletColors.BLUE),
    (FaceletColors.WHITE, FaceletColors.RED),
    (FaceletColors.WHITE, FaceletColors.GREEN),
    (FaceletColors.WHITE, FaceletColors.ORANGE),
    (FaceletColors.GREEN, FaceletColors.RED),
    (FaceletColors.GREEN, FaceletColors.ORANGE),
    (FaceletColors.BLUE, FaceletColors.RED),
    (FaceletColors.BLUE, FaceletColors.ORANGE),
    (FaceletColors.YELLOW, FaceletColors.GREEN),
    (FaceletColors.YELLOW, FaceletColors.RED),
    (FaceletColors.YELLOW, FaceletColors.BLUE),
    (FaceletColors.YELLOW, FaceletColors.ORANGE),
]

# Index of the facelet (orientation 0,1) for each of the edges
EDGE_POSITION_FACELETS = [
    (1, 37),  # UB
    (5, 28),  # UR
    (7, 19),  # UF
    (3, 10),  # UL
    (23, 30),  # FR
    (21, 14),  # FL
    (39, 32),  # BR
    (41, 12),  # BL
    (46, 25),  # DF
    (50, 34),  # DR
    (52, 43),  # DB
    (48, 16),  # DL
]

# The slice where each edge belongs, when the cube is solved
# 0 = M, 1 = E, 2 = S
HOME_SLICE = [0, 2, 0, 2, 1, 1, 1, 1, 0, 2, 0, 2]

# Orientation (in cubelib bit representation) for a correctly-oriented edge
# Index is the combination of the edge's home slice and the slice where it currently is
DEFAULT_ORIENTATION = [
    0,  # Piece is in its home slice
    5,  # E <-> M
    4,  # M <-> S
    1,  # E <-> S
]


class CubeViz:
    """Cube visualization logic"""

    def __init__(
        self,
        attempt: Attempt,
    ):
        self.attempt = attempt
        self.attempt.add_cube_listener(self.refresh)
        preferences.add_listener(self.refresh)

        # Initial camera position
        self.init_camera(0, -10, 6)
        self.view_y = -math.pi / 6
        self.view_x = 0

        self.colors = [(1, 1, 1, 0.2)] * 54
        self.palette = None
        self.hide_nearest_faces = False

    def init_camera(self, x, y, z):
        self.camera = np.array([x, y, z])

        z_axis = np.array([0, 0, 1])
        screen_x_dir = np.cross(-self.camera, z_axis)
        self.screen_x_dir = screen_x_dir / np.linalg.norm(screen_x_dir)
        screen_y_dir = np.cross(self.camera, self.screen_x_dir)
        self.screen_y_dir = screen_y_dir / np.linalg.norm(screen_y_dir)

    def set_palette(self, p: Palette):
        self.palette = p
        self.refresh()

    def get_palette(self) -> Palette:
        return self.palette or Palette.by_name(self.attempt.solution.kind)

    def handle_toggle_view_event(self, obj, event):
        if (
            event.type() == QEvent.KeyPress
            and event.key() == Qt.Key_Alt
            and not event.isAutoRepeat()
        ):
            self.hide_nearest_faces = True
            return True
        if (
            event.type() == QEvent.KeyRelease
            and event.key() == Qt.Key_Alt
            and not event.isAutoRepeat()
        ):
            self.hide_nearest_faces = False
            return True
        return False

    def refresh(self):
        palette = self.get_palette()
        self.colors = [palette.hidden_color] * 54
        self.colors[4] = palette.color_of_edge(FaceletColors.WHITE, Visibility.All)
        self.colors[13] = palette.color_of_edge(FaceletColors.ORANGE, Visibility.All)
        self.colors[22] = palette.color_of_edge(FaceletColors.GREEN, Visibility.All)
        self.colors[31] = palette.color_of_edge(FaceletColors.RED, Visibility.All)
        self.colors[40] = palette.color_of_edge(FaceletColors.BLUE, Visibility.All)
        self.colors[49] = palette.color_of_edge(FaceletColors.YELLOW, Visibility.All)
        corners = self.attempt.cube.corners()
        corner_visibility = self.attempt.corner_visibility()
        for i in range(0, 8):
            piece_id, orientation = corners[i]
            for side in range(0, 3):
                face = (side + 3 - orientation) % 3
                self.colors[CORNER_POSITION_FACELETS[i][side]] = (
                    palette.color_of_corner(
                        CORNER_PIECE_COLORS[piece_id][face], corner_visibility[i][side]
                    )
                )
        edges = self.attempt.cube.edges()
        edge_visibility = self.attempt.edge_visibility()
        for i in range(0, 12):
            piece_id, piece_orientation = edges[i]
            orientation = DEFAULT_ORIENTATION[HOME_SLICE[piece_id] ^ HOME_SLICE[i]]
            flipped = 0 if piece_orientation == orientation else 1
            for side in range(0, 2):
                self.colors[EDGE_POSITION_FACELETS[i][side]] = palette.color_of_edge(
                    EDGE_PIECE_COLORS[edges[i][0]][(side + flipped) % 2],
                    edge_visibility[i][side],
                )

    def draw_facelet(self, painter, w, h, rotation_matrix, x, y, z, color, axis):
        # Define the vertices of the square face based on axis

        vertex_center = np.array([x, y, z])
        # Transform vertices to world coordinates
        transformed_vertices = [
            rotation_matrix @ (v + vertex_center) for v in FACELET_VERTICES[axis]
        ]

        scale_factor = min(w, h) * np.linalg.norm(self.camera) / 5
        screen_vertices = [
            (
                w / 2
                + scale_factor
                * np.dot(v, self.screen_x_dir)
                / np.linalg.norm(v - self.camera),
                h / 2
                - scale_factor
                * np.dot(v, self.screen_y_dir)
                / np.linalg.norm(v - self.camera),
            )
            for v in transformed_vertices
        ]

        # Enable antialiasing for smoother edges
        painter.setRenderHint(QPainter.Antialiasing)

        # Create a semi-transparent pen with alpha channel (RGBA)
        qcol = QColor(*color)
        pen = QPen(QColor(255, 255, 255, 16), 1)
        painter.setPen(pen)

        # Create a semi-transparent brush with alpha channel
        brush = QBrush(qcol)
        painter.setBrush(brush)
        from PyQt5 import QtCore

        polygon = QPolygon([QtCore.QPoint(*v) for v in screen_vertices])
        painter.drawPolygon(polygon)

    def set_inverse(self, inverse: bool):
        self.inverse = inverse

    def update(self):
        self.refresh()

    def draw(self, painter, w, h):
        # Clear the screen with the background color
        bg = preferences.background_color
        painter.fillRect(0, 0, w, h, QColor(bg, bg, bg))
        # Apply rotation
        q = (
            Quaternion(axis=[1, 0, 0], angle=self.view_x)
            * Quaternion(axis=[0, 0, 1], angle=self.view_y)
            * rotation_for(self.attempt.solution.orientation)
        )
        rotation_matrix = q.rotation_matrix

        # Order faces from back to front
        def distance(i):
            v_rotated = q.rotate([facelet_x[i], facelet_y[i], facelet_z[i]])
            return np.linalg.norm(v_rotated - self.camera)

        faces = [(range(9 * i, 9 * (i + 1)), distance(9 * i + 4)) for i in range(0, 6)]
        faces.sort(key=lambda x: -x[1])
        faces = [f for f, d in faces]

        hidden_color = self.get_palette().hidden_color
        for f, face in enumerate(faces):
            for i in face:
                color = self.colors[i]
                if self.hide_nearest_faces and f >= 3:
                    color = hidden_color
                if f < 3 and color != hidden_color:
                    color = color[:3] + (255,)
                self.draw_facelet(
                    painter,
                    w,
                    h,
                    rotation_matrix,
                    facelet_x[i],
                    facelet_y[i],
                    facelet_z[i],
                    color,
                    FACELET_AXIS[i],
                )

    def rotate(self, dx, dy=0):
        self.view_y += dx * 0.005
        self.view_x += dy * 0.005


def rotation_for(o: Orientation) -> Quaternion:
    # Return the quaternion that brings a default cube into the given orientation
    base = Orientation("u", "f")
    if o.top in "fb":
        ticks = AXIS_ROTATIONS["r"].index(o.top)
        base = base.x(ticks)
        q = Quaternion(axis=[1, 0, 0], angle=-math.pi / 2 * ticks)
    else:
        ticks = AXIS_ROTATIONS["f"].index(o.top)
        q = Quaternion(axis=[0, 1, 0], angle=math.pi / 2 * ticks)
        base = base.z(ticks)
    ticks = (
        AXIS_ROTATIONS[base.top].index(o.front)
        - AXIS_ROTATIONS[base.top].index(base.front)
        + 4
    )
    q = Quaternion(axis=[0, 0, 1], angle=-math.pi / 2 * ticks) * q
    return q


class CubeWidget(QWidget):
    """OpenGL widget that uses CubeViz for rendering"""

    def __init__(self, viz: CubeViz, parent=None):
        super(CubeWidget, self).__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Timer for update loop
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_surface)
        self.timer.start(30)  # ~60 FPS

        self.setMinimumSize(400, 400)

        self.viz = viz
        self.viz.attempt.add_cube_listener(self.refresh)
        self.previous_solution = self.viz.attempt.solution

        # Mouse tracking
        self.setMouseTracking(True)
        self.last_mouse_pos = None
        self.dragging = False

    def refresh(self):
        # Repaint
        self.update()

    def update_surface(self):
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        self.viz.draw(painter, self.width(), self.height())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.last_mouse_pos = event.pos()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False

    def mouseMoveEvent(self, event):
        if self.dragging and self.last_mouse_pos:
            dx = event.x() - self.last_mouse_pos.x()
            dy = event.y() - self.last_mouse_pos.y()
            self.viz.rotate(dx, dy)
            self.last_mouse_pos = event.pos()
