from skeleton import HtrPart, DrAlgorithm, normalize, leave_slice, DrSolutionBreakdown
import unittest

class TestSkeleton(unittest.TestCase):
    def test_htr_reduce(self):
        self.assertEqual(HtrPart(["F2"], False), HtrPart.parse("F2").reduce())
        self.assertEqual(HtrPart([], False), HtrPart.parse("F2 F2").reduce())
        self.assertEqual(HtrPart(["R2"], True), HtrPart.parse("F2 R2").reduce())
        self.assertEqual(HtrPart(["U2"], False), HtrPart.parse("U F2 F2 U").reduce())
        self.assertEqual(HtrPart(["R2"], False), HtrPart.parse("F2 R2 F2 R2 F2").reduce())
        self.assertEqual(HtrPart([], True), HtrPart.parse("U R2 F2 R2 U").reduce())
        self.assertEqual(HtrPart(["R2", "U2", "F2","U2"], False), HtrPart.parse("F2 U2 F2 R2").reduce())
        self.assertEqual(HtrPart(["U2","R2", "U2"], False), HtrPart.parse("R2 U F2 F2 U R2").reduce())
        self.assertEqual(HtrPart(["F2"], True), HtrPart.parse("R2 U U2 R2 R2 U F2").reduce())

    def test_leave_slice(self):
        self.assertEqual("U' L2 D", leave_slice("U D2 R2 D"))
        self.assertEqual("U2 F2 B2", leave_slice("U D R2 U D' B2"))

    def test_normalize(self):
        self.assertEqual("U2 R2 Uw R2 U Uw2 R2 U F2 Rw2 F2 Rw2 U' F2 U2", normalize("U2 R2 D B2 U D2 F2 U L2 B2 R2 B2 U' L2 U2"))

    def test_parse(self):
        self.assertEqual(["", "R2", "F2"], [p.alg for p in DrAlgorithm.parse("U R2 U F2").parts])
        self.assertEqual(["F2 F2", "F2", "R2"], [p.alg for p in DrAlgorithm.parse("F2 B2 U R2 U F2").parts])
        self.assertEqual(["", "R2 U F2 F2 U R2", "R2"], [p.alg for p in DrAlgorithm.parse("U R2 U F2 B2 U F2 U F2").parts])

    def test_dr_reduce(self):
        self.assertEqual(["", "F2", "R2"], [p.alg for p in DrAlgorithm.parse("F2 F2 U F2 U R2").reduce().parts])
        self.assertEqual(["", "U2 F2", "U2 R2"], [p.alg for p in DrAlgorithm.parse("U F2 U2 F2 U R2").reduce().parts])
        self.assertEqual(["", "R2 U2 F2", "F2"], [p.alg for p in DrAlgorithm.parse("U F2 U2 R2 U R2").reduce().parts])
        self.assertEqual(["", "R2 U2 F2", "U2 F2 U2"], [p.alg for p in DrAlgorithm.parse("U F2 U2 R2 U R2 U2 R2").reduce().parts])
        self.assertEqual(["", "F2", "U2 R2 U2"], [p.alg for p in DrAlgorithm.parse("U R2 F2 U F2 U2").reduce().parts])
        self.assertEqual(["", "F2", "R2 U2"], [p.alg for p in DrAlgorithm.parse("U R2 F2 U F2 U2 F2").reduce().parts])
        self.assertEqual(["", "F2", "R2 U2 F2 U2"], [p.alg for p in DrAlgorithm.parse("U R2 F2 U F2 U2 R2 U2").reduce().parts])
        self.assertEqual(["", "F2", "F2", "U2 F2", "F2", "F2"], [p.alg for p in DrAlgorithm.parse("D B2 D' R2 L2 U L2 D' R2 U R2 D' F2 U' B2").reduce().parts])
        self.assertEqual(["", "R2 U2 F2"], [p.alg for p in DrAlgorithm.parse("U R2 U D R2").reduce().parts])
        self.assertEqual(["", "U2 F2", "R2 U2 F2", "U2 F2", "R2", "F2"], [p.alg for p in DrAlgorithm.parse("U' F2 U F2 L2 U D F2 U L2 U' F2 L2 U L2").reduce().parts])

        self.assertEqual(["", "F2", "R2 U2 F2"], [p.alg for p in DrAlgorithm.parse("U F2 U' R2 U2 F2").reduce().parts])
        self.assertEqual(["", "F2", "R2 U2 F2"], [p.alg for p in DrAlgorithm.parse("R2 F2 R2 U' R2 U F2 U2 F2 R2").reduce().parts])
        self.assertEqual(["", "F2", "R2 U2 F2"], [p.alg for p in DrAlgorithm.parse("R2 F2 R2 U' R2 U R2 F2 U2 F2").reduce().parts])
        self.assertEqual(["", "F2", "R2 U2 F2"], [p.alg for p in DrAlgorithm.parse("R2 F2 R2 U' R2 U' F2 U2 R2").reduce().parts])
        self.assertEqual(["", "F2", "R2 U2 F2"], [p.alg for p in DrAlgorithm.parse("R2 F2 R2 U' R2 U R2 U2 F2 U2").reduce().parts])
        self.assertEqual(["", "F2", "R2 U2 F2"], [p.alg for p in DrAlgorithm.parse("R2 F2 R2 U' R2 U' R2 U2 R2 F2 U2").reduce().parts])

        self.assertEqual(["", "F2", "R2 U2 F2 U2"], [p.alg for p in DrAlgorithm.parse("U F2 U' R2 U2 F2 U2").reduce().parts])
        self.assertEqual(["", "F2", "R2 U2 F2 U2"], [p.alg for p in DrAlgorithm.parse("R2 F2 R2 U' R2 U F2 U2 F2 R2 U2").reduce().parts])
        self.assertEqual(["", "F2", "R2 U2 F2 U2"], [p.alg for p in DrAlgorithm.parse("R2 F2 R2 U' R2 U R2 F2 U2 F2 U2").reduce().parts])
        self.assertEqual(["", "F2", "R2 U2 F2 U2"], [p.alg for p in DrAlgorithm.parse("R2 F2 R2 U' R2 U' F2 U2 R2 U2").reduce().parts])
        self.assertEqual(["", "F2", "R2 U2 F2 U2"], [p.alg for p in DrAlgorithm.parse("R2 F2 R2 U' R2 U R2 U2 F2").reduce().parts])
        self.assertEqual(["", "F2", "R2 U2 F2 U2"], [p.alg for p in DrAlgorithm.parse("R2 F2 R2 U' R2 U' R2 U2 R2 F2").reduce().parts])

    def test_dr_solution_breakdown(self):
        sol = DrSolutionBreakdown.parse("U D R2 U D' B2 U' F2 L2 F2 R2 D' F2 D2 R2 F2 R2 B2")
        self.assertEqual("U R2 U R2 U2 F2", sol.minimal_corner_solution.alg)

    def test_debug(self):
        self.assertEqual(["", "F2", "R2 U2 F2 U2"], [p.alg for p in DrAlgorithm.parse("U F2 U' R2 U2 F2 U2").reduce().parts])
        self.assertEqual(["", "F2", "R2 U2 F2 U2"], [p.alg for p in DrAlgorithm.parse("R2 F2 R2 U' R2 U F2 U2 F2 R2 U2").reduce().parts])
        self.assertEqual(["", "F2", "R2 U2 F2 U2"], [p.alg for p in DrAlgorithm.parse("R2 F2 R2 U' R2 U R2 F2 U2 F2 U2").reduce().parts])
        self.assertEqual(["", "F2", "R2 U2 F2 U2"], [p.alg for p in DrAlgorithm.parse("R2 F2 R2 U' R2 U' F2 U2 R2 U2").reduce().parts])
        self.assertEqual(["", "F2", "R2 U2 F2 U2"], [p.alg for p in DrAlgorithm.parse("R2 F2 R2 U' R2 U R2 U2 F2").reduce().parts])
        self.assertEqual(["", "F2", "R2 U2 F2 U2"], [p.alg for p in DrAlgorithm.parse("R2 F2 R2 U' R2 U' R2 U2 R2 F2").reduce().parts])
        pass
