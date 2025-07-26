import os
import sys
import math
import logging
import traceback
import re
from dataclasses import dataclass
from functools import cached_property
from typing import List, Set, Optional
from importlib.metadata import version

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QListWidget,
    QMessageBox,
    QSizePolicy,
    QStyledItemDelegate,
    QListWidgetItem,
    QAction,
    QFileDialog,
    QInputDialog,
    QDialog,
    QScrollArea,
)
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QKeySequence

from vfmc import catch_errors, catch_and_return
from vfmc.attempt import PartialSolution, Attempt, step_name
from vfmc import prefs
from vfmc.palette import Palette
from vfmc.prefs import preferences, SortOrder
from vfmc.viz import CubeViz, CubeWidget
from vfmc_core import Cube, Algorithm, StepInfo, scramble as gen_scramble

# Basic set of cube moves
MOVE_REGEX = r"[rRuUfFlLdDbB '2]*"

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
PRIORITY = Qt.UserRole + 3


class AppWindow(QMainWindow):
    """Main window for cube exploration with PyQt"""

    def __init__(self):
        super(AppWindow, self).__init__()

        self.setWindowTitle("VFMC")
        self.resize(1200, 800)

        self.attempt = Attempt()
        self.attempt.add_saved_solution_listener(self.populate_saved_solutions)
        self.attempt.add_solution_attribute_listener(self.format_saved_solutions)
        self.previous_solution = self.attempt.solution

        self.commands = Commands(self)
        self.command_history = []  # As entered by the user
        self.history_pointer = -1  # For traversing command history via up/down keys

        self.step_order = ["eo", "dr", "htr", "fr", "finish", "insertions"]

        self._create_menus()

        # Create GUI controls
        central_widget = self._empty_container(QVBoxLayout())
        central_widget.layout().setSpacing(4)
        central_widget.layout().setContentsMargins(10, 10, 10, 10)
        self.setCentralWidget(central_widget)
        w = self._empty_container(QHBoxLayout())
        w.layout().setContentsMargins(10, 0, 10, 0)
        w.layout().setSpacing(10)
        w.layout().addWidget(self.cube_widget)
        w.layout().addWidget(self.current_solution_scroll_widget)
        r2 = self._empty_container(QHBoxLayout())
        v = self._empty_container(QVBoxLayout())
        v.layout().addWidget(self.text_input_widget)
        v.layout().addWidget(self.status_widget)
        r2.layout().addWidget(v)
        r2.layout().addWidget(self.gui_commands_widget)
        central_widget.layout().addWidget(w)
        central_widget.layout().addWidget(r2)
        central_widget.layout().addWidget(self.solutions_widget, 1)

        # Set initial scramble
        self.commands.execute("scramble")

        def update():
            if preferences.sort_order != self.attempt._sort_order:
                self.commands.execute(
                    f'sort("{preferences.sort_order.key}",{preferences.sort_order.group_by_axis})'
                )

        preferences.add_listener(update)

        # Set focus to command input
        self.command_input.setFocus()

    @cached_property
    def cube_widget(self) -> QWidget:
        # Cube visualization
        cube_widget = QWidget()
        cube_widget.setLayout(QVBoxLayout())
        cube_widget.layout().setContentsMargins(0, 0, 0, 0)
        cube_widget.layout().setSpacing(0)

        # Graphical Cube
        self.viz = CubeViz(self.attempt)
        self.cube_viz_widget = CubeWidget(self.viz)
        cube_widget.layout().addWidget(self.cube_viz_widget)

        # Status labels below cube graphics
        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(0)

        # Left label - Step kind and variant
        step_label = QLabel("Step")
        step_label.setMinimumHeight(40)
        status_layout.addWidget(step_label, 1)  # Give it a stretch factor of 1

        # Inverse marker
        niss_label = QLabel("NISS")
        niss_label.setAlignment(Qt.AlignCenter)
        niss_label.setMinimumHeight(40)
        status_layout.addWidget(niss_label, 1)  # Give it a stretch factor of 1

        # Right label - Case name
        case_label = QLabel("Case")
        case_label.setAlignment(Qt.AlignRight)
        case_label.setMinimumHeight(40)
        status_layout.addWidget(case_label, 1)  # Give it a stretch factor of 1

        def update_bg_color():
            bg = str(hex(preferences.background_color))[2:]
            text_color = 255 if preferences.background_color < 128 else 0
            tc = str(hex(text_color))[2:]
            label_style = f"background-color: #{bg}{bg}{bg}; color: #{tc}{tc}{tc}; font-weight: bold; font-size: 18px; padding: 5px;"
            step_label.setStyleSheet(label_style)
            niss_label.setStyleSheet(label_style)
            case_label.setStyleSheet(label_style)

        update_bg_color()
        preferences.add_listener(update_bg_color)

        def refresh():
            sol = self.attempt.solution
            step_text = f"{sol.kind}{sol.variant}"
            step_label.setText(step_text)

            # Update NISS label
            niss_label.setText("(inverse)" if self.attempt.inverse else "")
            # Update case name
            if not sol.step_info.is_solved(self.attempt.cube):
                case_text = sol.step_info.case_name(self.attempt.cube)
                case_label.setText(case_text)
            else:
                case_label.setText("")

        self.attempt.add_cube_listener(refresh)
        cube_widget.layout().addWidget(status_container)
        return cube_widget

    @cached_property
    def current_solution_widget(self) -> "CurrentSolutionWidget":
        w = CurrentSolutionWidget(self.attempt)
        w.installEventFilter(self)
        return w

    @cached_property
    def current_solution_scroll_widget(self):
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.current_solution_widget)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # Force scrollbars to be visible
        scroll_area.setStyleSheet(
            """
            QScrollBar:vertical {
                width: 16px;
                background: #f0f0f0;
            }
            QScrollBar:horizontal {
                height: 16px;
                background: #f0f0f0;
            }
        """
        )

        return scroll_area

    def _empty_container(self, layout) -> QWidget:
        w = QWidget()
        w.setLayout(layout)
        w.setContentsMargins(0, 0, 0, 0)
        w.layout().setContentsMargins(0, 0, 0, 0)
        w.layout().setSpacing(0)
        return w

    @cached_property
    def gui_commands_widget(self) -> QWidget:
        # GUI alternatives to typing commands
        def command_button(cmd: str, name: Optional[str] = None):
            if name is None:
                name = cmd
            b = QPushButton(name)

            @catch_errors
            def execute(*args, **kwargs):
                self.commands.execute(cmd)

            b.clicked.connect(execute)
            return b

        step_selector = QComboBox()
        step_selector.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        step_selector.addItems(
            [
                "",
                "eofb",
                "eorl",
                "eoud",
                "drud",
                "drrl",
                "drfb",
                "htr",
                "fr",
                "finish",
                "insertions",
            ]
        )
        step_selector.setCurrentText("")

        @catch_errors
        def selection_changed(*args, **kwargs):
            text = step_selector.currentText()
            if text:
                self.commands.execute(text)

        step_selector.currentIndexChanged.connect(selection_changed)

        solve_button = QPushButton("solve")
        solve_count = QComboBox()
        solve_count.addItems([str(i) for i in range(1, 21)])

        @catch_errors
        def solve(*args, **kwargs):
            self.commands.execute(f"solve({solve_count.currentIndex()+1})")

        solve_button.clicked.connect(solve)

        gui_widget = self._empty_container(QHBoxLayout())

        w = self._empty_container(QVBoxLayout())
        w.layout().setAlignment(Qt.AlignLeft)
        w.layout().addWidget(step_selector)

        # Preferences button
        pref_button = QPushButton("Display Preferences")

        @catch_errors
        def show(*args, **kwargs):
            prefs.show_dialog(self)

        pref_button.clicked.connect(show)
        w.layout().addWidget(pref_button)

        gui_widget.layout().addWidget(w)

        gui_widget.layout().addWidget(QWidget(), 1)
        gui_widget.layout().addWidget(solve_button)
        gui_widget.layout().addWidget(solve_count)

        w = self._empty_container(QVBoxLayout())
        w.layout().addWidget(command_button("save"))
        w.layout().addWidget(command_button("done"))
        gui_widget.layout().addWidget(w)
        gui_widget.layout().addWidget(QWidget(), 1)

        w = self._empty_container(QVBoxLayout())
        w.layout().addWidget(command_button("niss"))
        h = self._empty_container(QHBoxLayout())
        h.layout().addWidget(command_button("x"))
        h.layout().addWidget(command_button("y"))
        h.layout().addWidget(command_button("z"))
        w.layout().addWidget(h)

        gui_widget.layout().addWidget(w)

        valid_steps: Set[str] = set()

        def enable_items(box: QComboBox, enabled):
            for i in range(box.count()):
                item = box.model().item(i)
                if item.text() in enabled:
                    item.setFlags(item.flags() | Qt.ItemIsEnabled)
                else:
                    item.setFlags(item.flags() & ~Qt.ItemIsEnabled)

        def refresh():
            valid_steps.clear()
            for kind, variant in self.attempt.possible_steps_following("", ""):
                valid_steps.add(f"{kind}{variant}")
            for step in reversed(self.attempt.solution.substeps()):
                valid_steps.add(step_name(step.kind, step.variant))
                for kind, variant in self.attempt.possible_steps_following(
                    step.kind, step.variant
                ):
                    if step.step_info.is_eligible(self.attempt.cube):
                        valid_steps.add(step_name(kind, variant))
            current_step = step_name(
                self.attempt.solution.kind, self.attempt.solution.variant
            )
            enable_items(step_selector, valid_steps)
            step_selector.blockSignals(True)
            step_selector.setCurrentText(current_step)
            step_selector.blockSignals(False)

        self.attempt.add_solution_attribute_listener(refresh)

        return gui_widget

    @cached_property
    def text_input_widget(self) -> QWidget:
        # Text command input
        w = self._empty_container(QHBoxLayout())
        w.layout().setContentsMargins(10, 0, 10, 0)  # Remove all margins
        w.layout().setSpacing(6)

        command_label = QLabel("Command:")
        self.command_input = QLineEdit()
        self.command_input.setText("help")
        self.command_input.setSelection(0, 4)

        @catch_errors
        def execute(*args, **kwargs):
            self.execute_command()

        self.command_input.returnPressed.connect(execute)
        self.command_input.installEventFilter(self)

        w.layout().addWidget(command_label)
        w.layout().addWidget(self.command_input)

        return w

    @cached_property
    def status_widget(self) -> QWidget:
        self.status_label = QLabel()
        self.status_label.setContentsMargins(10, 0, 10, 0)
        return self.status_label

    @cached_property
    def solutions_widget(self) -> QWidget:
        # Lists of solutions for each step
        solutions_container = self._empty_container(QVBoxLayout())
        solutions_container.layout().setContentsMargins(10, 0, 10, 0)  # Remove margins

        solution_lists_layout = QHBoxLayout()
        solution_lists_layout.setSpacing(10)  # Add some spacing between columns

        self.solution_widgets = {}

        # Define colors for different states
        selection_color = "#22dd7c"
        active_selection_color = "#33ff9e"

        # Create a common stylesheet for all list widgets with focus-independent styling
        list_style = f"""
            /* Default appearance */
            QListWidget::item {{
                color: palette(text);
                background-color: transparent;
            }}

            /* Basic selection style (blue) */
            QListWidget::item:selected {{
                background-color: {selection_color};
                color: black
            }}

            /* Keep selection color even when widget loses focus */
            QListWidget::item:selected:!active {{
                background-color: {active_selection_color};
                color: black
            }}
        """

        def build_solution_widget(kind: str, label: Optional[str] = None):
            container = self._empty_container(QVBoxLayout())
            label = label or kind.upper()
            container.layout().addWidget(QLabel(f"{label}:"))
            list = QListWidget()
            list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            @catch_errors
            def activate(item, *args, **kwargs):
                self.activate_item(item)

            list.itemDoubleClicked.connect(activate)

            @catch_errors
            def selected(*args, **kwargs):
                self.item_selected(list)

            list.itemClicked.connect(selected)
            list.itemSelectionChanged.connect(selected)
            list.installEventFilter(self)
            list.setStyleSheet(list_style)
            list.setItemDelegate(SolutionItemRenderer())
            list.setProperty("kind", kind)
            container.layout().addWidget(list)
            self.solution_widgets[kind] = list
            return container

        # Solution List Widgets
        solution_lists_layout.addWidget(build_solution_widget("eo"))
        solution_lists_layout.addWidget(build_solution_widget("dr"))
        htr_slice = self._empty_container(QVBoxLayout())
        htr_slice.layout().addWidget(build_solution_widget("htr"))
        htr_slice.layout().addWidget(build_solution_widget("finish", "Finish"))
        solution_lists_layout.addWidget(htr_slice)
        fr_finish = self._empty_container(QVBoxLayout())
        fr_finish.layout().addWidget(build_solution_widget("fr"))
        fr_finish.layout().addWidget(build_solution_widget("insertions", "Insertions"))
        solution_lists_layout.addWidget(fr_finish)

        solutions_container.layout().addLayout(solution_lists_layout)

        return solutions_container

    def populate_saved_solutions(self):
        """Clear and refresh the saved solution steps"""
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
        """
        Apply formatting to the solutions in the solution widgets
        Bold for steps that are active
        Strikethrough for steps marked "done"
        """
        active = self.attempt.solution.substeps()
        active_list_item = None

        for kind in reversed(self.step_order):
            list = self.solution_widgets[kind]
            list.blockSignals(True)
            matched = False
            for i in range(list.count() - 1, -1, -1):
                item = list.item(i)
                sol = item.data(SOLUTION)
                item.setData(BOLD, sol in active and not matched)
                padding = "   " if i < 9 else ("  " if i < 99 else " ")
                item.setText(f"{i + 1}.{padding}{self.attempt.to_str(sol)}")
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

    def set_status(self, status: str):
        """Show user-relevant info"""
        self.status_label.setText(status)

    def _append_moves(self, moves_str):
        """Append moves to the current solution"""
        alg = Algorithm(moves_str)

        sol = self.attempt.solution

        if sol.alg.len() > 0:
            if not self.attempt.append(alg):
                self.set_status(
                    f"{alg} not allowed after {sol.previous.kind}{sol.previous.variant}"
                )
        else:
            if not self.attempt.append(alg):
                assert sol.previous is not None
                if sol.previous.allows_moves(alg):
                    previous_alg = sol.previous.alg
                    self.attempt.back()
                    was_inverse = self.attempt.inverse
                    self.attempt.set_inverse(False)
                    self.attempt.append(previous_alg)
                    self.attempt.append(alg)
                    self.attempt.set_inverse(was_inverse)
                else:
                    self.set_status(
                        f"{moves_str} not allowed after {sol.previous.kind}{sol.previous.variant}"
                    )

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
                inverse = self.attempt.inverse
                self.attempt.advance_to(kind, variant)
                self.attempt.set_inverse(inverse)
                return True
            else:
                self.set_status(f"Cube is not eligible for {kind}{variant}")
                return False

    def scroll_to(self, solution: PartialSolution):
        """Make sure the given solution is visible"""
        w = self.solution_widgets[solution.kind]
        for i in range(0, w.count()):
            if w.item(i).data(SOLUTION) == solution:
                w.item(i).setSelected(True)
                w.setCurrentItem(w.item(i))
                w.scrollToItem(w.item(i))

    def activate_item(self, item):
        """
        User has selected a step from one of the solution widgets
        Result of a double-click or hitting enter
        Load the solution step into the view
        """
        sol = item.data(SOLUTION)
        index = self.attempt.solutions_by_kind()[sol.kind].index(sol) + 1
        # Execute via self.commands to get this into the history
        self.commands.execute(f'check("{sol.kind}",{index})')

    def item_selected(self, list_widget):
        """
        User has highlighted a step from one of the solution widgets
        Result of a single-click or arrow key navigation
        Does not activate the step; only shows related steps in the other widgets
        """
        selected_item = list_widget.currentItem()
        if not selected_item:
            return

        selected_step = selected_item.data(SOLUTION)

        for k, w in self.solution_widgets.items():
            w.blockSignals(True)
            w.clearSelection()
            w.setCurrentItem(None)
            w.setSelectionMode(QListWidget.MultiSelection)
            for i in range(w.count()):
                item = w.item(i)
                sol = item.data(SOLUTION)
                highlight = (
                    sol in selected_step.substeps() or selected_step in sol.substeps()
                )
                item.setSelected(highlight)
                if highlight:
                    w.setCurrentItem(item)
            w.setSelectionMode(QListWidget.SingleSelection)
            w.blockSignals(False)
        for _, w in self.solution_widgets.items():
            if w != list_widget:
                w.scrollToItem(w.currentItem())

    def execute_command(self):
        cmd = self.command_input.text().strip()
        self.command_history.append(cmd)
        self.history_pointer = len(self.command_history) - 1
        self.commands.execute(cmd)
        self.command_input.clear()

    def eventFilter(self, obj, event):
        """Handle keyboard events for navigating between solution lists"""
        delegate = super()

        @catch_and_return(False)
        def handle(*args, **kwargs):
            if self.viz.handle_toggle_view_event(obj, event):
                return True
            # Check if this is a key event for one of our solution lists
            if event.type() == QEvent.KeyPress:
                key = event.key()
                if event.isAutoRepeat():
                    return False
                if key == Qt.Key_Return or key == Qt.Key_Enter:
                    if obj in list(self.solution_widgets.values()):
                        kind = obj.property("kind")
                        if not kind:
                            return False
                        # Enter key to check the currently selected solution
                        if obj.currentItem():
                            self.activate_item(obj.currentItem())
                            return True
                    return False
                elif key == Qt.Key_Delete or key == Qt.Key_Backspace:
                    if obj in list(self.solution_widgets.values()):
                        kind = obj.property("kind")
                        if not kind:
                            return False
                        # Forget the selected solution
                        if obj.currentItem():
                            sol = obj.currentItem().data(SOLUTION)
                            index = (
                                self.attempt.solutions_by_kind()[sol.kind].index(sol)
                                + 1
                            )
                            self.commands.execute(f'forget("{sol.kind}",{index})')
                            return True
                    return False
                elif key == Qt.Key_Tab or key == Qt.Key_Backtab:
                    # Handle Tab and Shift+Tab to move between solution lists
                    if (
                        obj not in self.solution_widgets.values()
                        and obj != self.command_input
                    ):
                        return False

                    def select_related_solution(widget, sol):
                        if widget.count():
                            widget.clearSelection()
                            widget.setCurrentItem(None)
                            selection = 0
                            for i in range(0, widget.count()):
                                if (
                                    widget.item(i).data(SOLUTION) in sol.substeps()
                                    or sol in widget.item(i).data(SOLUTION).substeps()
                                ):
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
                        # Shift-tab navigates to current_solution_widget
                        if key == Qt.Key_Backtab:
                            self.current_solution_widget.setCurrentItem(
                                self.current_solution_widget.item(
                                    self.current_solution_widget.count() - 1
                                )
                            )
                            self.current_solution_widget.setFocus()
                            return True
                        # Otherwise navigate to the last active step
                        for k in reversed(self.step_order):
                            w = self.solution_widgets[k]
                            for i in range(0, w.count()):
                                sol = w.item(i).data(SOLUTION)
                                if sol in self.attempt.solution.substeps():
                                    return select_related_solution(w, sol)
                        return select_related_solution(
                            self.solution_widgets["eo"], self.attempt.solution
                        )
                    # Navigate between solution steps
                    index = self.step_order.index(obj.property("kind"))
                    if key == Qt.Key_Backtab:
                        if index == 0:
                            self.command_input.setFocus()
                            return True
                        else:
                            next_index = index
                            sol = self.attempt.solution
                            while True:
                                next_index = (next_index - 1) % len(self.step_order)
                                widget = self.solution_widgets[
                                    self.step_order[next_index]
                                ]
                                if widget.selectedItems():
                                    sol = widget.selectedItems()[0].data(SOLUTION)
                                if next_index == 0 or widget.count() > 0:
                                    break
                            return select_related_solution(widget, sol)
                    else:
                        if index == len(self.step_order) - 1:
                            self.command_input.setFocus()
                            return True
                        else:
                            next_index = index
                            sol = self.attempt.solution
                            while True:
                                next_index = (next_index + 1) % len(self.step_order)
                                widget = self.solution_widgets[
                                    self.step_order[next_index]
                                ]
                                if widget.selectedItems():
                                    sol = widget.selectedItems()[0].data(SOLUTION)
                                if (
                                    next_index == len(self.step_order) - 1
                                    or widget.count() > 0
                                ):
                                    break
                            return select_related_solution(widget, sol)
                # Command history
                elif obj == self.command_input and key == Qt.Key_Up:
                    if self.history_pointer < 0:
                        return True
                    previous_command = self.command_history[self.history_pointer]
                    self.command_input.setText(previous_command)
                    self.history_pointer = max(0, self.history_pointer - 1)
                    return True
                elif obj == self.command_input and key == Qt.Key_Down:
                    self.history_pointer = min(
                        self.history_pointer + 1, len(self.command_history)
                    )
                    previous_command = ""
                    if self.history_pointer < len(self.command_history) - 1:
                        previous_command = self.command_history[
                            self.history_pointer + 1
                        ]
                    self.command_input.setText(previous_command)
                    self.history_pointer = min(
                        self.history_pointer, len(self.command_history) - 1
                    )
                    return True

            return delegate.eventFilter(obj, event)

        return handle()

    def check_solution(self, solution):
        """Load a selected solution"""
        self.attempt.set_solution(solution)
        if solution.step_info.is_solved(self.attempt.cube):
            self.attempt.advance()
        self.command_input.setFocus()

    def _create_menus(self):
        """Create the menu bar with File and Help menus"""
        # Create menu bar
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("File")

        # Save session action
        save_action = QAction("Save Session", self)

        @catch_errors
        def save(*args, **kwargs):
            self.save_session_dialog()

        save_action.triggered.connect(save)
        file_menu.addAction(save_action)

        # Load session action
        load_action = QAction("Load Session", self)

        @catch_errors
        def load(*args, **kwargs):
            self.load_session_dialog()

        load_action.triggered.connect(load)
        file_menu.addAction(load_action)

        # Export image
        export_action = QAction("Export image", self)

        @catch_errors
        def export(*args, **kwargs):
            self.export_image_dialog()

        export_action.triggered.connect(export)
        file_menu.addAction(export_action)

        # Exit action
        exit_action = QAction("Exit", self)

        @catch_errors
        def close(*args, **kwargs):
            self.close()

        exit_action.triggered.connect(close)
        file_menu.addAction(exit_action)

        # Help menu
        help_menu = menu_bar.addMenu("Help")

        # Help action
        help_action = QAction("Help", self)

        @catch_errors
        def show_help(*args, **kwargs):
            self.show_help()

        help_action.triggered.connect(show_help)
        help_menu.addAction(help_action)

        # About action
        about_action = QAction("About", self)

        @catch_errors
        def show_about(*args, **kwargs):
            self.show_about()

        about_action.triggered.connect(show_about)
        help_menu.addAction(about_action)

    def save_session_dialog(self):
        """Show dialog to save session"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Session", "", "VFMC Files (*.vfmc)"
        )
        if filename:
            if not filename.endswith(".vfmc"):
                filename += ".vfmc"
            self.commands.save_session(filename)

    def load_session_dialog(self):
        """Show dialog to load session"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Session", "", "VFMC Files (*.vfmc)"
        )
        if filename:
            self.commands.load_session(filename)

    def export_image_dialog(self):
        """Show dialog to save session"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Image", "", "PNG (*.png)"
        )
        if filename:
            if not filename.endswith(".png"):
                filename += ".png"
            size, ok = QInputDialog.getInt(
                self, "Image Size", "Enter size:", 100, 25, 500
            )
            if ok:
                self.commands.export_image(filename, size)

    def show_about(self):
        """Show about dialog"""
        about_dialog = QMessageBox(self)
        about_dialog.setWindowTitle("About VFMC")
        about_dialog.setText(f"<h2>VFMC v{version('vfmc')}</h2>")
        about_dialog.setInformativeText(
            "<html><body>"
            "<p style='font-size: 14px;'>A tool for building fewest-move cube solutions virtually.</p>"
            "<p style='font-size: 14px;'>Developed by Rodney Kinney. Based on the cubelib library by Jonas Balsfulland.</p>"
            f"<p style='font-size: 10px;'>Error log: {os.path.join(prefs.app_dir(), 'vfmc.log')}</p>"
            "</body></html>"
        )
        about_dialog.setMinimumWidth(300)
        about_dialog.setMinimumHeight(300)
        about_dialog.setStandardButtons(QMessageBox.Ok)
        about_dialog.show()

    def show_help(self):
        """Show help window"""
        help_dialog = QMessageBox(self)
        help_dialog.setWindowModality(Qt.NonModal)
        help_dialog.setWindowTitle("VFMC help")

        commands = []
        for name in dir(self.commands):
            if name.startswith("_"):
                continue
            attr = getattr(self.commands, name)
            if callable(attr):
                commands.append((name, attr))

        help_file = os.path.join(os.path.dirname(__file__), "help.html")
        with open(help_file, "r") as f:
            help_dialog.setInformativeText(f.read())

        help_dialog.setText("Welcome to VFMC")
        help_dialog.setStandardButtons(QMessageBox.Ok)
        help_dialog.show()
        self.command_input.setFocus()


class InsertionsDialog(QDialog):
    def __init__(self, window, step):
        super().__init__(parent=window)
        self.window = window
        self.step = step
        self.setWindowTitle("Insertions")
        self.setModal(True)
        self.resize(800, 100)

        layout = QVBoxLayout(self)
        self.attempt = Attempt()
        self.attempt.set_scramble(self.window.attempt.scramble)
        self.attempt.set_solution(self.step)
        viz = CubeViz(self.attempt)
        layout.addWidget(CubeWidget(viz))

        self.save_button = QPushButton("Save", self)

        @catch_errors
        def save(*args, **kwargs):
            self.save()

        self.save_button.clicked.connect(save)
        self.save_button.setEnabled(False)

        # Editable text field
        self.text_edit = QLineEdit(self)

        @catch_errors
        def refresh(*args, **kwargs):
            self.refresh()

        self.text_edit.cursorPositionChanged.connect(refresh)
        self.text_edit.textChanged.connect(refresh)
        self.text_edit.setText(
            str(Algorithm("").merge(self.step.insertions.replacement.all_on_normal()))
        )
        layout.addWidget(self.text_edit)

        # Buttons
        buttons = QHBoxLayout()
        layout.addLayout(buttons)
        buttons.addStretch(1)
        buttons.addWidget(self.save_button)
        cancel_button = QPushButton("Cancel", self)

        @catch_errors
        def close(*args, **kwargs):
            self.close()

        cancel_button.clicked.connect(close)
        buttons.addWidget(cancel_button)

        self.setLayout(layout)

    def refresh(self):
        self.step.set_replacement(
            self.text_edit.text(), self.text_edit.cursorPosition()
        )
        self.attempt.set_solution(self.step)
        step = self.step.clone()
        step.set_replacement(self.text_edit.text(), len(self.text_edit.text()))
        is_solved = step.step_info.is_solved(
            Cube(f"{self.attempt.scramble} {step.full_alg()}")
        )
        self.save_button.setEnabled(is_solved)

    def save(self):
        self.window.commands.execute(f'compute_insertions("{self.text_edit.text()}")')
        self.window.commands.execute('comment("solved")')
        self.window.commands.execute("save")
        self.close()


def run(session_file: Optional[str] = None):
    app = QApplication(sys.argv)
    app.setApplicationName("VFMC")
    window = AppWindow()
    window.show()
    if session_file:
        window.commands.load_session(session_file)

    sys.exit(app.exec_())


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
            # Does it match a method in this class?
            if cmd.endswith("'"):
                cmd = cmd.replace("'", "_prime")
            cmd_name = re.sub("\\(.*$", "", cmd)
            if cmd_name in dir(self):
                # Add parentheses if missing
                if cmd.find("(") < 0:
                    cmd = f"{cmd}()"
                # Use locals and globals from this context
                local_vars = {"self": self}
                exec(f"result = self.{cmd}", globals(), local_vars)
                result = local_vars.get("result")
                if result is None:
                    result = CommandResult(add_to_history=[raw_command])
                if result.error is not None:
                    self.window.set_status(f"Error: {result.error}")
                elif result.add_to_history:
                    self.command_history.extend(result.add_to_history)
                    self.history_pointer = len(self.command_history) - 1
            else:
                # Check if it's a sequence of cube moves
                if re.fullmatch(MOVE_REGEX, raw_command):
                    self.window._append_moves(raw_command)
                    self.command_history.append(raw_command)
                else:
                    self.window.set_status(f"No such command: {raw_command}")
        except Exception as e:
            logging.error(traceback.format_exc())
            logging.error(sys.exc_info())
            self.window.set_status(f"Error: {e}")

    def debug(self):
        from vfmc_core import debug

        self.window.set_status(debug(self.attempt.cube))
        return CommandResult(add_to_history=[])

    def help(self):
        self.window.show_help()
        return CommandResult(add_to_history=[])

    def x(self):
        self.attempt.solution.x(1)

    def x_prime(self):
        self.attempt.solution.x(3)

    def x2(self):
        self.attempt.solution.x(2)

    def y(self):
        self.attempt.solution.y(1)

    def y_prime(self):
        self.attempt.solution.y(3)

    def y2(self):
        self.attempt.solution.y(2)

    def z(self):
        self.attempt.solution.z(1)

    def z_prime(self):
        self.attempt.solution.z(3)

    def z2(self):
        self.attempt.solution.z(2)

    def set_step(self, kind, variant):
        self.window.set_step(kind, variant)

    def eoud(self):
        self.window.set_step("eo", "ud")

    def eofb(self):
        self.window.set_step("eo", "fb")

    def eorl(self):
        self.window.set_step("eo", "rl")

    def drud(self):
        self.window.set_step("dr", "ud")

    def drfb(self):
        self.window.set_step("dr", "fb")

    def drrl(self):
        self.window.set_step("dr", "rl")

    def sort(self, key: str, group_by_axis: bool = False):
        self.attempt.set_sort_order(SortOrder(key, group_by_axis))

    def htr(self):
        variant = ""
        for v in ["ud", "fb", "rl"]:
            if StepInfo("dr", v).is_solved(self.window.attempt.cube):
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
            variant = next(
                s.variant for s in self.attempt.solution.substeps() if s.kind == "dr"
            )
        if variant is not None:
            self.window.set_step("fr", variant)
        else:
            self.window.set_status(
                """No DR step found. Specify axis="..." to set the FR axis"""
            )

    def finish(self, axis=None):
        self.window.set_step("finish", "")

    def insertions(self):
        self.window.set_step("insertions", "")

    def compute_insertions(self, moves_str: str):
        if self.attempt.solution.kind != "insertions":
            return CommandResult(add_to_history=[])
        self.attempt.solution.set_replacement(moves_str, len(moves_str))
        self.attempt.solution.add_markers()

    def set_inverse(self, b: bool):
        self.attempt.set_inverse(b)

    def niss(self):
        """Switch between normal and inverse scramble"""
        self.attempt.set_inverse(not self.attempt.inverse)

    def solve(self, num_solutions: int = 1):
        """Find and save solutions for the current step"""
        if num_solutions > 50:
            self.window.set_status("Maximum of 50 solutions per solve")
            return
        self.window.set_status(
            f"Finding solutions for {self.attempt.solution.kind}{self.attempt.solution.variant}..."
        )
        solutions = self.attempt.solve(num_solutions)
        if solutions:
            self.window.set_status(
                f"Found {len(solutions)} solution{'' if len(solutions) == 1 else 's'}"
            )
        else:
            self.window.set_status(
                f"No solutions found for {self.attempt.solution.kind}{self.attempt.solution.variant}"
            )
        commands = []
        if solutions:
            was_inverse = self.attempt.inverse
            for sol in solutions:
                commands.append(step_name(sol.kind, sol.variant))
                if sol.alg.normal_moves():
                    commands.append("set_inverse(False)")
                    commands.append(" ".join(sol.alg.normal_moves()))
                if sol.alg.inverse_moves():
                    commands.append("set_inverse(True)")
                    commands.append(" ".join(sol.alg.inverse_moves()))
                commands.append("save")
            commands.append(f"set_inverse({was_inverse})")
            commands.append(
                step_name(self.attempt.solution.kind, self.attempt.solution.variant)
            )

        for cmd in commands:
            self.execute(cmd)
        if len(solutions) == 1:
            sol = solutions[0]
            index = self.attempt.solutions_by_kind()[sol.kind].index(sol) + 1
            self.execute(f'check("{sol.kind}",{index})')
        return CommandResult(add_to_history=[])

    def comment(self, s: str):
        sol = self.attempt.solution
        if sol.alg.len() == 0:
            sol = sol.previous
        if not sol:
            return
        self.attempt.set_comment(sol, s)
        item = self._item_containing(sol)
        if item:
            i = item.listWidget().row(item)
            padding = "   " if i < 9 else ("  " if i < 99 else " ")
            item.setText(f"{i + 1}.{padding}{self.attempt.to_str(sol)}")
            return

    def _item_containing(self, sol: PartialSolution) -> Optional[QListWidgetItem]:
        for kind in reversed(self.window.step_order):
            widget = self.window.solution_widgets[kind]
            for i in range(widget.count()):
                item = widget.item(i)
                if item.data(SOLUTION) == sol:
                    return item
        return None

    def done(self):
        sol = self.attempt.solution
        self.attempt.toggle_done(sol)

    def obscure(self):
        sol = self.attempt.solution
        self.attempt.toggle_obscured(sol)

    def save(self):
        """Save this algorithm and start a new one"""
        self.window.current_solution_widget.sync_history_with_editor()
        saved = self.attempt.save()
        if saved:
            self.window.scroll_to(saved)
            self.window.command_input.setFocus()

    def reset(self):
        """Reset the cube to the beginning of the current step"""
        self.attempt.reset()

    def back(self):
        """Go back to the previous step"""
        self.attempt.back()

    def check(self, kind: str, index: int):
        k = kind.lower()
        if k not in self.attempt.solutions_by_kind():
            self.window.set_status(f"Bad step type: {kind}")
            return
        solutions = self.attempt.solutions_by_kind()[kind.lower()]
        if index < 1 or index > len(solutions):
            self.window.set_status(f"Couldn't find {kind} #{index}")
            return
        self.window.check_solution(solutions[index - 1].clone())

    def forget(self, kind: Optional[str] = None, index: Optional[int] = None):
        if kind is None and index is None:
            self.attempt.forget(self.attempt.solution)
            return
        if kind is None or index is None:
            self.window.set_status("Must specify both step type and position")
            return
        k = kind.lower()
        if k not in self.attempt.solutions_by_kind():
            self.window.set_status(f"Bad step type: {kind}")
            return
        solutions = self.attempt.solutions_by_kind()[kind.lower()]
        if index < 1 or index > len(solutions):
            self.window.set_status(f"Couldn't find {kind} #{index}")
            return
        self.attempt.forget(solutions[index - 1])
        self.window.command_input.setFocus()

    def scramble(self, scramble: str = None):
        """
        <br>Use scramble(\"...\") to initialize with the specified scramble
        <br>or omit the parentheses to generate a new random scramble
        """
        if scramble is None:
            wrapper = Algorithm("R' U' F")
            scramble = str(wrapper.merge(Algorithm(gen_scramble())).merge(wrapper))
        self.attempt.set_scramble(scramble)
        self.command_history.clear()
        scramble_cmd = f'scramble("{scramble}")'
        sort_cmd = f'sort("{preferences.sort_order.key}",{preferences.sort_order.group_by_axis})'
        return CommandResult(add_to_history=[scramble_cmd, sort_cmd])

    def save_session(self, filename):
        try:
            with open(filename, "w") as f:
                f.write(f"# VFMC version {version('vfmc')}\n")
                f.writelines("\n".join(self.command_history))
            self.window.set_status(f"Saved session to {filename}")
            return CommandResult(add_to_history=[])
        except Exception as e:
            self.window.set_status(f"Unable to save to {filename}: {e}")
            return CommandResult(error=e, add_to_history=[])

    def load_session(self, filename):
        h = self.command_history
        try:
            self.command_history = []
            with open(filename, "r") as f:
                for cmd in f.readlines():
                    if not cmd.startswith("#"):
                        self.execute(cmd.strip())
            self.window.set_status(f"Loaded '{filename}'")
            return CommandResult(add_to_history=[])
        except Exception as e:
            self.command_history = h
            self.window.set_status(f"Unable to load '{filename}': {e}")
            return CommandResult(error=e, add_to_history=[])

    def palette(self, name):
        p = Palette.by_name(name) if name else None
        self.window.viz.set_palette(p)
        return CommandResult(add_to_history=[])

    def camera(self, x, y, z, angle=-math.pi / 6):
        self.window.viz.set_camera(x, y, z)
        self.window.viz.view_y = angle
        self.window.viz.refresh()
        return CommandResult(add_to_history=[])

    def export_image(self, filename, size=None):
        self.window.cube_viz_widget.export_png(filename, size)
        return CommandResult(add_to_history=[])


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
        self.history_is_stale = False
        self.current_editor = None
        self.comment = None
        self.originalKeyPress = None
        self.original_alg = None
        self.setSelectionMode(QListWidget.ContiguousSelection)
        self.setStyleSheet("font-size: 16px;")
        self.setEditTriggers(QListWidget.DoubleClicked)
        self.attempt.add_cube_listener(self.sync_widget_with_cube)

    def sync_widget_with_cube(self):
        """Sync the widget with Attempt cube state"""
        if self.current_editor:
            return  # Don't sync if user is editing
        self.clear()
        self.addItem(self.attempt.scramble)
        self.addItem(self.attempt.inverse_scramble)
        self.addItem("")
        for step in self.attempt.solution.substeps():
            text = f"{step.alg_str(verbose=True)}"
            if step.kind != "":
                if step.step_info.is_solved(self.attempt.cube):
                    text = f"{self.attempt.to_str(step, verbose=True)}"
                else:
                    parentheses = f"{' ' if step.alg.len() else ''}{'( )' if not step.alg.inverse_moves() and self.attempt.inverse else ''}"
                    comment = self.attempt.get_comment(step)
                    if not comment or step.alg.len() == 0:
                        comment = step.default_comment()
                    text = f"{text}{parentheses} // {comment} ({step.full_alg().len()})"
            item = QListWidgetItem(text)
            item.setData(SOLUTION, step)
            self.addItem(item)
        last_item = self.item(self.count() - 1)
        if last_item.data(SOLUTION).kind != "insertions":
            last_item.setFlags(last_item.flags() | Qt.ItemIsEditable)

    def edit(self, index, trigger, event):
        delegate = super()

        @catch_and_return(False)
        def handle(*args, **kwargs):
            result = delegate.edit(index, trigger, event)
            if result:
                editor = self.indexWidget(index)
                if editor:
                    self.current_editor = editor
                    text = editor.text().split("//")[0].strip()
                    editor.setText(text)
                    if ")" in text and self.attempt.inverse:
                        editor.setCursorPosition(text.index(")"))
                    self.original_alg = self.attempt.solution.alg

                    @catch_errors
                    def sync(*args, **kwargs):
                        self.sync_cube_with_editor()

                    self.current_editor.textEdited.connect(sync)
                    self.comment = None
            return result

        return handle()

    def sync_cube_with_editor(self):
        if not self.current_editor:
            return
        edited_text = self.current_editor.text().split("//")
        alg_str = edited_text[0].strip()
        self.comment = edited_text[1].strip() if len(edited_text) > 1 else None
        if "(" in alg_str and ")" not in alg_str:
            return
        if not alg_str and self.attempt.inverse:
            self.current_editor.setText("( )")
            self.current_editor.setCursorPosition(2)
        try:
            alg = Algorithm(alg_str)
            self.attempt.solution.alg = Algorithm("")
            if not self.attempt.solution.append(alg):
                self.window().set_status(
                    f"{alg} not allowed after {self.attempt.solution.previous.kind}{self.attempt.solution.previous.variant}"
                )
            else:
                self.window().set_status("")
                self.attempt.update_cube()
                self.history_is_stale = True
        except Exception:
            pass

    def sync_history_with_editor(self):
        if not self.history_is_stale or not self.original_alg:
            return
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
        if self.comment:
            commands.execute(f'comment("{self.comment}")')
        self.history_is_stale = False

    def closeEditor(self, editor, hint):
        # Called when editing is finished
        delegate = super()

        @catch_errors
        def handle(*args, **kwargs):
            self.sync_history_with_editor()
            self.parent().window().command_input.setFocus()

            self.current_editor = None
            self.original_alg = None

            delegate.closeEditor(editor, hint)
            self.sync_widget_with_cube()

        handle()

    def mouseDoubleClickEvent(self, event):
        delegate = super()

        @catch_errors
        def handle(*args, **kwargs):
            item = self.itemAt(event.pos())
            if item and item.data(SOLUTION):
                self.activate_step(item.data(SOLUTION))
            delegate.mouseDoubleClickEvent(event)

        handle()

    # Override key event to handle copy and editing
    def keyPressEvent(self, event):
        delegate = super()

        @catch_errors
        def handle(*args, **kwargs):
            if event.matches(QKeySequence.Copy):
                selected_items = self.selectedItems()
                if selected_items:
                    clipboard_text = "\n".join(item.text() for item in selected_items)
                    QApplication.clipboard().setText(clipboard_text)
            elif event.key() in {
                Qt.Key_Enter,
                Qt.Key_Return,
                Qt.Key_Delete,
                Qt.Key_Backspace,
            }:
                # Enter key starts editing the current item if any
                current_item = self.currentItem()
                if current_item:
                    if current_item.flags() & Qt.ItemIsEditable:
                        self.editItem(current_item)
                    else:
                        self.activate_step(current_item.data(SOLUTION))
            else:
                delegate.keyPressEvent(event)  # Default behavior for other keys

        handle()

    def activate_step(self, target: PartialSolution):
        if target.kind == "insertions":
            if not self.attempt.solution.step_info.is_solved(self.attempt.cube):
                InsertionsDialog(self.window(), self.attempt.solution).exec()
            return
        if target not in self.attempt.solutions_by_kind()[target.kind]:
            return
        # Execute via self.commands to get this into the history
        cmd = self.window().commands
        inverse = self.attempt.inverse
        cmd.execute(f'set_step("{target.kind}","{target.variant}")')
        if target.alg.inverse_moves():
            cmd.execute("set_inverse(True)")
            cmd.execute(" ".join(target.alg.inverse_moves()))
        if target.alg.normal_moves():
            cmd.execute("set_inverse(False)")
            cmd.execute(" ".join(target.alg.normal_moves()))
        cmd.execute(f"set_inverse({inverse})")
        self.editItem(self.item(self.count() - 1))
        self.window().format_saved_solutions()


@dataclass
class CommandResult:
    error: Optional[Exception] = None
    add_to_history: List[str] = None


def main():
    # Configure logging
    logfile = prefs.app_dir() / "vfmc.log"
    logging.basicConfig(
        filename=logfile,
        filemode="w",
        level=logging.DEBUG,
        format="%(levelname)s - %(message)s",
    )

    if getattr(sys, "frozen", False):  # Running from a PyInstaller bundle
        bundle_dir = os.path.dirname(sys.executable)
        # Set working directory to the home of the executable
        if os.path.basename(bundle_dir) == "MacOS":
            logging.debug(f"Running bundle from {bundle_dir}")
            os.chdir(os.path.dirname(os.path.dirname(bundle_dir)))
    session_file = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else None
    run(session_file)


if __name__ == "__main__":
    main()
