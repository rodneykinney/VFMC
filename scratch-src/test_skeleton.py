from skeleton import HtrPart, DrSolution, normalize
import unittest

debug_only = True

class TestSkeleton(unittest.TestCase):
    @unittest.skipIf(debug_only, "disabled")
    def test_htr_reduce(self):
        self.assertEqual(HtrPart("F2").reduce(), ("F2", False))
        self.assertEqual(HtrPart("F2 F2").reduce(), ("", False))
        self.assertEqual(HtrPart("F2 R2").reduce(), ("R2", True))
        self.assertEqual(HtrPart("U F2 F2 U").reduce(), ("U2", False))
        self.assertEqual(HtrPart("F2 R2 F2 R2 F2").reduce(), ("R2", False))
        self.assertEqual(HtrPart("U R2 F2 R2 U").reduce(), ("", True))
        self.assertEqual(HtrPart("F2 U2 F2 R2").reduce(), ("R2 U2 F2 U2", False))
        self.assertEqual(HtrPart("R2 U F2 F2 U R2").reduce(), ("U2 R2 U2", False))
        self.assertEqual(HtrPart("R2 U U2 R2 R2 U F2").reduce(), ("F2", True))

    @unittest.skipIf(debug_only, "disabled")
    def test_normalize(self):
        self.assertEqual(normalize("U2 R2 D B2 U D2 F2 U L2 B2 R2 B2 U' L2 U2"), "U2 R2 U R2 U' R2 U F2 R2 F2 R2 U' F2 U2")

    @unittest.skipIf(debug_only, "disabled")
    def test_parse(self):
        self.assertEqual([p.alg for p in DrSolution.parse("U R2 U F2").parts], ["", "R2", "F2"])
        self.assertEqual([p.alg for p in DrSolution.parse("F2 B2 U R2 U F2").parts], ["F2 F2", "F2", "R2"])
        self.assertEqual([p.alg for p in DrSolution.parse("U R2 U F2 B2 U F2 U F2").parts], ["", "R2 U F2 F2 U R2", "R2"])

    @unittest.skipIf(debug_only, "disabled")
    def test_dr_reduce(self):
        self.assertEqual([p.alg for p in DrSolution.parse("F2 F2 U F2 U R2").reduce().parts], ["", "F2", "R2"])
        self.assertEqual([p.alg for p in DrSolution.parse("U F2 U2 F2 U R2").reduce().parts], ["", "U2 F2 U2", "R2"])
        self.assertEqual([p.alg for p in DrSolution.parse("U F2 U2 R2 U R2").reduce().parts], ["", "U2 R2 U2 F2 U2", "R2"])
        self.assertEqual([p.alg for p in DrSolution.parse("U F2 U2 R2 U R2 U2 R2").reduce().parts], ["", "U2 R2 U2 F2 U2", "U2 R2 U2"])
        self.assertEqual([p.alg for p in DrSolution.parse("U R2 F2 U F2 U2").reduce().parts], ["", "F2", "U2 R2 U2"])
        self.assertEqual([p.alg for p in DrSolution.parse("U R2 F2 U F2 U2 F2").reduce().parts], ["", "F2", "R2 U2"])
        self.assertEqual([p.alg for p in DrSolution.parse("U R2 F2 U F2 U2 R2 U2").reduce().parts], ["", "F2", "F2 U2 R2"])
        self.assertEqual([p.alg for p in DrSolution.parse("D B2 D' R2 L2 U L2 D' R2 U R2 D' F2 U' B2").reduce().parts], ["", "F2", "F2", "U2 F2", "F2", "F2"])
        self.assertEqual([p.alg for p in DrSolution.parse("U R2 U D R2").reduce().parts], ["", "R2 U2 F2"])
        self.assertEqual([p.alg for p in DrSolution.parse("U' F2 U F2 L2 U D F2 U L2 U' F2 L2 U L2").reduce().parts], ["", "U2 F2", "R2 U2 F2", "U2 F2", "R2", "F2"])
        self.assertEqual([p.alg for p in DrSolution.parse("U R2 F2 R2 B2 R2 F2 D L2 U' D' R2 D F2 D'").reduce().parts], ["F2 U2 R2", "R2", "U2"])

    @unittest.skipIf(not debug_only, "disabled")
    def test_debug(self):
        self.assertEqual([p.alg for p in DrSolution.parse("U R2 F2 R2 B2 R2 F2 D L2 U' D' R2 D F2 D'").reduce().parts], ["R2 U2 F2", "U2 F2", ""])
        pass
