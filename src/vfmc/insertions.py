from dataclasses import dataclass
from typing import List
from difflib import SequenceMatcher
import re

from vfmc.orientation import AXIS_ROTATIONS, OPPOSITES
from vfmc_core import Algorithm


@dataclass
class Insertion:
    pos: int
    moves: List[str]


@dataclass
class Replacement:
    start: int
    end: int
    moves: List[str]


class Insertions:
    def __init__(self, alg: Algorithm):
        self.original = alg
        self.replacement = alg
        self.wide_alg_moves = alg.all_on_normal().normal_moves()

    def set_replacement(self, moves_str: str, pos: int):
        try:
            assert "(" not in moves_str and ")" not in moves_str
            before_cursor = parse_wide_alg(moves_str[:pos])
            after_cursor = parse_wide_alg(moves_str[pos:])
            alg = Algorithm(
                f"{' '.join(before_cursor.normalized_moves)} ({Algorithm(' '.join(after_cursor.normalized_moves)).inverted()})"
            )
            self.replacement = alg
            self.wide_alg_moves = before_cursor.wide_moves
        except Exception:
            pass

    def net_alg(self) -> Algorithm:
        return self.original.inverted().merge(self.replacement)

    def get_edits(self) -> List:
        old_moves = self.original.all_on_normal().normal_moves()
        new_moves = self.wide_alg_moves
        m = SequenceMatcher(a=old_moves, b=new_moves)
        edits = []
        for tag, i1, i2, j1, j2 in m.get_opcodes():
            if tag == "equal":
                pass
            elif tag == "replace":
                edits.append(Replacement(start=i1, end=i2, moves=new_moves[j1:j2]))
                pass
            elif tag == "delete":
                edits.append(
                    Insertion(
                        pos=i1,
                        moves=Algorithm(" ".join(old_moves[i1:i2]))
                        .inverted()
                        .normal_moves(),
                    )
                )
            elif tag == "insert":
                edits.append(Insertion(pos=i1, moves=new_moves[j1:j2]))
            else:
                raise f"Unknown tag: {tag}"
        return edits


@dataclass
class WideAlgorithm:
    wide_moves: List[str]
    normalized_moves: List[str]


def parse_wide_alg(moves_str) -> WideAlgorithm:
    """Parse an algorithm that accepts wide moves"""
    moves_str = moves_str.lower()
    alg_pattern = r"^\s*([rufldb][w]?[2']?\s*)*$"
    if not re.fullmatch(alg_pattern, moves_str):
        raise ValueError("Invalid algorithm")
    move_pattern = r"([rufldb])([w]?)([2']?)(?:\s*)"
    moves = re.findall(move_pattern, moves_str)

    def create_transform(f, r):
        rot = AXIS_ROTATIONS[f]
        ticks = 3 if r == "'" else (2 if r == "2" else 1)

        def transform(f):
            if f in rot:
                ft = rot[(rot.index(f) + ticks) % 4]
            else:
                ft = f
            return ft

        return transform

    transformations = []
    wide_moves = []
    norm_moves = []
    for face, wide, rotation in moves:
        wide_moves.append(f"{face.upper()}{wide}{rotation}")
        is_wide = wide == "w"
        for t in transformations:
            face = t(face)

        if is_wide:
            transformations.append(create_transform(face, rotation))
            face = OPPOSITES[face]

        norm_moves.append(f"{face}{rotation}")

    return WideAlgorithm(wide_moves=wide_moves, normalized_moves=norm_moves)
