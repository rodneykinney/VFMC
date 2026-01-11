import math
from dataclasses import dataclass, field
import sys
import re
from functools import cached_property
from typing import Callable

DR_MOVES = ["F2", "R2", "B2", "L2", "U", "U'", "U2", "D", "D'", "D2"]


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


def corner_swap(centers: list[int]) -> list[int]:
    return [centers[1], centers[0], centers[3], centers[2]] + [centers[5], centers[4], centers[6],
                                                               centers[8],
                                                               centers[7], centers[9]]


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


@dataclass
class DrSolution:
    moves: list[str]
    centers: list[str] = field(default_factory=lambda: DR_MOVES)

    def replace(self, start_pos: int, end_pos: int, replacement: tuple,
                center_transform: Callable) -> "DrSolution":
        transformed_centers = center_transform(DR_MOVES)
        before = self.moves[:start_pos] + [m for m in replacement]
        after = [transformed_centers[DR_MOVES.index(m)] for m in self.moves[end_pos:]]
        return DrSolution(before + after, center_transform(self.centers))

    def simplify(self, is_simplified: Callable[["DrSolution"], bool],
                 substitutions: dict[tuple, tuple]) -> "DrSolution":
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

    def denormalized(self) -> "DrSolution":
        moves = []

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
        return self.centers[4] not in ("U", "D")

    @cached_property
    def additional_section_moves(self) -> tuple:
        sections = self.leave_slice.htr_sections
        skeleton_sections = self.minimal_corner_skeleton.htr_sections
        assert len(sections) == len(skeleton_sections)
        return tuple(len(s) - len(ss) for s, ss in zip(sections, skeleton_sections))

    @cached_property
    def entropy(self) -> float:
        counts = self.additional_section_moves
        total = sum(counts)
        return -sum(c / total * math.log(c / total) for c in counts if c)

    @cached_property
    def qt_positions(self) -> tuple:
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
        moves = self.alg.split(" ")
        boundaries = self.qt_positions + (len(moves),)
        sections = [moves[:boundaries[0]]] + [moves[a + 1:b] for a, b in
                                              zip(boundaries[0:], boundaries[1:])]
        return sections

    @cached_property
    def leave_slice(self) -> "DrSolution":
        ls = self.simplify(has_no_slice_insertions, D_WIDENINGS | RUF_CANCELLATIONS)
        return ls

    @cached_property
    def ruf_corner_skeleton(self) -> "DrSolution":
        return self.simplify(uses_ruf_only, D_WIDENINGS | LB_WIDENINGS)

    @cached_property
    def normalized_corner_skeleton(self) -> "DrSolution":
        skel = self.ruf_corner_skeleton.simplify(is_normal_corner_solution, CORNER_INVARIANT)
        return skel

    @cached_property
    def minimal_corner_skeleton(self) -> "DrSolution":
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


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # lines = [sys.argv[1].split("(")[0].strip()]
        lines = [l.split("(")[0].strip() for l in open(sys.argv[1]).readlines()]
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
        best = l[0]
        print(
            f"{best.minimal_corner_skeleton.annotated_alg} ({len(best.minimal_corner_skeleton.moves)})")
        for sol in l:
            print(
                f"\t{sol.alg} ({len(sol.moves)}) +{'+'.join((str(n) for n in sol.additional_section_moves))}")
