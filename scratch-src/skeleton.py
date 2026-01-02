from dataclasses import dataclass, field
import sys



@dataclass()
class HtrPart:
    moves: list[str] = field(default_factory=lambda: [])
    corner_swap_parity: bool = False

    @staticmethod
    def parse(alg: str) -> "HtrPart":
        return HtrPart(alg.split(" "), False)

    @property
    def alg(self):
        return " ".join(self.moves)

    def __repr__(self):
        return self.alg

    def inverse(self) -> "HtrPart":
        inverse_moves = [
            U_MOVES[1 - U_MOVES.index(m)] if m in U_MOVES else m for m in reversed(self.moves)]
        return HtrPart(inverse_moves)

    def replace(self, end_position: int, length: int, substitution: "HtrPart") -> "HtrPart":
        before = self.moves[:end_position - length + 1]
        after = [CORNER_SWAP_EFFECT.get(m, m) for m in self.moves[end_position + 1:]] if substitution.corner_swap_parity else self.moves[end_position + 1:]
        moves =  before + substitution.moves + after
        return HtrPart(moves, substitution.corner_swap_parity ^ self.corner_swap_parity)

    def reduce(self) -> "HtrPart":
        reduction = HtrPart(self.moves, self.corner_swap_parity)
        iterations = 0
        while reduction.alg not in FULLY_REDUCED + NEARLY_REDUCED:
            i = 1
            while i < len(reduction.moves):
                iterations += 1 if i == 1 else 0
                if iterations > 100:
                    raise Exception("Not converging")
                substitution, n = None, 2
                while substitution is None and n < 5:
                    substitution = SUBSTITUTIONS.get(tuple[str, str](reduction.moves[i - n + 1:i + 1]))
                    if substitution:
                        reduction = reduction.replace(i, n, substitution)
                    n += 1
                if substitution:
                    i = 1
                    continue
                i += 1
        return reduction

class DrAlgorithm:
    def __init__(self, parts: list[HtrPart]):
        self.parts = parts

    @property
    def alg(self) -> str:
        alg = " U ".join(" ".join(p.moves) for p in self.parts).strip()
        alg = alg.replace("U2 U U2", "U").replace("U2 U", "U'").replace("U U2", "U'")
        return alg

    @staticmethod
    def parse_normalized(alg: str) -> "DrAlgorithm":
        moves = alg.split(" ")
        if set(moves) & DR_BREAKING:
            raise ValueError("DR-breaking algorithm")
        non_ruf = next((m for m in moves if m not in RUF_MOVES), None)
        if non_ruf:
            raise ValueError("Expecting only RUF moves")
        # Put into <htr-part> U <htr-part> ... U <htr_part> form
        parts = []
        current_part = HtrPart()
        for m in moves:
            if m in U_MOVES:
                if parts and current_part.reduce().alg in ("", "U2"):
                    combined_moves = parts[-1].moves + ["U"] + current_part.moves + [m]
                    current_part = HtrPart(combined_moves)
                    parts = parts[:-1]
                else:
                    parts.append(current_part)
                    current_part = HtrPart() if m == "U" else HtrPart(["U2"])
            else:
                if current_part.moves:
                    current_part.moves.append(m)
                else:
                    current_part = HtrPart([m])
        parts.append(current_part)
        return DrAlgorithm(parts)

    def reduce(self) -> "DrAlgorithm":
        reduced_parts = []
        corner_swap_parity = False
        for i in range(len(self.parts)):
            part = self.parts[i]
            if corner_swap_parity:
                moves = ["U2"] + [CORNER_SWAP_EFFECT.get(m, m) for m in part.moves]
                part = HtrPart(moves)
            reduction = part.reduce()
            corner_swap_parity ^= reduction.corner_swap_parity
            if i < len(self.parts) - 1 and "U2" in reduction.moves[-1:]:
                del reduction.moves[-1]
                self.parts[i+1].moves.insert(0, "U2")
            reduced_parts.append(reduction)
        return DrAlgorithm(reduced_parts)


def leave_slice(alg: str) -> str:
    moves = alg.split(" ")
    transform = "1"
    canonical = [moves[0]]
    for previous,move in zip(moves,moves[1:]):
        move_t = CENTER_TRANSFORMS[transform].get(move,move)
        insertion = SLICE_INSERTIONS.get((previous,move)) or SLICE_INSERTIONS.get((move,previous))
        if insertion:
            r,t = insertion
            transform = CENTER_MULT[transform].get(t,t)
            canonical = canonical[:-1]
            if r:
                canonical += [r]
        else:
            canonical.append(move_t)
    return " ".join(canonical)


def normalize(alg: str) -> str:
    """Reduce solution to RUF moveset and remove slice insertions"""
    moves = alg.split(" ")
    transforms = ["1" for _ in moves]

    norm_moves = []

    for i in range(0, len(moves)):
        # Transformed move based on center permutation
        move_t = CENTER_TRANSFORMS[transforms[i]].get(moves[i], moves[i])
        if move_t not in RUF_MOVES:
            # Widen the move
            move_t = WIDENED_MOVES[move_t]
            t = WIDENING_TRANSFORMS[moves[i]]
            for ii in range(i + 1, len(moves)):
                transforms[ii] = CENTER_MULT[transforms[ii]].get(t, t)
        if norm_moves and move_t == "U2" and norm_moves[-1] in U_MOVES:
            norm_moves[-1] = U_MOVES[1 - U_MOVES.index(norm_moves[-1])]
        else:
            norm_moves.append(move_t)
    canon = " ".join(norm_moves)
    return canon

@dataclass
class DrSolutionBreakdown:
    full_alg: str
    leave_slice_alg: str
    normalized_corner_solution: str
    minimal_corner_solution: DrAlgorithm

    @property
    def report(self) -> str:
        lines = [
            f"| Solution: {self.full_alg}",
            f"| Leave slice: {self.leave_slice_alg}",
            f"| Corner skeleton: {self.minimal_corner_solution.alg}",
        ]
        max_line_length = max(len(s) for s in lines) + 2
        lines = [l + " " * (max_line_length-len(l)) + " |" for l in lines]
        hline = '\n|' + '-' *  max_line_length + "|\n"
        return hline.join([""] + lines + [""])

    @staticmethod
    def parse(alg: str) -> "DrSolutionBreakdown":
        full_alg = alg
        leave_slice_alg = leave_slice(full_alg)
        normalized_corner_solution = normalize(leave_slice_alg)
        minimal_corner_solution = DrAlgorithm.parse_normalized(normalized_corner_solution.replace("w","")).reduce()
        return DrSolutionBreakdown(
            full_alg=full_alg,
            leave_slice_alg=leave_slice_alg,
            normalized_corner_solution=normalized_corner_solution,
            minimal_corner_solution=minimal_corner_solution
        )

FULLY_REDUCED = ("", "R2", "F2", "U2 R2", "U2 F2", "R2 U2 F2")
NEARLY_REDUCED = tuple(f"{t} U2".strip() for t in FULLY_REDUCED)
SUBSTITUTIONS = {
    ("U", "U'"): HtrPart([]), ("U'", "U"): HtrPart([]),
    ("U", "U2"): HtrPart(["U'"]), ("U2", "U"): HtrPart(["U'"]),
    ("U'", "U2"): HtrPart(["U"]), ("U2", "U'"): HtrPart(["U"]),
    ("R2", "R2"): HtrPart([]), ("F2", "F2"): HtrPart([]), ("U2", "U2"): HtrPart([]),
    ("U", "U"): HtrPart(["U2"]), ("U'", "U'"): HtrPart(["U2"]),
    ("R2", "F2"): HtrPart(["F2"], True),
    ("F2", "R2"): HtrPart(["R2"], True),
    ("R2", "U2", "R2"): HtrPart(["U2", "R2", "U2"]),
    ("F2", "U2", "F2"): HtrPart(["U2", "F2", "U2"]),
    ("F2", "U2", "R2"): HtrPart(["U2", "R2", "U2", "F2", "U2"]),
    ("U2", "R2", "U2", "F2"): HtrPart(["R2", "U2", "F2"], True),
}
CORNER_SWAP_EFFECT = {
    "F2": "R2",
    "R2": "F2",
    "U": "U'",
    "U'": "U"
}



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
    "D2": "Uw2",
    "D": "Uw",
    "D'": "Uw'",
    "L2": "Rw2",
    "B2": "Fw2",
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
SLICE_INSERTIONS = {
    ("U", "D"): ("U2", "E"),
    ("U", "D'"): ("", "EP"),
    ("U'", "D"): ("", "E"),
    ("U'", "D'"): ("U2", "EP"),
    ("U", "D2"): ("U'", "E2"),
    ("U'", "D2"): ("U", "E2"),
    ("D", "U2"): ("D'", "E2"),
    ("D'", "U2"): ("D", "E2"),
}

if __name__ == "__main__":
    alg = sys.argv[1] if len(sys.argv) == 2 else " ".join(sys.argv[1:])
    print(alg)
    sol = DrAlgorithm.parse_normalized(alg)
    skeleton = sol.reduce()
    print(skeleton.alg)
