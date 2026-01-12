"""
This script takes a list of DR-to-Finish solutions
and groups them by the corresponding corner skeleton.

For each solution, it gives the number of additional moves (over the minimum)
that the solution inserts within each half-turn section of the skeleton.

You can pipe the output of nissy directly to this script, e.g.:

$ nissy scramble dr | nissy solve drfin -M 14 -i | python skeleton.py
R2 U' R2 U2 F2 U' R2 U' R2 U (10)
        B2 L2 U L2 D2 F2 D B2 D F2 R2 U (12) +1+0+0+1+0
        B2 L2 U' B2 U2 L2 U D2 R2 D L2 F2 D (13) +1+0+0+1+0 E-slice +1
U' R2 U' R2 U R2 U F2 U' F2 U (11)
        U D2 R2 D' L2 U B2 U F2 D' F2 B2 L2 U (14) +0+0+0+0+0+2+0 E-slice +1
U R2 U R2 U R2 U F2 U' F2 U' R2 U2 [R2 F2 R2] (13)
        U L2 D L2 D F2 U B2 D' L2 F2 U B2 U2 (14) +0+0+0+0+0+1+0

This scramble is a 2c4 corner case.
There is one 10-move skeleton that yields a 12-move and 13-move solution
There is one 6-qt, 11-move skeleton that yields a 14-move solution
There is one 6-qt, 13-move skeleton that yields a 14-move solution
Although there are many other possible 4qt corner skeletons, all of them lead
to solutions with > 14 moves.
"""

import math
from dataclasses import dataclass, field
import sys
import re
from functools import cached_property
from typing import Callable

DR_MOVES = ["F2", "R2", "B2", "L2", "U", "U'", "U2", "D", "D'", "D2"]


@dataclass
class DrSolution:
    moves: list[str]
    centers: list[str] = field(default_factory=lambda: DR_MOVES)

    def replace(self, start_pos: int, end_pos: int, replacement: tuple,
                center_transform: Callable) -> "DrSolution":
        """Replace a set of moves with a different sequence, and apply some center transform to the remaining moves"""
        transformed_centers = center_transform(DR_MOVES)
        before = self.moves[:start_pos] + [m for m in replacement]
        after = [transformed_centers[DR_MOVES.index(m)] for m in self.moves[end_pos:]]
        return DrSolution(before + after, center_transform(self.centers))

    def simplify(self, is_simplified: Callable[["DrSolution"], bool],
                 substitutions: dict[tuple, tuple]) -> "DrSolution":
        """Simplify this solution by substituting move sequences until it meets some criterion"""
        norm = DrSolution(list(self.moves), self.centers)
        sequence_lengths = set(len(k) for k in substitutions.keys())
        seen = set()
        while not is_simplified(norm):
            if norm.alg in seen:
                raise Exception("Not converging")
            seen.add(norm.alg)
            for i in range(len(norm.moves)):
                sub, n = None, min(sequence_lengths)
                while sub is None and n <= max(sequence_lengths):
                    sub = substitutions.get(tuple(norm.moves[i - n + 1:i + 1]))
                    if sub:
                        replacement_seq, center_transform = sub
                        norm = norm.replace(i - n + 1, i + 1, replacement_seq,
                                            center_transform)
                    n += 1
                if sub:
                    break
        return norm

    @staticmethod
    def parse(alg: str) -> "DrSolution":
        return DrSolution(alg.split(" "))

    @cached_property
    def alg(self):
        return " ".join(self.moves)

    @cached_property
    def annotated_alg(self) -> str:
        return f"{self.alg}{' [R2 F2 R2]' if self.corner_swap_parity else ''}"

    @cached_property
    def corner_swap_parity(self) -> bool:
        """If true, then an R2 F2 R2 corner swap is needed to fully solve corners"""
        return self.centers[4] not in ("U", "D")

    @cached_property
    def additional_section_moves(self) -> tuple:
        """The number of addition moves in each HTR section of the corner skeleton"""
        sections = self.leave_slice.htr_sections
        skeleton_sections = self.minimal_corner_skeleton.htr_sections
        assert len(sections) == len(skeleton_sections)
        return tuple(len(s) - len(ss) for s, ss in zip(sections, skeleton_sections))

    @cached_property
    def entropy(self) -> float:
        """A measure of how smoothly the addition section moves are distributed between the sections"""
        counts = self.additional_section_moves
        total = sum(counts)
        return -sum(c / total * math.log(c / total) for c in counts if c)

    @cached_property
    def qt_positions(self) -> tuple:
        """
        The index of the quarter-turn moves in this solution
        Ignores net-zero-qt sequences such as U R2 L2 U
        """
        moves = self.moves
        pos = []
        for i in range(len(moves)):
            if moves[i] in ("U", "U'", "D", "D'"):
                if pos and DrSolution(moves[pos[-1] + 1:i]).simplify(is_minimal_htr_section,
                                                                     CORNER_INVARIANT).moves in (
                        [], ["U2"]):
                    pos = pos[:-1]
                else:
                    pos.append(i)
        return tuple(pos)

    @cached_property
    def htr_sections(self) -> list[list[str]]:
        """The HTR sequences of moves in between each quarter turn"""
        moves = self.alg.split(" ")
        boundaries = self.qt_positions + (len(moves),)
        sections = [moves[:boundaries[0]]] + [moves[a + 1:b] for a, b in
                                              zip(boundaries[0:], boundaries[1:])]
        return sections

    @cached_property
    def leave_slice(self) -> "DrSolution":
        """
        The shortest equivalent algorithm that leaves the E slice unsolved
        (up to rotations)
        """
        ls = self.simplify(has_no_slice_insertions, D_WIDENINGS | RUF_CANCELLATIONS)
        return ls

    @cached_property
    def ruf_corner_skeleton(self) -> "DrSolution":
        """The equivalent skeleton that uses only RUF moves"""
        return self.simplify(uses_ruf_only, D_WIDENINGS | LB_WIDENINGS)

    @cached_property
    def normalized_corner_skeleton(self) -> "DrSolution":
        """
        The normalized corner skeleton uniquely identifies the hyper-parity path taken to solve corners, up to rotations and corner swaps
        It is not the minimum-move corner skeleton because that is not unique if the solution contains R2 U2 F2 sequences
        """
        skel = self.ruf_corner_skeleton.simplify(is_normal_corner_solution, CORNER_INVARIANT)
        return skel

    @cached_property
    def minimal_corner_skeleton(self) -> "DrSolution":
        """
        A sequence that solves corners, up to rotations and corner swaps, in the minimum number of moves
        """
        skel = self.normalized_corner_skeleton
        if "R2 U2 F2" not in skel.alg:
            return skel
        if skel.alg.endswith("R2 U2 F2 U2"):
            skel = skel.simplify(is_minimal_corner_solution, FR_FINISH)
        if skel.corner_swap_parity:
            skel = skel.simplify(
                lambda sol: is_minimal_corner_solution(sol) and not sol.corner_swap_parity,
                CORNER_SWAP_ELIMINATION)
        return skel


##################################################
# Various simplifications of the complete solution
def uses_ruf_only(sol: DrSolution) -> bool:
    return re.match(r"""^(U|U'|U2|R2|F2)*$""", "".join(sol.moves)) is not None


def has_no_slice_insertions(sol: DrSolution) -> bool:
    return re.match(r""".*[UD]('|2)?[UD]('|2)?.*""", "".join(sol.moves)) is None


def is_minimal_corner_solution(sol: DrSolution) -> bool:
    return re.match(
        r"""^(R2|F2|U2R2|U2F2|R2U2F2|F2U2R2)?((U|U')(R2|F2|R2U2F2|F2U2R2))*((U|U')(R2|R2U2|F2|F2U2|R2U2F2|F2U2R2)?)?$""",
        "".join(sol.moves)) is not None


def is_normal_corner_solution(sol: DrSolution) -> bool:
    return re.match(
        r"""^(R2|F2|U2R2|U2F2|R2U2F2)?(UR2|U'R2|UF2|U'F2|UR2U2F2)*(U|U'|UR2|U'R2|UR2U2|U'R2U2|UF2|U'F2|UF2U2|U'F2U2|UR2U2F2|UR2U2F2U2)?$""",
        "".join(sol.moves)) is not None


def is_minimal_htr_section(sol: DrSolution) -> bool:
    return re.match(r"""^(U2)?(R2|F2|R2U2F2)?(U2)?$""", "".join(sol.moves)) is not None


##################################################


##################################################
# Center transforms that correspond to move-widenings/slice-insertions
def null(centers: list[int]) -> list[int]:
    return centers


def e(centers: list[int]) -> list[int]:
    return centers[3:4] + centers[:3] + centers[4:]


def eprime(centers: list[int]) -> list[int]:
    return centers[1:4] + centers[:1] + centers[4:]


def e2(centers: list[int]) -> list[int]:
    return centers[2:4] + centers[0:2] + centers[4:]


def s2(centers: list[int]) -> list[int]:
    return [centers[0], centers[3], centers[2], centers[1]] + centers[7:10] + centers[4:7]


def m2(centers: list[int]) -> list[int]:
    return [centers[2], centers[1], centers[0], centers[3]] + centers[7:10] + centers[4:7]


# The effect of a corner swaps on subsequent moves can be represented
# with a transformation of centers, in the same was as a slice insertion
def corner_swap(centers: list[int]) -> list[int]:
    return [centers[1], centers[0], centers[3], centers[2]] + [centers[5], centers[4], centers[6],
                                                               centers[8],
                                                               centers[7], centers[9]]
##################################################


##################################################
# Different move substitions that simplify the solution,
# while leaving the corners unchanged (up to rotations and corner swaps)
D_WIDENINGS: dict[tuple, tuple] = {
    ("D",): (("U",), e),
    ("D'",): (("U'",), eprime),
    ("D2",): (("U2",), e2),
}
LB_WIDENINGS: dict[tuple, tuple] = {
    ("B2",): (("F2",), s2),
    ("L2",): (("R2",), m2),
}
RUF_CANCELLATIONS: dict[tuple, tuple] = {
    ("R2", "R2"): ((), null),
    ("U2", "U2"): ((), null),
    ("F2", "F2"): ((), null),

    ("U", "U'"): ((), null),
    ("U", "U"): (("U2",), null),
    ("U'", "U'"): (("U2",), null),
    ("U'", "U"): ((), null),

    ("U", "U2"): (("U'",), null),
    ("U2", "U"): (("U'",), null),
    ("U'", "U2"): (("U",), null),
    ("U2", "U'"): (("U",), null),
}
CORNER_SWAPS: dict[tuple, tuple] = {
    ("R2", "F2"): (("F2",), corner_swap),
    ("F2", "R2"): (("R2",), corner_swap),
}
EDGE_PERMS: dict[tuple, tuple] = {
    ("R2", "U2", "R2"): (("U2", "R2", "U2"), null),
    ("F2", "U2", "F2"): (("U2", "F2", "U2"), null),
    ("F2", "U2", "R2"): (("R2", "U2", "F2", "U2"), corner_swap),
    ("U2", "R2", "U2", "F2"): (("R2", "U2", "F2",), corner_swap),
    ("U'", "R2", "U2", "F2"): (("U", "R2", "U2", "F2"), corner_swap),
}
FR_FINISH: dict[tuple, tuple] = {
    ("U", "R2", "U2", "F2", "U2"): (("U", "F2", "U2", "R2"), corner_swap),
}
CORNER_SWAP_ELIMINATION: dict[tuple, tuple] = {
    ("R2", "U2", "F2", "U"): (("F2", "U2", "R2", "U"), corner_swap),
    ("R2", "U2", "F2", "U'"): (("F2", "U2", "R2", "U'"), corner_swap),
    ("U", "R2", "U2", "F2"): (("U'", "R2", "U2", "F2"), corner_swap),
    ("U", "F2", "U2", "R2"): (("U'", "F2", "U2", "R2"), corner_swap),
}
CORNER_INVARIANT: dict[tuple, tuple] = (
        D_WIDENINGS | LB_WIDENINGS | RUF_CANCELLATIONS | CORNER_SWAPS | EDGE_PERMS)
##################################################

if __name__ == "__main__":
    if len(sys.argv) > 1:
        lines = [sys.argv[1].split("(")[0].strip()]
    else:
        lines = [l.split("(")[0].strip() for l in sys.stdin.readlines()]
    skeletons: list[tuple[str, list[DrSolution]]] = []
    for line in lines:
        if next((m for m in line.split(" ") if m not in DR_MOVES), None):
            continue
        sol = DrSolution(line.split(" "))
        match = next((l for s, l in skeletons if s == sol.normalized_corner_skeleton.alg), None)
        if match:
            if sol.leave_slice.ruf_corner_skeleton.alg not in [s.leave_slice.ruf_corner_skeleton.alg
                                                               for s in match]:
                match.append(sol)
        else:
            skeletons.append((sol.normalized_corner_skeleton.alg, [sol]))

    for norm, l in skeletons:
        sorted = l.sort(key=lambda sol: (len(sol.moves), sol.entropy))
        print(
            f"{l[0].minimal_corner_skeleton.annotated_alg} ({len(l[0].minimal_corner_skeleton.moves)})")
        for sol in l:
            print(
                f"\t{sol.alg} ({len(sol.moves)}) +{'+'.join((str(n) for n in sol.additional_section_moves))}{'' if len(sol.leave_slice.moves) == len(sol.moves) else f' E-slice +{len(sol.moves) - len(sol.leave_slice.moves)}'}")
