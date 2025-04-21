import sys
import logging
import os
from enum import Enum

from OpenGL.GL import *
from OpenGL.GLU import *
import math
import numpy as np
from PyQt5 import Qt
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QSurfaceFormat
from PyQt5.QtWidgets import QOpenGLWidget

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
    """Visualize a cube in 3D space using pygame and OpenGL"""

    def __init__(
            self,
            attempt: Attempt,
            opacity=.8,  # Set the opacity for the colors
    ):
        # Set up the display
        self.opacity = opacity

        self.attempt = attempt
        self.attempt.add_cube_listener(self.refresh)

        # Initial camera position
        self.camera_x = 0.0
        self.camera_y = -10.0
        self.camera_z = 6.0
        self.view_angle = -math.pi / 6

        self.corner_display = DisplayOption.BAD
        self.edge_display = DisplayOption.BAD
        self.center_display = DisplayOption.ALL

        self.colors = [(1, 1, 1, .2)] * 54

    def initializeGL(self, width, height):
        """Initialize OpenGL settings"""
        glClearColor(BACKGROUND, BACKGROUND, BACKGROUND, 1)
        glEnable(GL_DEPTH_TEST)

        # Enable alpha blending
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_BLEND)

        # Set up the perspective
        self.resize(width, height)

    def resize(self, width, height):
        """Handle widget resize events"""
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(25, (width / height), 0.1, 50.0)

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
        elif self.corner_display ==DisplayOption.NONE:
            return False
        else:
            return self.attempt.solution.step_info.should_draw_corner(self.attempt.cube, pos_id, face)

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

    def draw_facelet(self, x, y, z, color, axis):
        glPushMatrix()
        glTranslatef(x, y, z)
        draw_grid = False

        # Draw a square face
        glBegin(GL_QUADS)
        if axis == 'xy':
            if draw_grid:
                glColor4f(0, 0, 0, color[3])
                glVertex3f(-0.5, -0.5, 0.0)
                glVertex3f(0.5, -0.5, 0.0)
                glVertex3f(0.5, 0.5, 0.0)
                glVertex3f(-0.5, 0.5, 0.0)
            glColor4fv(color)
            glVertex3f(-0.48, -0.48, 0.0)
            glVertex3f(0.48, -0.48, 0.0)
            glVertex3f(0.48, 0.48, 0.0)
            glVertex3f(-0.48, 0.48, 0.0)
        elif axis == 'xz':
            if draw_grid:
                glColor4f(0, 0, 0, color[3])
                glVertex3f(-0.5, 0.0, -0.5)
                glVertex3f(0.5, 0.0, -0.5)
                glVertex3f(0.5, 0.0, 0.5)
                glVertex3f(-0.5, 0.0, 0.5)
            glColor4fv(color)
            glVertex3f(-0.48, 0.0, -0.48)
            glVertex3f(0.48, 0.0, -0.48)
            glVertex3f(0.48, 0.0, 0.48)
            glVertex3f(-0.48, 0.0, 0.48)
        elif axis == 'yz':
            if draw_grid:
                glColor4f(0, 0, 0, color[3])
                glVertex3f(0.0, -0.5, -0.5)
                glVertex3f(0.0, 0.5, -0.5)
                glVertex3f(0.0, 0.5, 0.5)
                glVertex3f(0.0, -0.5, 0.5)
            glColor4fv(color)
            glVertex3f(0.0, -0.48, -0.48)
            glVertex3f(0.0, 0.48, -0.48)
            glVertex3f(0.0, 0.48, 0.48)
            glVertex3f(0.0, -0.48, 0.48)
        glEnd()

        glPopMatrix()

    def set_inverse(self, inverse: bool):
        self.inverse = inverse

    def update(self):
        self.refresh()

    def draw(self):
        # Clear the screen
        glClearColor(BACKGROUND, BACKGROUND, BACKGROUND, 1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Set camera position
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(self.camera_x, self.camera_y, self.camera_z,  # Camera position
                  0, 0, 0,  # Look at point
                  0, 1, 0)  # Up vector

        # Apply rotation
        qview = Quaternion(axis=[0, 0, 1], angle=self.view_angle)
        q = qview * rotation_for(self.attempt.solution.orientation)
        rotation_matrix = q.rotation_matrix

        # Order faces from back to front
        def distance(i):
            v_rotated = q.rotate([facelet_x[i], facelet_y[i], facelet_z[i]])
            return (v_rotated[0] - self.camera_x) ** 2 + \
                (v_rotated[1] - self.camera_y) ** 2 + \
                (v_rotated[2] - self.camera_z) ** 2

        faces = [
            (range(9 * i, 9 * (i + 1)), distance(9 * i + 4)) for i in range(0, 6)
        ]
        faces.sort(key=lambda x: -x[1])
        faces = [f for f, d in faces]

        # Update the GL matrix with the new rotation
        m = np.identity(4)
        m[:3, :3] = rotation_matrix

        # Convert to OpenGL format (column-major) and apply
        glPushMatrix()
        glMultMatrixf(m.T.flatten())

        for face in faces:
            for i in face:
                self.draw_facelet(facelet_x[i], facelet_y[i], facelet_z[i],
                                  self.colors[i], axis[i])

        glPopMatrix()

    def rotate(self, dx, dy=0):
        self.view_angle += dx * .005

def rotation_for(o: Orientation) -> Quaternion:
    # Return the quaternion that brings a default cube into the given orientation
    base = Orientation("u","f")
    if o.top in "fb":
        ticks = AXIS_ROTATIONS["r"].index(o.top)
        base.x(ticks)
        q = Quaternion(axis=[1, 0, 0], angle=-math.pi / 2 * ticks)
    else:
        ticks = AXIS_ROTATIONS["f"].index(o.top)
        q = Quaternion(axis=[0, 1, 0], angle=math.pi / 2 * ticks)
        base.z(ticks)
    ticks = AXIS_ROTATIONS[base.top].index(o.front) - AXIS_ROTATIONS[base.top].index(base.front) + 4
    q = Quaternion(axis=[0,0,1], angle=-math.pi / 2 * ticks) * q
    return q

class CubeWidget(QOpenGLWidget):
    """OpenGL widget that uses the CubeViz drawing methods"""

    def __init__(self, viz: CubeViz, parent=None):
        super(CubeWidget, self).__init__(parent)
        self.setMinimumSize(400, 400)

        # Set up the OpenGL format
        gl_format = QSurfaceFormat()
        gl_format.setVersion(2, 1)
        gl_format.setProfile(QSurfaceFormat.CompatibilityProfile)
        QSurfaceFormat.setDefaultFormat(gl_format)

        self.viz = viz
        self.viz.attempt.add_cube_listener(self.refresh)
        self.previous_solution = self.viz.attempt.solution

        # Set up a timer for animation/updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(30)  # 30ms refresh rate (approx 33 fps)

        # Mouse tracking
        self.setMouseTracking(True)
        self.last_mouse_pos = None
        self.dragging = False

    def refresh(self):
        # Repaint
        self.update()

    def initializeGL(self):
        """Initialize OpenGL settings"""
        self.viz.initializeGL(self.width(), self.height())

    def resizeGL(self, width, height):
        """Handle widget resize events"""
        self.viz.resize(width, height)

    def paintGL(self):
        """Render the OpenGL scene"""
        self.viz.draw()

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
            self.viz.rotate(dx)
            self.last_mouse_pos = event.pos()


