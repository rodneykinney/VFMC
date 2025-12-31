import dataclasses
import sys
from functools import cached_property

FULLY_REDUCED = ("", "R2", "F2", "U2 R2", "U2 F2", "R2 U2 F2")
NEARLY_REDUCED = tuple(f"{t} U2".strip() for t in FULLY_REDUCED)
TWO_MOVERS = {
    ("U", "U'"): [], ("U'", "U"): [],
    ("U", "U2"): ["U'"], ("U2", "U"): ["U'"],
    ("U'", "U2"): ["U"], ("U2", "U'"): ["U"],
    ("R2", "R2"): [], ("F2", "F2"): [], ("U2", "U2"): [],
    ("U", "U"): ["U2"], ("U'", "U'"): ["U2"]
}
THREE_MOVERS = {
    ("R2", "U2", "R2"): ["U2", "R2", "U2"],
    ("F2", "U2", "F2"): ["U2", "F2", "U2"],
    ("F2", "U2", "R2"): ["U2", "R2", "U2", "F2", "U2"],
}
CORNER_SWAP_INSERTION = {
    ("R2", "F2"): ["F2"],
    ("F2", "R2"): ["R2"],
}
CORNER_SWAP_EFFECT = {
    "F2": "R2",
    "R2": "F2",
    "U": "U'",
    "U'": "U"
}


class HtrPart:
    def __init__(self, moves):
        self.moves = moves if isinstance(moves, list) else moves.split(" ") if moves else []

    @property
    def alg(self):
        return " ".join(self.moves)

    def __repr__(self):
        return self.alg

    def inverse(self) -> "HtrPart":
        inverse_moves = [
            U_MOVES[1 - U_MOVES.index(m)] if m in U_MOVES else m for m in reversed(self.moves)]
        return HtrPart(inverse_moves)

    def reduce(self) -> tuple[str, bool]:
        alg = " ".join(self.moves)
        corner_swap_parity = False
        iterations = 0
        while alg not in FULLY_REDUCED + NEARLY_REDUCED:
            moves = alg.split(" ")
            i = 1
            while i < len(moves):
                iterations += 1 if i == 1 else 0
                if iterations > 100:
                    raise Exception("Not converging")
                reduction = TWO_MOVERS.get(tuple[str, str](moves[i - 1:i + 1]))
                if reduction is not None:
                    moves = moves[:i - 1] + reduction + moves[i + 1:]
                    i = 1
                    continue
                reduction = THREE_MOVERS.get(tuple[str, str, str](moves[i - 2:i + 1]))
                if reduction is not None:
                    moves = moves[:i - 2] + reduction + moves[i + 1:]
                    i = 1
                    continue
                reduction = CORNER_SWAP_INSERTION.get(tuple[str, str](moves[i - 1:i + 1]))
                if reduction is not None:
                    corner_swap_parity = not corner_swap_parity
                    moves = (moves[:i - 1] + reduction +
                             [CORNER_SWAP_EFFECT.get(m, m) for m in moves[i + 1:]])
                    i = 1
                    continue
                i += 1
            alg = " ".join(moves)
        return (alg, corner_swap_parity)


class DrSolution:
    def __init__(self, parts: list[HtrPart]):
        self.parts = parts

    @cached_property
    def alg(self) -> str:
        alg = " U ".join(" ".join(p.moves) for p in self.parts).strip()
        alg = alg.replace("U2 U U2", "U").replace("U2 U", "U'").replace("U U2", "U'")
        return alg

    @staticmethod
    def parse(alg: str) -> "DrSolution":
        alg = normalize(alg)
        moves = alg.split(" ")
        # Put into <htr-part> U <htr-part> ... U <htr_part> form
        parts = []
        current_part = HtrPart("")
        for m in moves:
            if m in U_MOVES:
                if parts and current_part.reduce()[0] in ("", "U2"):
                    combined_moves = parts[-1].moves + ["U"] + current_part.moves + [m]
                    current_part = HtrPart(combined_moves)
                    parts = parts[:-1]
                else:
                    parts.append(current_part)
                    current_part = HtrPart([]) if m == "U" else HtrPart(["U2"])
            else:
                if current_part.moves:
                    current_part.moves.append(m)
                else:
                    current_part = HtrPart([m])
        parts.append(current_part)
        return DrSolution(parts)

    def reduce(self) -> "DrSolution":
        reduced_parts = []
        corner_swap_parity = False
        for seq in self.parts:
            if corner_swap_parity:
                moves = ["U2"] + [CORNER_SWAP_EFFECT.get(m, m) for m in seq.moves]
                seq = HtrPart(moves)
            reduction, parity = seq.reduce()
            corner_swap_parity ^= parity
            seq = HtrPart(reduction)
            reduced_parts.append(seq)
        if reduced_parts and reduced_parts[-1].moves[-4:] == ["R2", "U2", "F2", "U2"]:
            # Move trailing U2 to beginning of final part
            moves = ([] if reduced_parts[-1].moves[0] == "U2" else ["U2"]) + ["F2", "U2", "R2"]
            reduced_parts[-1] = HtrPart(moves)
        if reduced_parts and reduced_parts[0].moves[:4] == ["U2", "R2", "U2", "F2"]:
            # Move leading U2 to end of first part
            moves = ["F2", "U2", "R2"] + reduced_parts[0].moves[4:]
            reduced_parts[0] = HtrPart(moves)
        return DrSolution(reduced_parts)


def normalize(alg: str) -> str:
    """Reduce solution to RUF moveset and remove slice insertions"""
    moves = alg.split(" ")
    if set(moves) & DR_BREAKING:
        return alg

    transforms = ["1" for _ in moves]

    canonical = []

    for i in range(0, len(moves)):
        # Transformed move based on center permutation
        move_t = CENTER_TRANSFORMS[transforms[i]].get(moves[i], moves[i])
        if move_t not in RUF_MOVES:
            # Widen the move
            move_t = WIDENED_MOVES[move_t]
            t = WIDENING_TRANSFORMS[moves[i]]
            for ii in range(i + 1, len(moves)):
                transforms[ii] = CENTER_MULT[transforms[ii]].get(t, t)
        if canonical and move_t == "U2" and canonical[-1] in U_MOVES:
            canonical[-1] = U_MOVES[1 - U_MOVES.index(canonical[-1])]
        else:
            canonical.append(move_t)
    canon = " ".join(canonical)
    return canon


# The DR Center permutation group has 5 generators: E2, M2, S2, E, E'
# It has 7 members: 1, E2, M2, S2, E, E', EM2, ES2

# Multiplication tables for DR center permutations
CENTER_MULT = {
    "1": {},
    "M2": {
        "E2": "S2",
        "M2": "1",
        "S2": "E2",
        "E": "ES2",
        "EP": "EM2"
    },
    "S2": {
        "E2": "M2",
        "M2": "E2",
        "S2": "1",
        "E": "EM2",
        "EP": "ES2",

    },
    "E2": {
        "E2": "1",
        "M2": "S2",
        "S2": "M2",
        "E": "EP",
        "EP": "E",
    },
    "E": {
        "E2": "EP",
        "M2": "EM2",
        "S2": "ES2",
        "E": "E2",
        "EP": "1",
    },
    "EP": {
        "E2": "E",
        "M2": "ES2",
        "S2": "EM2",
        "E": "1",
        "EP": "E2",

    },
    "EM2": {
        "E2": "ES2",
        "M2": "E",
        "S2": "EP",
        "E": "M2",
        "EP": "S2",

    },
    "ES2": {
        "E2": "EM2",
        "M2": "EP",
        "S2": "E",
        "E": "S2",
        "EP": "M2",
    },
}

# Transformations of moves based on DR center permutation
# (missing moves are unchanged)
UD_SWAP = {"U": "D", "U'": "D'", "U2": "D2",
           "D": "U", "D'": "U'", "D2": "U2"}
RL_SWAP = {"R2": "L2", "L2": "R2"}
FB_SWAP = {"F2": "B2", "B2": "F2"}
CENTER_TRANSFORMS = {
    "1": {},
    "M2": UD_SWAP | FB_SWAP,
    "S2": UD_SWAP | RL_SWAP,
    "E2": FB_SWAP | RL_SWAP,
    "E": {"F2": "L2", "L2": "B2", "B2": "R2", "R2": "F2"},
    "EP": {"F2": "R2", "R2": "B2", "B2": "L2", "L2": "F2"},
    "EM2": UD_SWAP | {"F2": "R2", "R2": "F2", "B2": "L2", "L2": "B2"},
    "ES2": UD_SWAP | {"F2": "L2", "L2": "F2", "B2": "R2", "R2": "B2"},
}

RUF_MOVES = ("R2", "F2", "U", "U'", "U2")
U_MOVES = ("U", "U'")
DR_BREAKING = {"R", "R'", "L", "L'", "F", "F'", "B", "B'"}
WIDENED_MOVES = {
    "D2": "U2",
    "D": "U",
    "D'": "U'",
    "L2": "R2",
    "B2": "F2",
}
WIDENING_TRANSFORMS = {
    "R2": "M2",
    "L2": "M2",
    "F2": "S2",
    "B2": "S2",
    "U2": "E2",
    "U": "EP",
    "U'": "E",
    "D2": "E2",
    "D": "E",
    "D'": "EP",
}

if __name__ == "__main__":
    alg = sys.argv[1] if len(sys.argv) == 2 else " ".join(sys.argv[1:])
    print(alg)
    sol = DrSolution.parse(alg)
    skeleton = sol.reduce()
    print(skeleton.alg)
