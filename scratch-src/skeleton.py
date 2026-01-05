from dataclasses import dataclass
import sys
from functools import cached_property
from typing import Callable

DR_MOVES = ["F2", "R2", "B2", "L2", "U", "U'", "U2", "D", "D'", "D2"]
MINIMAL_HTR_SECTION = ([], ["R2"], ["F2"], ["R2", "U2", "F2"])


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
    ("F2", "U2", "R2"): (("U2", "R2", "U2", "F2", "U2"), null),
    ("U2", "R2", "U2", "F2"): (("R2", "U2", "R2", "F2"), null),
}
CORNER_INVARIANT: dict[
    tuple, tuple] = D_WIDENINGS | LB_WIDENINGS | RUF_CANCELLATIONS | CORNER_SWAPS | EDGE_PERMS


@dataclass
class DrSolution:
    alg: str

    @cached_property
    def annotated_corner_skeleton(self) -> str:
        sections = self.leave_slice.htr_sections
        skeleton_sections = self.corner_skeleton.htr_sections
        assert len(sections) == len(skeleton_sections)
        return self.corner_skeleton.alg

    @cached_property
    def additions_section_moves(self) -> tuple:
        sections = self.leave_slice.htr_sections
        skeleton_sections = self.corner_skeleton.htr_sections
        assert len(sections) == len(skeleton_sections)
        return tuple(len(s) - len(ss) for s, ss in zip(sections, skeleton_sections))

    @cached_property
    def qt_positions(self) -> tuple:
        moves = self.alg.split(" ")
        pos = []
        for i in range(len(moves)):
            if moves[i] in ("U", "U'", "D", "D'"):
                if pos and normalize(moves[pos[-1] + 1:i], is_minimal_htr_section,
                                     CORNER_INVARIANT) in ([], ["U2"]):
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
        moves = self.alg.split(" ")
        moves = normalize(moves, has_no_slice_insertions, D_WIDENINGS | RUF_CANCELLATIONS)
        return DrSolution(" ".join(moves))

    @cached_property
    def corner_skeleton(self) -> "DrSolution":
        skel = normalize(self.alg.split(" "), is_minimal_corner_solution, CORNER_INVARIANT)
        skel = normalize(skel, has_no_trailing_u2,
                         {("R2", "U2", "F2", "U2"): (("F2", "U2", "R2"), corner_swap), })
        return DrSolution(" ".join(skel))


def has_no_trailing_u2(moves: list[str]) -> bool:
    return moves[-4:] != ["R2", "U2", "F2", "U2"]

def has_no_slice_insertions(moves: list[str]) -> bool:
    moves = [m.replace("'","").replace("D","U") for m in moves]
    slice_insertions = next((True for a,b in zip(moves,moves[1:]) if (a,b) in (("U","U"),("U","U2"), ("U2","U"))), None)
    return slice_insertions is None

def is_minimal_corner_solution(moves: list[str]) -> bool:
    sections = DrSolution(" ".join(moves)).htr_sections
    if sections[0][:1] == ["U2"]:
        sections[0] = sections[0][1:]
    if sections[-1][-1:] == ["U2"]:
        sections[-1] = sections[-1][:-1]
    not_reduced = next((s for s in sections if s not in MINIMAL_HTR_SECTION), None)
    return not_reduced is None


def is_minimal_htr_section(moves: list[str]) -> bool:
    if moves[:1] == ["U2"]:
        moves = moves[1:]
    if moves[-1:] == ["U2"]:
        moves = moves[:-1]
    return moves in MINIMAL_HTR_SECTION


def normalize(moves: list[str], has_normal_form: Callable[[list[str]], bool],
              substitutions: dict[tuple, tuple]) -> list[str]:
    norm_moves = moves
    sequence_lengths = set(len(k) for k in substitutions.keys())
    seen = set()
    while not has_normal_form(norm_moves):
        m = tuple(norm_moves)
        if m in seen:
            raise Exception("Not converging")
        seen.add(m)
        move_names = DR_MOVES
        for i in range(len(norm_moves)):
            sub, n = None, min(sequence_lengths)
            while sub is None and n <= max(sequence_lengths):
                sub = substitutions.get(tuple(norm_moves[i - n + 1:i + 1]))
                if sub:
                    replacement_seq, center_transform = sub
                    move_names = center_transform(move_names)
                    before = norm_moves[:i - n + 1] + [m for m in replacement_seq]
                    after = [move_names[DR_MOVES.index(m)] for m in norm_moves[i + 1:]]
                    norm_moves = before + after
                n += 1
            if sub:
                break
    return norm_moves


if __name__ == "__main__":
    alg = sys.argv[1] if len(sys.argv) == 2 else " ".join(sys.argv[1:])
    print(alg)
    sol = DrSolution(alg)
    skeleton = sol.corner_skeleton
    print(skeleton.alg)
