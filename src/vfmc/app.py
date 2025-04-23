import dataclasses
import os
import sys
import math
import logging
import traceback
import functools
from typing import Optional, List, Tuple
from importlib.metadata import version

from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
                             QLabel, QLineEdit, QPushButton,
                             QListWidget, QMessageBox, QSizePolicy, QStyledItemDelegate,
                             QListWidgetItem)
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QKeySequence

from vfmc.attempt import PartialSolution, Attempt
from vfmc.viz import CubeViz, DisplayOption, CubeWidget
from vfmc_core import Cube, Algorithm, StepInfo, scramble as gen_scramble

# Basic set of cube moves
MOVES = {
    "R", "U", "F", "L", "D", "B",
    "R'", "U'", "F'", "L'", "D'", "B'",
    "R2", "U2", "F2", "L2", "D2", "B2",
}

NEXT_STEPS = {
    ("eo", "ud"): [("dr", "fb"), ("dr", "rl")],
    ("eo", "rl"): [("dr", "ud"), ("dr", "fb")],
    ("eo", "fb"): [("dr", "ud"), ("dr", "rl")],
    ("dr", "ud"): [("htr", "ud")],
    ("dr", "rl"): [("htr", "rl")],
    ("dr", "fb"): [("htr", "fb")],
    ("htr", "ud"): [("fr", "ud")],
    ("htr", "rl"): [("fr", "rl")],
    ("htr", "fb"): [("fr", "fb")],
    ("fr", "ud"): [("slice", "ud")],
    ("fr", "fb"): [("slice", "fb")],
    ("fr", "rl"): [("slice", "rl")],
    ("slice", "ud"): [("finish", "")],
    ("slice", "fb"): [("finish", "")],
    ("slice", "rl"): [("finish", "")],
}

PREFERRED_AXIS = {
    ("eo", "ud"): (["fb", "rl"], ["ud"]),
    ("eo", "rl"): (["ud", "fb"], ["rl"]),
    ("eo", "fb"): (["ud", "rl"], ["fb"]),
    ("*", "ud"): (["ud"], ["fb", "rl"]),
    ("*", "fb"): (["fb"], ["ud", "rl"]),
    ("*", "rl"): (["rl"], ["fb", "ud"]),
    ("*", "*"): (["ud"], ["fb", "rl"]),
}

AXIS_ORIENTATIONS = {
    ("ud", "fb"): (0, 0, 0),
    ("ud", "rl"): (0, 0, -math.pi / 2),
    ("fb", "ud"): (math.pi / 2, 0, 0),
    ("fb", "rl"): (math.pi / 2, 0, -math.pi / 2),
    ("rl", "fb"): (0, -math.pi / 2, 0),
    ("rl", "ud"): (0, -math.pi / 2, math.pi / 2),
}

SOLUTION = Qt.UserRole
BOLD = Qt.UserRole + 1
STRIKETHROUGH = Qt.UserRole + 2
OLD_ALG = Qt.UserRole + 3


class AppWindow(QMainWindow):
    """Main window for cube exploration with PyQt"""

    def __init__(self):
        super(AppWindow, self).__init__()

        self.setWindowTitle("VFMC")
        self.resize(1200, 800)

        self.attempt = Attempt()
        self.attempt.add_cube_listener(self.refresh_current_solution)
        self.attempt.add_solution_listener(self.populate_saved_solutions)
        self.previous_solution = self.attempt.solution

        self.commands = Commands(self)
        self.command_history = [] # As entered by the user
        self.history_pointer = -1 # For traversing command history via up/down keys

        # Create central widget and main layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(2)  # Minimize spacing between components
        main_layout.setContentsMargins(4, 4, 4, 4)  # Minimize margins 
        self.setCentralWidget(central_widget)

        # Top section: cube widget + scramble/step info
        top_panel = QWidget()
        top_layout = QHBoxLayout(top_panel)
        main_layout.addWidget(top_panel)

        # Create a vertical layout for the GL widget and status labels
        gl_container = QWidget()
        gl_layout = QVBoxLayout(gl_container)
        gl_layout.setContentsMargins(0, 0, 0, 0)
        gl_layout.setSpacing(0)

        # OpenGL widget
        self.viz = CubeViz(self.attempt)
        self.gl_widget = CubeWidget(self.viz)
        gl_layout.addWidget(self.gl_widget)

        # Status labels below GL widget
        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(0)

        label_style = "background-color: #4d4d4d; color: white; font-weight: bold; font-size: 18px; padding: 5px;"
        # Left label - Step kind and variant
        self.step_label = QLabel("Step")
        self.step_label.setStyleSheet(label_style)
        self.step_label.setMinimumHeight(40)
        status_layout.addWidget(self.step_label, 1)  # Give it a stretch factor of 1

        # Inverse marker
        self.niss_label = QLabel("NISS")
        self.niss_label.setStyleSheet(label_style)
        self.niss_label.setAlignment(Qt.AlignCenter)
        self.niss_label.setMinimumHeight(40)
        status_layout.addWidget(self.niss_label, 1)  # Give it a stretch factor of 1

        # Right label - Case name
        self.case_label = QLabel("Case")
        self.case_label.setStyleSheet(label_style)
        self.case_label.setAlignment(Qt.AlignRight)
        self.case_label.setMinimumHeight(40)
        status_layout.addWidget(self.case_label, 1)  # Give it a stretch factor of 1

        gl_layout.addWidget(status_container)
        top_layout.addWidget(gl_container)

        # Scramble and step info panel (right of GL widget)
        info_panel = QWidget()
        info_layout = QVBoxLayout(info_panel)
        top_layout.addWidget(info_panel)

        current_container = QWidget()
        current_layout = QVBoxLayout(current_container)
        self.current_solution = CurrentSolutionWidget(self.attempt)
        current_layout.addWidget(self.current_solution)
        info_layout.addWidget(current_container)

        # Command input below the GL widget - with minimal spacing
        command_container = QWidget()
        command_container.setSizePolicy(QSizePolicy.Preferred,
                                        QSizePolicy.Minimum)  # Minimize vertical space
        command_layout = QHBoxLayout(command_container)
        command_layout.setContentsMargins(10, 0, 10, 0)  # Remove all margins
        command_layout.setSpacing(6)  # Minimal spacing between elements

        command_label = QLabel("Command:")
        self.command_input = QLineEdit()
        self.command_input.returnPressed.connect(self.execute_command)
        self.command_input.installEventFilter(self)
        help_button = QPushButton("Help")
        help_button.clicked.connect(self.show_help)

        command_layout.addWidget(command_label)
        command_layout.addWidget(self.command_input)
        command_layout.addWidget(help_button)
        main_layout.addWidget(command_container, 0)  # No vertical stretch

        # Status label with minimal spacing
        status_container = QWidget()
        status_container.setSizePolicy(QSizePolicy.Preferred,
                                       QSizePolicy.Minimum)  # Minimize vertical space
        status_layout = QVBoxLayout(status_container)
        status_layout.setContentsMargins(10, 0, 10, 0)  # No vertical margins
        status_layout.setSpacing(0)  # Remove spacing
        self.status_label = QLabel()
        self.status_label.setMaximumHeight(20)  # Limit the height
        status_layout.addWidget(self.status_label)
        main_layout.addWidget(status_container, 0)  # No vertical stretch

        # Solutions lists - make them expand to fill available vertical space
        solutions_container = QWidget()
        solutions_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        solutions_layout = QVBoxLayout(solutions_container)
        solutions_layout.setContentsMargins(10, 0, 10, 0)  # Remove margins
        solutions_layout.setSpacing(0)  # Remove vertical spacing

        # Create a horizontal layout for the solution lists
        solution_lists_layout = QHBoxLayout()
        solution_lists_layout.setSpacing(10)  # Add some spacing between columns

        self.step_order = ["eo", "dr", "htr", "fr", "slice", "finish"]
        self.solution_widgets = {}

        # Define colors for different states
        selection_color = "#22dd7c"
        active_selection_color = "#33ff9e"

        # Create a common stylesheet for all list widgets with focus-independent styling
        list_style = f"""
            /* Default appearance */
            QListWidget::item {{ 
                color: black;
                background-color: transparent;
            }}
            
            /* Basic selection style (blue) */
            QListWidget::item:selected {{ 
                background-color: {selection_color}; 
                color: black;
            }}
            
            /* Keep selection color even when widget loses focus */
            QListWidget::item:selected:!active {{ 
                background-color: {active_selection_color}; 
                color: black;
            }}
        """

        def build_solution_widget(kind: str, label: Optional[str] = None):
            container = QWidget()
            container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 10, 10)
            layout.setSpacing(2)
            label = label or kind.upper()
            layout.addWidget(QLabel(f"{label}:"))
            list = QListWidget()
            list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            list.itemDoubleClicked.connect(self.activate_item)
            list.itemClicked.connect(lambda item: self.item_selected(list))
            list.itemSelectionChanged.connect(lambda: self.item_selected(list))
            list.installEventFilter(self)
            list.setStyleSheet(list_style)
            list.setItemDelegate(SolutionItemRenderer())
            list.setProperty("kind", kind)
            layout.addWidget(list)
            self.solution_widgets[kind] = list
            return container

        # Solution List Widgets
        solution_lists_layout.addWidget(build_solution_widget("eo"))
        solution_lists_layout.addWidget(build_solution_widget("dr"))
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        layout.addWidget(build_solution_widget("htr"))
        layout.addWidget(build_solution_widget("slice", "Slice"))
        solution_lists_layout.addWidget(container)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        layout.addWidget(build_solution_widget("fr"))
        layout.addWidget(build_solution_widget("finish", "Finish"))
        solution_lists_layout.addWidget(container)

        self.current_solution.installEventFilter(self)

        solutions_layout.addLayout(solution_lists_layout)
        main_layout.addWidget(solutions_container,
                              1)  # Add stretch factor of 1 to expand vertically

        # Set initial scramble
        self.commands.execute("scramble")

        # Set focus to command input
        self.command_input.setFocus()

    def refresh_current_solution(self):
        self.current_solution.refresh()

        # Update step name
        sol = self.attempt.solution
        step_text = f"{sol.kind}{sol.variant}"
        self.step_label.setText(step_text)

        # Update NISS label
        self.niss_label.setText("(inverse)" if self.attempt.inverse else "")

        # Update case name
        if not sol.step_info.is_solved(self.attempt.cube):
            case_text = sol.step_info.case_name(self.attempt.cube)
            self.case_label.setText(case_text)
        else:
            self.case_label.setText("")

    def populate_saved_solutions(self):
        solutions = self.attempt.solutions_by_kind()

        for kind, list in self.solution_widgets.items():
            list.clear()
            for i, sol in enumerate(solutions.get(kind, [])):
                padding = "   " if i < 9 else ("  " if i < 99 else " ")
                list.addItem(f"{i + 1}.{padding}{self.attempt.to_str(sol)}")
                item = list.item(list.count() - 1)
                item.setData(SOLUTION, sol)

        self.format_saved_solutions()

    def format_saved_solutions(self):
        active = self.attempt.solution.substeps()
        active_list_item = None

        for kind in reversed(self.step_order):
            list = self.solution_widgets[kind]
            list.blockSignals(True)
            matched = False
            for i in range(list.count()):
                item = list.item(i)
                sol = item.data(SOLUTION)
                item.setData(BOLD, sol in active and not matched)
                matched = matched or item.data(BOLD)
                item.setData(STRIKETHROUGH, self.attempt.is_done(sol))
                item.setSelected(False)
                if item.data(BOLD) and not active_list_item:
                    active_list_item = list, item
            list.blockSignals(False)
            list.update()
        if active_list_item:
            list, item = active_list_item
            item.setSelected(True)
            list.setCurrentItem(item)
            self.item_selected(list)

    def set_scramble(self, scramble: str):
        """Set the cube to a specific scramble"""
        for w in self.solution_widgets.values():
            w.clear()
        self.attempt.set_scramble(scramble)

    def set_status(self, status: str):
        self.status_label.setText(status)

    def _append_moves(self, moves_str):
        """Append moves to the current solution"""
        moves = moves_str.split(" ")
        inverse = self.attempt.inverse

        sol = self.attempt.solution

        if sol.alg.len() > 0:
            if not self.attempt.append_moves(moves, inverse):
                self.set_status(
                    f"{moves} not allowed after {sol.previous.kind}{sol.previous.variant}")
        else:
            if not self.attempt.append_moves(moves, inverse):
                assert sol.previous is not None
                if sol.previous.allows_moves(moves_str):
                    alg = sol.previous.alg
                    self.attempt.back()
                    self.attempt.append_moves(alg.normal_moves(), False)
                    self.attempt.append_moves(alg.inverse_moves(), True)
                    self.attempt.append_moves(moves, inverse)
                else:
                    self.set_status(
                        f"{moves_str} not allowed after {sol.previous.kind}{sol.previous.variant}")

    def set_step(self, kind, variant) -> bool:
        """Change to a specific solving step"""
        step_info = StepInfo(kind, variant)
        sol = self.attempt.solution
        while sol.alg.len() == 0 and sol.previous:
            sol = sol.previous
        past_step_kinds = {s.kind for s in sol.substeps()[:-1]}
        if kind in past_step_kinds:
            # Moving backward
            while sol.kind != kind:
                sol = sol.previous
            if sol.previous:
                sol = sol.previous
            else:
                sol = PartialSolution()
            self.attempt.solution = sol
            self.attempt.advance_to(kind, variant)
            return True
        elif kind == sol.kind:
            self.attempt.back()
            self.attempt.advance_to(kind, variant)
            return True
        else:
            if step_info.is_eligible(self.attempt.cube):
                self.attempt.advance_to(kind, variant)
                return True
            else:
                self.set_status(f"Cube is not eligible for {kind}{variant}")
                return False

    def activate_item(self, item):
        sol = item.data(SOLUTION)
        index = self.attempt.solutions_by_kind()[sol.kind].index(sol) + 1
        # Execute via self.commands to get this into the history
        self.commands.execute(f'check("{sol.kind}",{index})')

    def scroll_to(self, solution: PartialSolution):
        w = self.solution_widgets[solution.kind]
        for i in range(0,w.count()):
            if w.item(i).data(SOLUTION) == solution:
                w.item(i).setSelected(True)
                w.setCurrentItem(w.item(i))
                w.scrollToItem(w.item(i))

    def item_selected(self, list_widget):
        selected_item = list_widget.currentItem()
        if not selected_item:
            return

        selected_step = selected_item.data(SOLUTION)

        for k, w in self.solution_widgets.items():
            w.blockSignals(True)
            w.clearSelection()
            w.setCurrentItem(None)
            w.setSelectionMode(QListWidget.ContiguousSelection)
            for i in range(w.count()):
                item = w.item(i)
                sol = item.data(SOLUTION)
                highlight = sol in selected_step.substeps() or selected_step in sol.substeps()
                item.setSelected(highlight)
                if highlight:
                    w.setCurrentItem(item)
            w.setSelectionMode(QListWidget.SingleSelection)
            w.blockSignals(False)
        for _, w in self.solution_widgets.items():
            w.scrollToItem(w.currentItem())

    def solve(self, num_solutions: int):
        """Find and save solutions for the current step"""
        if num_solutions > 50:
            self.set_status("Maximum of 50 solutions per solve")
            return
        sol = self.attempt.solution
        on_inverse = self.attempt.inverse
        if on_inverse:
            self.attempt.niss()
        existing = set(str(s) for s in self.attempt.solutions_for_step(sol.kind, sol.variant))
        self.set_status(f"Finding solutions for {sol.kind}{sol.variant}...")
        algs = sol.step_info.solve(self.attempt.cube, len(existing) + num_solutions)
        solutions = []
        for alg in algs:
            base_alg = Algorithm(str(sol.alg))
            base_alg.merge(alg)
            s = PartialSolution(
                kind=sol.kind,
                variant=sol.variant,
                previous=sol.previous,
                alg=sol.alg.merge(alg)
            )
            if str(s) not in existing:
                solutions.append(s)
            if len(solutions) >= num_solutions:
                break
        if solutions:
            self.set_status(f"Found {len(solutions)} solution{'' if len(solutions) == 1 else 's'}")
            self.attempt.save_solutions(solutions)
            self.check_solution(solutions[-1])
        else:
            self.set_status(f"No solutions found for {sol.kind}{sol.variant}")
        if on_inverse:
            self.attempt.niss()

    def execute_command(self):
        cmd = self.command_input.text().strip()
        self.command_history.append(cmd)
        self.history_pointer = len(self.command_history) - 1
        self.commands.execute(cmd)
        self.command_input.clear()

    def eventFilter(self, obj, event):
        """Handle keyboard events for navigating between solution lists"""
        # Check if this is a key event for one of our solution lists
        if event.type() == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_Return or key == Qt.Key_Enter:
                if obj in list(self.solution_widgets.values()):
                    kind = obj.property("kind")
                    if not kind:
                        return False
                    # Enter key to check the currently selected solution
                    if obj.currentItem():
                        self.activate_item(obj.currentItem())
                        return True
            elif (key == Qt.Key_Tab or key == Qt.Key_Backtab):
                # Handle Tab and Shift+Tab to move between solution lists
                if obj not in self.solution_widgets.values() and obj != self.command_input:
                    return False

                def select_widget(widget):
                    if widget.count():
                        widget.clearSelection()
                        widget.setCurrentItem(None)
                        selection = 0
                        for i in range(0, widget.count()):
                            if widget.item(i).data(SOLUTION) in self.attempt.solution.substeps():
                                selection = i
                                break
                        widget.setCurrentItem(widget.item(selection))
                        widget.setFocus()
                        widget.update()
                        return True
                    else:
                        self.command_input.setFocus()
                        return True

                if obj == self.command_input:
                    if key == Qt.Key_Backtab:
                        self.current_solution.setCurrentItem(self.current_solution.item(self.current_solution.count() - 1))
                        self.current_solution.setFocus()
                        return True
                    for k in reversed(self.step_order):
                        w = self.solution_widgets[k]
                        for i in range(0, w.count()):
                            if w.item(i).data(SOLUTION) in self.attempt.solution.substeps():
                                return select_widget(w)
                    return select_widget(self.solution_widgets["eo"])
                index = self.step_order.index(obj.property("kind"))
                if key == Qt.Key_Backtab:
                    if index == 0:
                        self.command_input.setFocus()
                        return True
                    else:
                        next_index = index
                        while True:
                            next_index = (next_index - 1) % len(self.step_order)
                            widget = self.solution_widgets[self.step_order[next_index]]
                            if next_index == 0 or widget.count() > 0:
                                break
                        return select_widget(widget)
                else:
                    if index == len(self.step_order) - 1:
                        self.command_input.setFocus()
                        return True
                    else:
                        next_index = (index + 1) % len(self.step_order)
                        return select_widget(self.solution_widgets[self.step_order[next_index]])
            elif (obj == self.command_input and key == Qt.Key_Up):
                if self.history_pointer < 0:
                    return True
                previous_command = self.command_history[self.history_pointer]
                self.command_input.setText(previous_command)
                self.history_pointer = max(0, self.history_pointer - 1)
                return True
            elif (obj == self.command_input and key == Qt.Key_Down):
                self.history_pointer = min(self.history_pointer+1, len(self.command_history))
                previous_command = ""
                if self.history_pointer < len(self.command_history)-1:
                    previous_command = self.command_history[self.history_pointer+1]
                self.command_input.setText(previous_command)
                self.history_pointer = min(self.history_pointer, len(self.command_history)-1)
                return True
            elif (obj == self.command_input and (event.modifiers() & Qt.ControlModifier or event.modifiers() & Qt.MetaModifier) and key == Qt.Key_Z):
                self.commands.undo()
                return True

        return super().eventFilter(obj, event)

    def check_solution(self, solution):
        """Load a selected solution"""
        self.attempt.set_solution(solution)
        key = (self.attempt.solution.kind, self.attempt.solution.variant)
        next_steps = NEXT_STEPS.get(key)
        if next_steps:
            self.attempt.advance_to(*next_steps[0])
        self.command_input.setFocus()
        self.format_saved_solutions()

    def show_help(self):
        """Show help popup with commands organized by section"""
        help_dialog = QMessageBox(self)
        help_dialog.setWindowModality(Qt.NonModal)
        help_dialog.setWindowTitle("VFMC help")

        # Generate help text by inspecting Commands methods
        commands = []
        for name in dir(self.commands):
            if name.startswith('_'):
                continue
            attr = getattr(self.commands, name)
            if callable(attr):
                commands.append((name, attr))

        help_file = os.path.join(os.path.dirname(__file__), "help.html")
        with open(help_file, "r") as f:
            help_dialog.setInformativeText(f.read())

        help_dialog.setText(f"Welcome to VFMC v{version('vfmc')}")
        help_dialog.setStandardButtons(QMessageBox.Ok)
        help_dialog.show()
        self.command_input.setFocus()


def main():
    # Create the Qt Application
    app = QApplication(sys.argv)
    window = AppWindow()
    window.show()

    # Start the application
    sys.exit(app.exec_())


def vfmc_command(tag):
    """Decorator to categorize commands into sections for help text"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper.tag = tag
        return wrapper

    return decorator


class Commands:
    def __init__(self, window: AppWindow):
        self.window = window
        self.attempt = window.attempt
        self.command_history = []  # Commands that were executed
        self.history_pointer = -1

    def execute(self, raw_command):
        """Execute a command from the command input"""
        cmd = raw_command
        if not cmd:
            return

        try:
            self.window.set_status("")
            result = None
            # Check if it's a sequence of cube moves
            if all(m in MOVES for m in cmd.upper().split()):
                self.window._append_moves(cmd.upper())
            else:
                if cmd.endswith("'"):
                    cmd = cmd.replace("'", "_prime")
                # Assume it's a Python command
                if cmd.find("(") < 0:
                    cmd = f"{cmd}()"
                # Use locals and globals from this context
                local_vars = {"self": self}
                exec(f"result = self.{cmd}", globals(), local_vars)
                result = local_vars.get("result")
            if result is None:
                result = CommandResult(add_to_history=raw_command)
            if result.error is not None:
                self.window.set_status(f"Error: {result.error}")
            elif result.add_to_history is not None:
                self.command_history.append(result.add_to_history)
                self.history_pointer = len(self.command_history)-1
        except Exception as e:
            logging.error(traceback.format_exc())
            logging.error(sys.exc_info())
            if sum((1 for n in dir(self) if cmd.startswith(n))) == 0:
                self.window.set_status(f"No such command: {raw_command}")
            else:
                self.window.set_status(f"Error: {e}")

    def undo(self):
        if self.history_pointer < 0:
            return
        last_command = self.command_history[self.history_pointer]
        next_undo = self.history_pointer - 1
        if all(m in MOVES for m in last_command.upper().split()):
            inverse = str(Algorithm(last_command).inverted())
            self.execute(inverse)
        elif last_command == "niss":
            self.execute("niss")
        else:
            self.history_pointer = -1
            return
        self.history_pointer = max(0, next_undo)

    def display(
            self,
            corners: Optional[str] = None,
            edges: Optional[str] = None,
            centers: Optional[str] = None,
    ):
        try:
            display_corners = DisplayOption[corners.upper()] if corners else None
            display_edges = DisplayOption[edges.upper()] if edges else None
            display_centers = DisplayOption[centers.upper()] if centers else None
            if display_corners:
                self.window.viz.corner_display = display_corners
            if display_edges:
                self.window.viz.edge_display = display_edges
            if display_centers:
                self.window.viz.center_display = display_centers
            self.attempt.notify_cube_listeners()
            return CommandResult(add_to_history=None)
        except:
            return CommandResult(error=ValueError(f'Valid values for display are: "all", "none", or "bad"'),add_to_history=None)

    def x(self):
        self.attempt.solution.orientation.x(1)

    def x_prime(self):
        self.attempt.solution.orientation.x(3)

    def x2(self):
        self.attempt.solution.orientation.x(2)

    def y(self):
        self.attempt.solution.orientation.y(1)

    def y_prime(self):
        self.attempt.solution.orientation.y(3)

    def y2(self):
        self.attempt.solution.orientation.y(2)

    def z(self):
        self.attempt.solution.orientation.z(1)

    def z_prime(self):
        self.attempt.solution.orientation.z(3)

    def z2(self):
        self.attempt.solution.orientation.z(2)

    def eoud(self):
        """Look for EO on UD axis"""
        self.window.set_step("eo", "ud")

    def eofb(self):
        """Look for EO on FB axis"""
        self.window.set_step("eo", "fb")

    def eorl(self):
        """Look for EO on RL axis"""
        self.window.set_step("eo", "rl")

    def drud(self):
        """Look for DR on UD axis"""
        self.window.set_step("dr", "ud")

    def drfb(self):
        """Look for DR on FB axis"""
        self.window.set_step("dr", "fb")

    def drrl(self):
        """Look for DR on RL axis"""
        self.window.set_step("dr", "rl")

    def htr(self):
        """Look for HTR"""
        sol = self.attempt.solution
        variant = ""
        for v in ["ud", "fb", "rl"]:
            if StepInfo("dr", v).is_solved(self.window.cube):
                variant = v
                break
        if variant:
            self.window.set_step("htr", variant)
        else:
            self.window.set_status("Cube is not eligible for HTR")

    def fr(self, axis=None):
        """Look for FR"""
        variant = axis
        if variant is None:
            variant = next(s.variant for s in self.attempt.solution.substeps() if s.kind == "dr")
        if variant is not None:
            self.window.set_step("fr", variant)
        else:
            self.window.set_status("""No DR step found. Specify axis="..." to set the FR axis""")

    def slice(self, axis=None):
        variant = next(s.variant for s in self.attempt.solution.substeps() if s.kind == "dr")
        if variant is not None:
            self.window.set_step("slice", variant)
        else:
            self.window.set_status("""No DR step found. Specify axis="..." to set the slice axis""")

    def finish(self, axis=None):
        self.window.set_step("finish", "")

    def niss(self):
        """Switch between normal and inverse scramble"""
        self.attempt.niss()

    def solve(self, num_solutions: int = 1):
        """Find and save solutions for the current step"""
        self.window.solve(num_solutions)

    def comment(self, s: str):
        sol = self.attempt.solution
        if sol.alg.len() == 0:
            sol = sol.previous
        if not sol:
            return
        self.attempt.set_comment(sol, s)
        for kind in reversed(self.window.step_order):
            widget = self.window.solution_widgets[kind]
            for i in range(widget.count()):
                item = widget.item(i)
                if item.data(SOLUTION) == sol:
                    padding = "   " if i < 9 else ("  " if i < 99 else " ")
                    item.setText(f"{i + 1}.{padding}{self.attempt.to_str(sol)}")
                    return

    def done(self):
        sol = self.attempt.solution
        self.attempt.toggle_done(sol)
        self.window.format_saved_solutions()

    def save(self):
        """Save this algorithm and start a new one"""
        sol = self.attempt.solution
        if not sol.step_info.is_solved(self.attempt.cube):
            if sol.kind == "" or sol.previous is None:
                self.window.set_status("Complete at least one step before saving")
                return
            partial = PartialSolution(
                kind=sol.previous.kind,
                variant=sol.previous.variant,
                previous=sol.previous.previous,
                alg=sol.previous.alg.merge(sol.alg),
            )
            options = NEXT_STEPS.get((partial.kind, partial.variant), [])
            case = sol.step_info.case_name(self.attempt.cube)
            comment = f"{sol.kind}{sol.variant}-{case}" if len(options) > 1 else case
            self.attempt.save_solution(partial)
            self.attempt.set_comment(partial, comment)
            self.window.populate_saved_solutions()
            self.window.scroll_to(partial)
            return
        self.attempt.save()
        next_steps = NEXT_STEPS.get((sol.kind, sol.variant))
        if next_steps is not None and len(next_steps) == 1:
            self.attempt.advance_to(*next_steps[0])
        else:
            self.reset()

    def reset(self):
        """Reset the cube to the beginning of the current step"""
        self.attempt.reset()

    def back(self):
        """Go back to the previous step"""
        self.attempt.back()
        self.window.format_saved_solutions()

    def check(self, kind: str, index: int):
        k = kind.lower()
        if k not in self.attempt.solutions_by_kind():
            self.window.set_status(f"Bad step type: {kind}")
            return
        solutions = self.attempt.solutions_by_kind()[kind.lower()]
        if index < 1 or index > len(solutions):
            self.window.set_status(f"Couldn't find {kind} #{index}")
            return
        self.window.check_solution(solutions[index - 1])

    def scramble(self, scramble: str = None):
        """
        <br>Use scramble(\"...\") to initialize with the specified scramble
        <br>or omit the parentheses to generate a new random scramble
        """
        if scramble is None:
            wrapper = Algorithm("R' U' F")
            scramble = str(wrapper.merge(Algorithm(gen_scramble())).merge(wrapper))
        self.window.set_scramble(scramble)
        return CommandResult(add_to_history=f'scramble("{scramble}")')

    def save_session(self, filename):
        try:
            with open(filename, "w") as f:
                f.writelines("\n".join(self.command_history))
            self.window.set_status(f"Saved session to {filename}")
            return CommandResult(add_to_history=None)
        except Exception as e:
            self.window.set_status(f"Unable to save to {filename}: {e}")
            return CommandResult(error=e, add_to_history=None)

    def load_session(self, filename):
        h = self.command_history
        try:
            self.command_history = []
            with open(filename, "r") as f:
                for cmd in f.readlines():
                    self.execute(cmd.strip())
            self.window.set_status(f"Loaded '{filename}'")
            return CommandResult(add_to_history=None)
        except Exception as e:
            self.command_history = h
            self.window.set_status(f"Unable to load '{filename}': {e}")
            return CommandResult(error=e, add_to_history=None)


class SolutionItemRenderer(QStyledItemDelegate):
    def __init__(self):
        super(QStyledItemDelegate, self).__init__()

    def initStyleOption(self, option, item):
        # Override style for the active solution
        super().initStyleOption(option, item)

        if item.data(STRIKETHROUGH):
            option.font.setStrikeOut(True)
        if item.data(BOLD):
            option.font.setBold(True)

class CurrentSolutionWidget(QListWidget):
    def __init__(self, attempt: Attempt):
        super().__init__()
        self.attempt = attempt
        self.ignore_updates = False
        self.current_editor = None
        self.originalKeyPress = None
        self.original_alg = None
        self.setSelectionMode(QListWidget.ContiguousSelection)
        self.setStyleSheet("font-size: 16px;")
        self.setEditTriggers(QListWidget.DoubleClicked)

    def refresh(self):
        if self.ignore_updates:
            return
        self.clear()
        self.addItem(self.attempt.scramble)
        self.addItem("")
        for step in self.attempt.solution.substeps():
            line = f"{step.alg}"
            if step.kind != "":
                if step.step_info.is_solved(self.attempt.cube):
                    line = f"{self.attempt.to_str(step)}"
                else:
                    line = f"{line}{'( )' if step.alg.len() == 0 and self.attempt.inverse else ''} // {step.kind}{step.variant}-{step.step_info.case_name(self.attempt.cube)} ({step.full_alg().len()})"
            item = QListWidgetItem(line)
            self.addItem(item)
        last_item = self.item(self.count()-1)
        last_item.setFlags(last_item.flags() | Qt.ItemIsEditable)
        last_item.setData(OLD_ALG, self.attempt.solution.alg)

    def edit(self, index, trigger, event):
        result = super().edit(index, trigger, event)
        if result:
            editor = self.indexWidget(index)
            if editor:
                self.current_editor = editor
                text = editor.text().split("//")[0].strip()
                editor.setText(text)
                if ")" in text:
                    editor.setCursorPosition(text.index(")"))
                self.original_alg = self.attempt.solution.alg
                self.current_editor.textEdited.connect(self.alg_updated)
        return result

    def alg_updated(self):
        if not self.current_editor:
            return
        edited_text = self.current_editor.text().split("//")[0].strip()
        if "(" in edited_text and ")" not in edited_text:
            return
        try:
            alg = Algorithm(edited_text)
            self.attempt.solution.alg = alg
            self.ignore_updates = True
            self.attempt.update_cube()
            self.ignore_updates = False
        except:
            pass

    def closeEditor(self, editor, hint):
        # Called when editing is finished
        if self.original_alg and self.parent() and self.parent().window():
            self.blockSignals(True)
            # Reset solution to original state, before we started editing
            current_alg = self.attempt.solution.alg
            self.attempt.solution.alg = self.original_alg

            # To properly populate the history, execute the moves done in the editor
            net_alg = self.original_alg.inverted().merge(current_alg)
            commands = self.parent().window().commands
            if net_alg.normal_moves():
                if self.attempt.inverse:
                    commands.execute("niss")
                commands.execute(" ".join(net_alg.normal_moves()))
            if net_alg.inverse_moves():
                if not self.attempt.inverse:
                    commands.execute("niss")
                commands.execute(" ".join(net_alg.inverse_moves()))
            self.parent().window().command_input.setFocus()
            self.blockSignals(False)

        self.current_editor = None
        self.original_alg = None
        super().closeEditor(editor, hint)
        self.refresh()


# Override key event to handle copy and editing
    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Copy):
            selected_items = self.selectedItems()
            if selected_items:
                clipboard_text = "\n".join(item.text() for item in selected_items)
                QApplication.clipboard().setText(clipboard_text)
        elif event.key() in {Qt.Key_Enter, Qt.Key_Return, Qt.Key_Delete, Qt.Key_Backspace}:
            # Enter key starts editing the current item if any
            current_item = self.currentItem()
            if current_item:
                self.editItem(current_item)
        else:
            super().keyPressEvent(event)  # Default behavior for other keys


@dataclasses.dataclass
class CommandResult:
    error: Optional[Exception] = None
    add_to_history: Optional[str] = None


if __name__ == "__main__":
    # Configure logging
    logfile = os.path.expanduser("~/vfmc.log")
    logging.basicConfig(
        filename=logfile, filemode="w",
        level=logging.DEBUG,
        format='%(levelname)s - %(message)s'
    )

    # Figure out the application bundle path
    if getattr(sys, 'frozen', False):
        # We're running from a PyInstaller bundle
        bundle_dir = os.path.dirname(sys.executable)
        logging.debug(f"Running bundle from {bundle_dir}")
        # For apps launched from Finder, we need to set the working directory
        # to the bundle's MacOS directory (where the executable lives)
        if os.path.basename(bundle_dir) == 'MacOS':
            os.chdir(os.path.dirname(os.path.dirname(bundle_dir)))  # Go up to the .app level
    main()
