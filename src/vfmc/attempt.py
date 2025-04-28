import math
from typing import Optional, Dict, List, Callable, Set, Tuple
from collections import defaultdict

from vfmc.palette import Visibility
from vfmc_core import Algorithm, StepInfo, debug, Cube


class PartialSolution:
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
        d = VARIANT_ORIENTATIONS.get(kind, VARIANT_ORIENTATIONS.get("*"))
        self.orientation = Orientation(*d.get(variant, d.get("*")))
        if self.previous is not None:
            if self.previous.kind == "eo":
                if self.orientation.front not in self.previous.variant:
                    self.orientation.y(1)
            else:
                self.orientation = Orientation(
                    self.previous.orientation.top, self.previous.orientation.front
                )

    def append(self, alg: Algorithm):
        self.alg = self.alg.merge(alg)

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
    def __init__(self):
        self.scramble = ""
        self.cube = Cube("")
        self.inverse = False
        self.solution = PartialSolution()
        self._saved_by_kind: Dict[str, List[PartialSolution]] = defaultdict(list)
        self._done: Set[PartialSolution] = set()
        self._comments: Dict[PartialSolution, str] = {}
        self._cube_listeners = []
        self._saved_solution_listeners = []
        self._solution_attribute_listeners = []

    def set_scramble(self, s):
        self._saved_by_kind.clear()
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
        if not self.solution.allows_moves(alg):
            return False

        self.solution.append(alg)
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

    def solutions_by_kind(self) -> Dict[str, List[PartialSolution]]:
        return self._saved_by_kind

    def solutions_for_step(self, kind: str, variant: str) -> List[PartialSolution]:
        return [s for s in self._saved_by_kind.get(kind, []) if s.variant == s.variant]

    def corner_visibility(self) -> List[Tuple[Visibility, Visibility, Visibility]]:
        return [
            (Visibility(t[0]), Visibility(t[1]), Visibility(t[2]))
            for t in self.solution.step_info.corner_visibility(self.cube)
        ]

    def edge_visibility(self) -> List[Tuple[Visibility, Visibility]]:
        return [
            (Visibility(t[0]), Visibility(t[1]))
            for t in self.solution.step_info.edge_visibility(self.cube)
        ]

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

    def save(self):
        self.save_solution(self.solution)

    def save_solution(self, sol: PartialSolution):
        self.save_solutions([sol])

    def save_solutions(self, sols: List[PartialSolution]):
        new_sols_by_key = defaultdict(list)
        for s in sols:
            new_sols_by_key[s.kind].append(s)
        for kind, sols_for_kind in new_sols_by_key.items():
            existing = self._saved_by_kind[kind]
            existing_algs = set(str(s.full_alg()) for s in existing)
            existing += [
                s for s in sols_for_kind if not str(s.full_alg()) in existing_algs
            ]
            existing.sort(key=lambda s: (s.full_alg().len(), s.variant))
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
        for l in self._saved_solution_listeners:
            l()

    def notify_solution_attribute_listeners(self):
        for l in self._solution_attribute_listeners:
            l()

    def notify_cube_listeners(self):
        for l in self._cube_listeners:
            l()


def step_name(kind, variant):
    s = kind
    if s not in {"htr", "fr", "slice"}:
        s = f"{s}{variant}"
    return s


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

AXIS_ROTATIONS = {
    "f": ["u", "l", "d", "r"],
    "b": ["u", "r", "d", "l"],
    "r": ["u", "f", "d", "b"],
    "l": ["u", "b", "d", "f"],
    "u": ["f", "r", "b", "l"],
    "d": ["f", "l", "b", "r"],
}


class Orientation:
    def __init__(self, top: str, front: str):
        self.top = top
        self.front = front

    def x(self, ticks: int):
        rot = AXIS_ROTATIONS[self.right]
        self.top = rot[(rot.index(self.top) + ticks) % 4]
        self.front = rot[(rot.index(self.front) + ticks) % 4]

    @property
    def right(self):
        rot = AXIS_ROTATIONS[self.top]
        return rot[(rot.index(self.front) + 1) % 4]

    def z(self, ticks: int):
        rot = AXIS_ROTATIONS[self.front]
        self.top = rot[(rot.index(self.top) + ticks) % 4]

    def y(self, ticks: int):
        rot = AXIS_ROTATIONS[self.top]
        self.front = rot[(rot.index(self.front) + ticks) % 4]

    def __repr__(self):
        return f"top={self.top}, front={self.front}"
