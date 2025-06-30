from typing import Optional, Dict, List, Callable, Set, Tuple
import time
from collections import defaultdict

from vfmc_core import Algorithm, StepInfo, Cube
from vfmc.insertions import Insertions, Insertion, Replacement
from vfmc.orientation import Orientation
from vfmc.prefs import SortOrder, SortKeys

# Possible continuations for each step
NEXT_STEPS = {
    ("", ""): [("eo", "fb"), ("eo", "rl"), ("eo", "ud"), ("finish", "")],
    ("eo", "ud"): [("dr", "fb"), ("dr", "rl"), ("finish", "")],
    ("eo", "rl"): [("dr", "ud"), ("dr", "fb"), ("finish", "")],
    ("eo", "fb"): [("dr", "ud"), ("dr", "rl"), ("finish", "")],
    ("dr", "ud"): [("htr", "ud"), ("finish", "")],
    ("dr", "rl"): [("htr", "rl"), ("finish", "")],
    ("dr", "fb"): [("htr", "fb"), ("finish", "")],
    ("htr", "ud"): [("fr", "ud"), ("finish", ""), ("insertions", "")],
    ("htr", "rl"): [("fr", "rl"), ("finish", ""), ("insertions", "")],
    ("htr", "fb"): [("fr", "fb"), ("finish", ""), ("insertions", "")],
    ("fr", "ud"): [("finish", ""), ("insertions", "")],
    ("fr", "fb"): [("finish", ""), ("insertions", "")],
    ("fr", "rl"): [("finish", ""), ("insertions", "")],
    ("finish", ""): [("insertions", "")],
    ("insertions", ""): [("insertions", "")],
}

# Continuations after solving each step
DEFAULT_NEXT_STEPS = {
    ("htr", "ud"): ("fr", "ud"),
    ("htr", "rl"): ("fr", "rl"),
    ("htr", "fb"): ("fr", "fb"),
    ("fr", "ud"): ("finish", ""),
    ("fr", "fb"): ("finish", ""),
    ("fr", "rl"): ("finish", ""),
    ("finish", ""): ("insertions", ""),
}


class PartialSolution:
    """An individual solution step"""

    def __init__(
        self,
        kind: str = "",
        variant: str = "",
        alg: Algorithm = Algorithm(""),
        previous: Optional["PartialSolution"] = None,
    ):
        self.kind = kind
        self.variant = variant
        self.step_info = StepInfo(kind, variant)
        self.previous = previous
        self.alg = alg
        self.orientation = self.default_orientation()

    def default_orientation(self):
        orientation = Orientation.default_for(self.kind, self.variant)
        if self.previous is not None:
            if self.previous.kind == "eo":
                if orientation.front not in self.previous.variant:
                    orientation = orientation.y(1)
            else:
                orientation = Orientation(
                    self.previous.orientation.top, self.previous.orientation.front
                )
        return orientation

    def append(self, alg: Algorithm) -> bool:
        if not self.allows_moves(alg):
            return False
        self.alg = self.alg.merge(alg)
        return True

    def allows_moves(self, alg: Algorithm) -> bool:
        if self.previous is None or self.kind == "finish":
            return True
        return self.previous.step_info.are_moves_allowed(alg)

    def full_alg(self):
        if self.previous is not None:
            return self.previous.full_alg().merge(self.alg)
        return self.alg

    def substeps(self) -> List["PartialSolution"]:
        if self.previous is None:
            return [self]
        else:
            return self.previous.substeps() + [self]

    def is_empty(self) -> bool:
        val = self.alg.is_empty()
        if self.previous:
            val = val and self.previous.is_empty()
        return val

    def x(self, ticks: int):
        self.orientation = self.orientation.x(ticks)

    def y(self, ticks: int):
        self.orientation = self.orientation.y(ticks)

    def z(self, ticks: int):
        self.orientation = self.orientation.z(ticks)

    def alg_str(self, verbose: bool = False):
        return str(self.alg)

    def default_comment(self) -> str:
        return step_name(self.kind, self.variant)

    def clone(self) -> "PartialSolution":
        return PartialSolution.create(
            kind=self.kind,
            variant=self.variant,
            alg=self.alg,
            previous=self.previous,
        )

    def __repr__(self):
        return f"{self.alg} // ({self.full_alg().len()})"

    def __eq__(self, other):
        if self.__class__ == other.__class__:
            return (
                self.kind == other.kind
                and self.variant == other.variant
                and str(self.full_alg()) == str(other.full_alg())
            )
        else:
            return False

    def __hash__(self):
        return f"{self.kind}{self.variant}:{self.full_alg()}".__hash__()

    @staticmethod
    def create(
        kind: str = "",
        variant: str = "",
        alg: Algorithm = Algorithm(""),
        previous: Optional["PartialSolution"] = None,
    ) -> "PartialSolution":
        if kind == "insertions":
            return InsertionsStep(previous=previous)
        return PartialSolution(kind, variant, alg, previous)


class Attempt:
    """Global state of the FMC attempt"""

    def __init__(self):
        self.scramble = ""
        self.inverse_scramble = ""
        self.cube = Cube("")
        self.inverse = False
        self.solution = PartialSolution()
        self._saved_by_kind: Dict[str, List[PartialSolution]] = defaultdict(list)
        self._done: Set[PartialSolution] = set()
        self._comments: Dict[PartialSolution, str] = {}
        self._continuations: Dict[PartialSolution, Tuple[str, str]] = {}
        self._orientations: Dict[PartialSolution, Orientation] = {}
        self._obscured: Set[PartialSolution] = set()
        self._sort_order = SortOrder()
        self._save_timestamps: Dict[PartialSolution, float] = {}
        self._cube_listeners = []
        self._saved_solution_listeners = []
        self._solution_attribute_listeners = []

    def set_scramble(self, s):
        self._saved_by_kind.clear()
        self._done.clear()
        self._comments.clear()
        self._continuations.clear()
        self._orientations.clear()
        self.notify_saved_solution_listeners()
        self.scramble = s
        self.inverse_scramble = str(Algorithm(self.scramble).inverted().on_inverse())
        self.inverse = False
        self.set_solution(PartialSolution("", "", previous=None))
        self.update_cube()

    def niss(self, inverse: Optional[bool] = None):
        self.set_inverse(not self.inverse)

    def set_inverse(self, b):
        if b != self.inverse:
            self.inverse = b
            self.update_cube()

    def set_sort_order(self, order: SortOrder):
        if self._sort_order != order:
            self._sort_order = order
            for saved in self._saved_by_kind.values():
                saved.sort(key=self.sort_key())
            self.notify_saved_solution_listeners()

    def toggle_done(self, sol: PartialSolution):
        if sol not in self._saved_by_kind[sol.kind]:
            if sol.previous:
                self.toggle_done(sol.previous)
            return
        if sol in self._done:
            self._done.remove(sol)
        else:
            self._done.add(sol)
        self.notify_solution_attribute_listeners()

    def toggle_obscured(self, sol: PartialSolution):
        if sol in self._obscured:
            self._obscured.remove(sol)
        else:
            self._obscured.add(sol)
        self.notify_solution_attribute_listeners()

    def forget(self, sol: PartialSolution):
        self._saved_by_kind[sol.kind].remove(sol)
        self.notify_saved_solution_listeners()
        if sol == self.solution:
            if self.solution.previous:
                self.set_solution(self.solution.previous)
                if self.solution.step_info.is_solved(self.cube):
                    self.advance()
            else:
                self.back()

    def set_comment(self, sol: PartialSolution, s: str):
        self._comments[sol] = s
        self.notify_solution_attribute_listeners()

    def get_comment(self, sol: PartialSolution) -> Optional[str]:
        return self._comments.get(sol)

    def is_done(self, sol: PartialSolution):
        return sol in self._done

    def to_str(self, sol: PartialSolution, verbose: bool = False) -> str:
        if sol in self._obscured:
            return " ".join(["?" for i in range(sol.alg.len())])
        comment = self._comments.get(sol)
        if not comment:
            comment = sol.default_comment()
        return f"{sol.alg_str(verbose)} // {comment} ({sol.full_alg().len()})"

    def append(self, alg: Algorithm) -> bool:
        if self.inverse:
            alg = alg.on_inverse()
        if not self.solution.append(alg):
            return False
        self.update_cube()
        return True

    def back(self):
        if self.solution.previous is None:
            self.set_solution(PartialSolution())
            return

        if self.solution.alg.len() > 0:
            sol = PartialSolution.create(
                self.solution.kind,
                self.solution.variant,
                previous=self.solution.previous,
                alg=Algorithm(""),
            )
            self.set_solution(sol)
        else:
            previous = self.solution.previous
            self.solution = previous.previous or PartialSolution()
            self.advance_to(previous.kind, previous.variant)

    def possible_next_steps(self, sol: PartialSolution) -> List[Tuple[str, str]]:
        return NEXT_STEPS[(sol.kind, sol.variant)]

    def possible_steps_following(self, kind, variant) -> List[Tuple[str, str]]:
        return NEXT_STEPS[(kind, variant)]

    def advance_to(self, kind: str, variant: str):
        if (kind, variant) == (self.solution.kind, self.solution.variant):
            return
        previous = (
            self.solution
            if not self.solution.alg.is_empty()
            else self.solution.previous
        )
        if previous:
            if not previous.alg.inverse_moves():
                self.inverse = False
            else:
                self.inverse = len(previous.alg.normal_moves()) == 0
        sol = PartialSolution.create(kind, variant, previous=previous)
        self.set_solution(sol)

    def advance(self):
        next = self._continuations.get(self.solution)
        if not next:
            next = DEFAULT_NEXT_STEPS.get((self.solution.kind, self.solution.variant))
        if not next:
            next = NEXT_STEPS[(self.solution.kind, self.solution.variant)][0]
        self.advance_to(*next)

    def solutions_by_kind(self) -> Dict[str, List[PartialSolution]]:
        return self._saved_by_kind

    def solutions_for_step(self, kind: str, variant: str) -> List[PartialSolution]:
        return [s for s in self._saved_by_kind.get(kind, []) if s.variant == variant]

    def corner_visibility(self) -> List[Tuple[int, int, int]]:
        return self.solution.step_info.corner_visibility(self.cube)

    def edge_visibility(self) -> List[Tuple[int, int]]:
        return self.solution.step_info.edge_visibility(self.cube)

    def last_solved_step(self) -> Optional[PartialSolution]:
        for step in reversed(self.solution.substeps()):
            if step.step_info.is_solved(self.cube):
                return step
        return None

    def reset(self):
        alg = self.solution.alg
        # Clear only the moves for the current side
        if self.inverse:
            alg = Algorithm(" ".join(alg.normal_moves()))
        else:
            alg = Algorithm(f"({' '.join(alg.inverse_moves())})")
        new_solution = PartialSolution.create(
            self.solution.kind,
            self.solution.variant,
            previous=self.solution.previous,
            alg=alg,
        )
        self.set_solution(new_solution)

    def set_solution(self, sol: PartialSolution):
        self.solution = sol
        o = self._orientations.get(sol)
        if o:
            self.solution.orientation = o
        self.update_cube()
        self.notify_solution_attribute_listeners()

    def solve(self, num_solutions: int) -> List[PartialSolution]:
        """Find solutions for the current step"""
        sol = self.solution
        existing = set(str(s) for s in self.solutions_for_step(sol.kind, sol.variant))
        algs = sol.step_info.solve(self.cube, len(existing) + num_solutions)
        solutions = []
        for alg in algs:
            if self.inverse:
                alg = alg.on_inverse()
            base_alg = Algorithm(str(sol.alg))
            base_alg.merge(alg)
            s = PartialSolution.create(
                kind=sol.kind,
                variant=sol.variant,
                previous=sol.previous,
                alg=sol.alg.merge(alg),
            )
            if str(s) not in existing:
                solutions.append(s)
            if len(solutions) >= num_solutions:
                break
        return solutions

    def save(self) -> Optional[PartialSolution]:
        sol = self.solution.clone()
        is_solved = sol.step_info.is_solved(self.cube)
        if not is_solved and not self.get_comment(sol):
            case = self.solution.step_info.case_name(self.cube)
            comment = f"{step_name(self.solution.kind, self.solution.variant)}-{case}"
            self.set_comment(sol, comment)
        if is_solved:
            if sol.kind in {"eo", "dr"}:
                self.reset()
            else:
                self.advance()
        self.save_solution(sol)
        return sol

    def get_save_timestamps(self, sols: List[PartialSolution]) -> List[float]:
        return [self._save_timestamps[s] for s in sols]

    def sort_key(self):
        def sort_by_axis_move_count(sol):
            return (
                sol.kind,
                sol.variant,
                sol.full_alg().len(),
                len(sol.alg.inverse_moves()) > 0,
                len(sol.alg.normal_moves()) > 0,
                str(sol.alg),
            )

        def sort_by_move_count(sol):
            return (
                sol.full_alg().len(),
                len(sol.alg.inverse_moves()) > 0,
                len(sol.alg.normal_moves()) > 0,
                str(sol.alg),
            )

        def sort_by_axis_time(sol):
            return (sol.kind, sol.variant, self._save_timestamps[sol])

        def sort_by_time(sol):
            return self._save_timestamps[sol]

        if self._sort_order.key == SortKeys.TIME:
            return sort_by_axis_time if self._sort_order.group_by_axis else sort_by_time
        else:
            return (
                sort_by_axis_move_count
                if self._sort_order.group_by_axis
                else sort_by_move_count
            )

    def save_solution(self, sol: PartialSolution):
        self._save_timestamps[sol] = time.monotonic()

        existing = self._saved_by_kind[sol.kind]
        if sol not in existing:
            existing.append(sol)
        existing.sort(key=self.sort_key())
        self.notify_saved_solution_listeners()

    def add_saved_solution_listener(self, callback: Callable):
        self._saved_solution_listeners.append(callback)

    def add_solution_attribute_listener(self, callback: Callable):
        self._solution_attribute_listeners.append(callback)

    def add_cube_listener(self, callback: Callable):
        self._cube_listeners.append(callback)

    def update_cube(self):
        self.cube = Cube(self.scramble)
        self.cube.apply(self.solution.full_alg())
        if self.inverse:
            self.cube.invert()
        self.notify_cube_listeners()

    def notify_saved_solution_listeners(self):
        for listener in self._saved_solution_listeners:
            listener()

    def notify_solution_attribute_listeners(self):
        for listener in self._solution_attribute_listeners:
            listener()

    def notify_cube_listeners(self):
        for listener in self._cube_listeners:
            listener()


class InsertionsStep(PartialSolution):
    def __init__(self, previous):
        super().__init__(kind="insertions", previous=previous)
        self.insertions = Insertions(previous.full_alg())
        self.inserted_algs: Dict[str, str] = {}
        self.alg_with_markers = str(self.insertions.original.all_on_normal())

    def insertion_symbol(self, index):
        choices = "^#*@"
        n = int(index / len(choices)) + 1
        return choices[index % len(choices)] * n

    def replacement_symbol(self, index):
        open = "[{"
        close = "]}"
        n = int(index / len(open)) + 1
        open = open[index % len(open)] * n
        close = close[index % len(close)] * n
        return f"{open}{close}"

    def clone(self) -> "PartialSolution":
        step = InsertionsStep(previous=self.previous)
        step.alg = self.alg
        step.alg_with_markers = self.alg_with_markers
        step.insertions = self.insertions
        step.inserted_algs = self.inserted_algs
        return step

    def alg_str(self, verbose: bool = False):
        lines = []
        if not verbose:
            return " ".join(self.inserted_algs.keys())

        lines += [""] + [self.alg_with_markers]
        if self.inserted_algs:
            lines += [f"{symbol} = {alg}" for symbol, alg in self.inserted_algs.items()]
            lines += [""] + [str(Algorithm("").merge(self.insertions.replacement))]
        return "\n".join(lines + [""])

    def append(self, alg: Algorithm) -> bool:
        raise ValueError("Double-click on solution to find insertions")

    def set_replacement(self, text, pos):
        self.insertions.set_replacement(text, pos)
        self.alg = self.insertions.net_alg()

    def add_markers(self):
        # Add placeholders for insertions in preceding steps
        self.alg_with_markers = ""
        self.inserted_algs.clear()
        orig = self.insertions.original.all_on_normal().normal_moves()
        final = []
        pos = 0
        n_insert = -1
        n_replace = -1
        edits = self.insertions.get_edits()
        for edit in edits:
            if isinstance(edit, Insertion):
                n_insert += 1
                symbol = self.insertion_symbol(n_insert)
                final.extend(orig[pos : edit.pos])
                pos = edit.pos
                final.append(symbol)
                self.inserted_algs[symbol] = " ".join(edit.moves)
            elif isinstance(edit, Replacement):
                n_replace += 1
                symbol = self.replacement_symbol(n_replace)
                final.extend(orig[pos : edit.start])
                pos = edit.start
                final.append(symbol[: int(len(symbol) / 2)])
                final.extend(orig[pos : edit.end])
                pos = edit.end
                final.append(symbol[int(len(symbol) / 2) :])
                self.inserted_algs[symbol] = " ".join(edit.moves)
        final.extend(orig[pos:])
        self.alg_with_markers = " ".join(final)


def step_name(kind, variant):
    s = kind
    if s not in {"htr", "fr"}:
        s = f"{s}{variant}"
    return s
