from typing import Optional, Dict, List, Callable, Set, Tuple
from collections import defaultdict

from vfmc_core import Algorithm, StepInfo, Cube

# Possible continuations for each step
NEXT_STEPS = {
    ("", ""): [("eo", "fb"), ("eo", "rl"), ("eo", "ud")],
    ("eo", "ud"): [("dr", "fb"), ("dr", "rl")],
    ("eo", "rl"): [("dr", "ud"), ("dr", "fb")],
    ("eo", "fb"): [("dr", "ud"), ("dr", "rl")],
    ("dr", "ud"): [("htr", "ud")],
    ("dr", "rl"): [("htr", "rl")],
    ("dr", "fb"): [("htr", "fb")],
    ("htr", "ud"): [("fr", "ud"), ("slice", "ud"), ("finish", "")],
    ("htr", "rl"): [("fr", "rl"), ("slice", "rl"), ("finish", "")],
    ("htr", "fb"): [("fr", "fb"), ("slice", "rl"), ("finish", "")],
    ("fr", "ud"): [("slice", "ud"), ("finish", "")],
    ("fr", "fb"): [("slice", "fb"), ("finish", "")],
    ("fr", "rl"): [("slice", "rl"), ("finish", "")],
    ("slice", "ud"): [("finish", "")],
    ("slice", "fb"): [("finish", "")],
    ("slice", "rl"): [("finish", "")],
    ("finish", ""): [("finish", "")],
}

# Continuations after solving each step
DEFAULT_NEXT_STEPS = {
    ("htr", "ud"): ("fr", "ud"),
    ("htr", "rl"): ("fr", "rl"),
    ("htr", "fb"): ("fr", "fb"),
    ("fr", "ud"): ("slice", "ud"),
    ("fr", "fb"): ("slice", "fb"),
    ("fr", "rl"): ("slice", "rl"),
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

# Rotation matrix for different faces
AXIS_ROTATIONS = {
    "f": ["u", "l", "d", "r"],
    "b": ["u", "r", "d", "l"],
    "r": ["u", "f", "d", "b"],
    "l": ["u", "b", "d", "f"],
    "u": ["f", "r", "b", "l"],
    "d": ["f", "l", "b", "r"],
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
        self.orientation = Orientation.default_for(self)

    def append(self, alg: Algorithm) -> bool:
        if not self.allows_moves(alg):
            return False
        self.alg = self.alg.merge(alg)
        return True

    def allows_moves(self, alg: Algorithm) -> bool:
        if self.previous is None:
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

    def __repr__(self):
        return f"{self.alg} // ({self.full_alg().len()})"

    def __eq__(self, other):
        if self.__class__ == other.__class__:
            return str(self.full_alg()) == str(other.full_alg())
        else:
            return False

    def __hash__(self):
        return str(self.full_alg()).__hash__()


class Attempt:
    """Global state of the FMC attempt"""

    def __init__(self):
        self.scramble = ""
        self.cube = Cube("")
        self.inverse = False
        self.solution = PartialSolution()
        self._saved_by_kind: Dict[str, List[PartialSolution]] = defaultdict(list)
        self._done: Set[PartialSolution] = set()
        self._comments: Dict[PartialSolution, str] = {}
        self._continuations: Dict[PartialSolution, Tuple[str, str]] = {}
        self._orientations: Dict[PartialSolution, Orientation] = {}
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
        self.inverse = False
        self.set_solution(PartialSolution("", "", previous=None))
        self.update_cube()

    def niss(self, inverse: Optional[bool] = None):
        self.set_inverse(not self.inverse)

    def set_inverse(self, b):
        if b != self.inverse:
            self.inverse = b
            self.update_cube()

    def toggle_done(self, sol: PartialSolution):
        if sol in self._done:
            self._done.remove(sol)
        else:
            self._done.add(sol)
        self.notify_solution_attribute_listeners()

    def set_comment(self, sol: PartialSolution, s: str):
        self._comments[sol] = s
        self.notify_solution_attribute_listeners()

    def get_comment(self, sol: PartialSolution) -> Optional[str]:
        return self._comments.get(sol)

    def is_done(self, sol: PartialSolution):
        return sol in self._done

    def to_str(self, sol: PartialSolution) -> str:
        comment = self._comments.get(sol)
        if not comment:
            comment = sol.kind
        return f"{sol.alg} // {comment} ({sol.full_alg().len()})"

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
            sol = PartialSolution(
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
        self.set_solution(PartialSolution(kind, variant, previous=previous))

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
        return [s for s in self._saved_by_kind.get(kind, []) if s.variant == s.variant]

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
        new_solution = PartialSolution(
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
        on_inverse = self.inverse
        self.set_inverse(False)
        existing = set(str(s) for s in self.solutions_for_step(sol.kind, sol.variant))
        algs = sol.step_info.solve(self.cube, len(existing) + num_solutions)
        solutions = []
        for alg in algs:
            base_alg = Algorithm(str(sol.alg))
            base_alg.merge(alg)
            s = PartialSolution(
                kind=sol.kind,
                variant=sol.variant,
                previous=sol.previous,
                alg=sol.alg.merge(alg),
            )
            if str(s) not in existing:
                solutions.append(s)
            if len(solutions) >= num_solutions:
                break
        self.set_inverse(on_inverse)
        return solutions

    def save(self) -> Optional[PartialSolution]:
        to_be_saved = self.solution
        is_solved = to_be_saved.step_info.is_solved(self.cube)
        if not is_solved:
            if to_be_saved.kind == "" or to_be_saved.previous is None:
                return None
            to_be_saved = PartialSolution(
                kind=self.solution.previous.kind,
                variant=self.solution.previous.variant,
                previous=self.solution.previous.previous,
                alg=self.solution.previous.alg.merge(self.solution.alg),
            )
            options = self.possible_next_steps(to_be_saved)
            case = self.solution.step_info.case_name(self.cube)
            if not self.get_comment(to_be_saved):
                comment = (
                    f"{self.solution.kind}{self.solution.variant}-{case}"
                    if len(options) > 1
                    else case
                )
                self.set_comment(to_be_saved, comment)
            self._continuations[to_be_saved] = (
                self.solution.kind,
                self.solution.variant,
            )
            self._orientations[to_be_saved] = self.solution.orientation
        if is_solved:
            if to_be_saved.kind in {"eo", "dr", "finish"}:
                self.reset()
            else:
                self.advance()
        self.save_solutions([to_be_saved])
        return to_be_saved

    def save_solutions(self, sols: List[PartialSolution]):
        new_sols_by_key = defaultdict(list)

        def sort_key(sol):
            return (
                sol.full_alg().len(),
                len(sol.alg.inverse_moves()) > 0,
                len(sol.alg.normal_moves()) > 0,
                str(sol.alg),
            )

        for s in sols:
            new_sols_by_key[s.kind].append(s)
        for kind, sols_for_kind in new_sols_by_key.items():
            existing = self._saved_by_kind[kind]
            existing_algs = set(str(s.full_alg()) for s in existing)
            existing += [
                s for s in sols_for_kind if not str(s.full_alg()) in existing_algs
            ]
            existing.sort(key=sort_key)
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


def step_name(kind, variant):
    s = kind
    if s not in {"htr", "fr", "slice"}:
        s = f"{s}{variant}"
    return s


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
    def default_for(sol: PartialSolution):
        d = VARIANT_ORIENTATIONS.get(sol.kind, VARIANT_ORIENTATIONS.get("*"))
        orientation = Orientation(*d.get(sol.variant, d.get("*")))
        if sol.previous is not None:
            if sol.previous.kind == "eo":
                if orientation.front not in sol.previous.variant:
                    orientation = orientation.y(1)
            else:
                orientation = Orientation(
                    sol.previous.orientation.top, sol.previous.orientation.front
                )
        return orientation
