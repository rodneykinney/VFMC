import sys
import logging
import os
from enum import Enum

import math
import numpy as np
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QPolygon

from vfmc.attempt import PartialSolution, Attempt, Orientation, AXIS_ROTATIONS
from vfmc_core import (Cube, StepInfo)
from pyquaternion import Quaternion

# U + L + F + R + B + D
facelet_x = \
    [-1, 0, 1, -1, 0, 1, -1, 0, 1] \
    + [-1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5] \
    + [-1, 0, 1, -1, 0, 1, -1, 0, 1] \
    + [1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5] \
    + [1, 0, -1, 1, 0, -1, 1, 0, -1] \
    + [-1, 0, 1, -1, 0, 1, -1, 0, 1]
facelet_y = \
    [1, 1, 1, 0, 0, 0, -1, -1, -1] \
    + [1, 0, -1, 1, 0, -1, 1, 0, -1] \
    + [-1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5] \
    + [-1, 0, 1, -1, 0, 1, -1, 0, 1] \
    + [1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5] \
    + [-1, -1, -1, 0, 0, 0, 1, 1, 1]
facelet_z = \
    [1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5] \
    + [1, 1, 1, 0, 0, 0, -1, -1, -1] \
    + [1, 1, 1, 0, 0, 0, -1, -1, -1] \
    + [1, 1, 1, 0, 0, 0, -1, -1, -1] \
    + [1, 1, 1, 0, 0, 0, -1, -1, -1] \
    + [-1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5]

FACELET_VERTICES = {
    'xy': [
        np.array([-0.48, -0.48, 0.0]),
        np.array([0.48, -0.48, 0.0]),
        np.array([0.48, 0.48, 0.0]),
        np.array([-0.48, 0.48, 0.0])
    ],
    'xz': [
        np.array([-0.48, 0.0, -0.48]),
        np.array([0.48, 0.0, -0.48]),
        np.array([0.48, 0.0, 0.48]),
        np.array([-0.48, 0.0, 0.48]),
    ],
    'yz': [
        np.array([0.0, -0.48, -0.48]),
        np.array([0.0, 0.48, -0.48]),
        np.array([0.0, 0.48, 0.48]),
        np.array([0.0, -0.48, 0.48]),
    ]
}

axis = ["xy"] * 9 \
       + ["yz"] * 9 \
       + ["xz"] * 9 \
       + ["yz"] * 9 \
       + ["xz"] * 9 \
       + ["xy"] * 9

WHITE = (1, 1, 1)
YELLOW = (1, 1, 0)
GREEN = (0, .6, 0)
BLUE = (0, 0, 1)
RED = (1, 0, 0)
# ORANGE = (1, .8, .1)
ORANGE = (1, .37, .2)
GREY = (0.75, 0.75, 0.75)
BACKGROUND = .3

corner_piece_colors = [
    (WHITE, ORANGE, BLUE),
    (WHITE, BLUE, RED),
    (WHITE, RED, GREEN),
    (WHITE, GREEN, ORANGE),
    (YELLOW, ORANGE, GREEN),
    (YELLOW, GREEN, RED),
    (YELLOW, RED, BLUE),
    (YELLOW, BLUE, ORANGE),
]

corner_position_facelets = [
    (0, 9, 38),  # UBL
    (2, 36, 29),  # UBR
    (8, 27, 20),  # UFR
    (6, 18, 11),  # UFL
    (45, 17, 24),  # DFL
    (47, 26, 33),  # DFR
    (53, 35, 42),  # DBR
    (51, 44, 15),  # DBL
]

edge_piece_colors = [
    (WHITE, BLUE),
    (WHITE, RED),
    (WHITE, GREEN),
    (WHITE, ORANGE),
    (GREEN, RED),
    (GREEN, ORANGE),
    (BLUE, RED),
    (BLUE, ORANGE),
    (YELLOW, GREEN),
    (YELLOW, RED),
    (YELLOW, BLUE),
    (YELLOW, ORANGE),
]

edge_position_facelets = [
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

home_slice = [0, 2, 0, 2, 1, 1, 1, 1, 0, 2, 0, 2]  # 0 = M, 1 = E, 2 = S

default_orientation = [
    0,  # Piece is in its home slice
    5,  # E <-> M
    4,  # M <-> S
    1,  # E <-> S
]


class DisplayOption(Enum):
    ALL = 1
    NONE = 2
    BAD = 3


class CubeViz():
    """Cube visualizer"""
    def __init__(
            self,
            attempt: Attempt,
            opacity=.93,  # Set the opacity for the colors
    ):
        # Set up the display
        self.opacity = opacity

        self.attempt = attempt
        self.attempt.add_cube_listener(self.refresh)

        # Initial camera position
        self.init_camera(0, -10, 6)
        self.view_y = -math.pi / 6
        self.view_x = 0

        self.corner_display = DisplayOption.BAD
        self.edge_display = DisplayOption.BAD
        self.center_display = DisplayOption.ALL

        self.colors = [(1, 1, 1, .2)] * 54

    def init_camera(self, x, y, z):
        self.camera = np.array([x, y, z])

        z_axis = np.array([0, 0, 1])
        screen_x_dir = np.cross(-self.camera, z_axis)
        self.screen_x_dir = screen_x_dir / np.linalg.norm(screen_x_dir)
        screen_y_dir = np.cross(self.camera, self.screen_x_dir)
        self.screen_y_dir = screen_y_dir / np.linalg.norm(screen_y_dir)

    def should_draw_edge(self, pos_id, face):
        if self.edge_display == DisplayOption.ALL:
            return True
        elif self.edge_display == DisplayOption.NONE:
            return False
        else:
            return self.attempt.solution.step_info.should_draw_edge(self.attempt.cube, pos_id, face)

    def should_draw_corner(self, pos_id, face):
        if self.corner_display == DisplayOption.ALL:
            return True
        elif self.corner_display == DisplayOption.NONE:
            return False
        else:
            return self.attempt.solution.step_info.should_draw_corner(self.attempt.cube, pos_id,
                                                                      face)

    def refresh(self):
        self.colors = [(1, 1, 1, .2)] * 54
        if self.center_display != DisplayOption.NONE:
            self.colors[4] = WHITE + (self.opacity,)
            self.colors[13] = ORANGE + (self.opacity,)
            self.colors[22] = GREEN + (self.opacity,)
            self.colors[31] = RED + (self.opacity,)
            self.colors[40] = BLUE + (self.opacity,)
            self.colors[49] = YELLOW + (self.opacity,)
        corners = self.attempt.cube.corners()
        for i in range(0, 8):
            piece_id, orientation = corners[i]
            for side in range(0, 3):
                if not self.should_draw_corner(i, side):
                    continue
                face = (side + 3 - orientation) % 3
                self.colors[corner_position_facelets[i][side]] = (
                        corner_piece_colors[piece_id][face] +
                        (self.opacity,))
        edges = self.attempt.cube.edges()
        for i in range(0, 12):
            piece_id, piece_orientation = edges[i]
            orientation = default_orientation[home_slice[piece_id] ^ home_slice[i]]
            flipped = 0 if piece_orientation == orientation else 1
            for side in range(0, 2):
                if not self.should_draw_edge(i, side):
                    continue
                self.colors[edge_position_facelets[i][side]] = edge_piece_colors[edges[i][0]][
                                                                   (side + flipped) % 2] + (
                                                                   self.opacity,)

    def draw_facelet(self, painter, w, h, rotation_matrix, x, y, z, color, axis):
        # Define the vertices of the square face based on axis

        vertex_center = np.array([x, y, z])
        # Transform vertices to world coordinates
        transformed_vertices = [rotation_matrix @ (v + vertex_center) for v in FACELET_VERTICES[axis]]

        scale_factor = min(w, h) * np.linalg.norm(self.camera) / 5
        screen_vertices = [
            (w / 2 + scale_factor * np.dot(v, self.screen_x_dir) / np.linalg.norm(v-self.camera) ,
             h / 2 - scale_factor * np.dot(v, self.screen_y_dir) / np.linalg.norm(v-self.camera) )
            for v in transformed_vertices
        ]

        # Enable antialiasing for smoother edges
        painter.setRenderHint(QPainter.Antialiasing)

        # Create a semi-transparent pen with alpha channel (RGBA)
        qcol = QColor(int(color[0] * 255), int(color[1] * 255), int(color[2] * 255), int(color[3] * 255))
        pen = QPen(QColor(255,255,255,16), 1)
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
        painter.fillRect(0, 0, w, h, QColor(int(BACKGROUND * 255), int(BACKGROUND * 255), int(BACKGROUND * 255)))
        # Apply rotation
        q = (Quaternion(axis=[1, 0, 0], angle=self.view_x) *
             Quaternion(axis=[0, 0, 1], angle=self.view_y) *
             rotation_for(self.attempt.solution.orientation))
        rotation_matrix = q.rotation_matrix

        # Order faces from back to front
        def distance(i):
            v_rotated = q.rotate([facelet_x[i], facelet_y[i], facelet_z[i]])
            return np.linalg.norm(v_rotated - self.camera)

        faces = [
            (range(9 * i, 9 * (i + 1)), distance(9 * i + 4)) for i in range(0, 6)
        ]
        faces.sort(key=lambda x: -x[1])
        faces = [f for f, d in faces]

        for face in faces:
            for i in face:
                self.draw_facelet(painter, w, h, rotation_matrix, facelet_x[i], facelet_y[i],
                                  facelet_z[i],
                                  self.colors[i], axis[i])

    def rotate(self, dx, dy=0):
        self.view_y += dx * .005
        self.view_x += dy * .005


def rotation_for(o: Orientation) -> Quaternion:
    # Return the quaternion that brings a default cube into the given orientation
    base = Orientation("u", "f")
    if o.top in "fb":
        ticks = AXIS_ROTATIONS["r"].index(o.top)
        base.x(ticks)
        q = Quaternion(axis=[1, 0, 0], angle=-math.pi / 2 * ticks)
    else:
        ticks = AXIS_ROTATIONS["f"].index(o.top)
        q = Quaternion(axis=[0, 1, 0], angle=math.pi / 2 * ticks)
        base.z(ticks)
    ticks = AXIS_ROTATIONS[base.top].index(o.front) - AXIS_ROTATIONS[base.top].index(base.front) + 4
    q = Quaternion(axis=[0, 0, 1], angle=-math.pi / 2 * ticks) * q
    return q


class CubeWidget(QWidget):
    """OpenGL widget that uses the CubeViz drawing methods"""

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
