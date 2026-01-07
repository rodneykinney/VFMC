from skeleton import DrSolution, is_minimal_htr_section, CORNER_INVARIANT, normalize, is_minimal_corner_solution
import unittest


class TestSkeleton(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(["U2", "F2"], normalize(DrSolution.parse("U D R2 U D'"), is_minimal_htr_section,
                                                 CORNER_INVARIANT).moves)
        self.assertEqual(["F2"], normalize(DrSolution.parse("F2 L2 F2 R2"), is_minimal_htr_section,
                                           CORNER_INVARIANT).moves)

    def test_qt_positions(self):
        self.assertEqual((6, 11),
                         DrSolution.parse(
                             "U D R2 U D' B2 U' F2 L2 F2 R2 D' F2 D2 R2 F2 R2 B2").qt_positions)
        self.assertEqual((0, 7, 9, 11, 13),
                         DrSolution.parse("D B2 D' R2 L2 U L2 D' R2 U R2 D' F2 U' B2").qt_positions)
        self.assertEqual((0,),
                         DrSolution.parse("U R2 U D R2").qt_positions)
        self.assertEqual((0, 2, 8, 10, 13),
                         DrSolution.parse("U' F2 U F2 L2 U D F2 U L2 U' F2 L2 U L2").qt_positions)

    def test_htr_sections(self):
        self.assertEqual([["U", "D", "R2", "U", "D'", "B2"], ["F2", "L2", "F2", "R2"],
                          ["F2", "D2", "R2", "F2", "R2", "B2"]],
                         DrSolution.parse(
                             "U D R2 U D' B2 U' F2 L2 F2 R2 D' F2 D2 R2 F2 R2 B2").htr_sections)
        self.assertEqual([[], ["B2", "D'", "R2", "L2", "U", "L2"], ["R2"], ["R2"], ["F2"], ["B2"]],
                         DrSolution.parse("D B2 D' R2 L2 U L2 D' R2 U R2 D' F2 U' B2").htr_sections)
        self.assertEqual([[], ["R2", "U", "D", "R2"], []],
                         DrSolution.parse("U R2 U D R2 U").htr_sections)
        self.assertEqual([[], ["F2"], ["F2", "L2", "U", "D", "F2"], []],
                         DrSolution.parse("U' F2 U F2 L2 U D F2 U").htr_sections)

    def test_leave_slice(self):
        self.assertEquals("U2 F2 B2 U' F2 L2 F2 R2 D' F2 D2 R2 F2 R2 B2", DrSolution.parse("U D R2 U D' B2 U' F2 L2 F2 R2 D' F2 D2 R2 F2 R2 B2").leave_slice.alg)

    def test_corner_skeleton(self):
        self.assertTrue(is_minimal_corner_solution("U R2 U R2 U2 F2".split(" ")))
        self.assertTrue(is_minimal_corner_solution("U F2 U F2 U' F2 U F2 U F2".split(" ")))
        self.assertFalse(is_minimal_corner_solution("U' F2 R2 U2 F2 U' F2 U R2 U F2".split(" ")))
        self.assertEqual("U R2 U R2 U2 F2", DrSolution.parse("U D R2 U D' B2 U' F2 L2 F2 R2 D' F2 D2 R2 F2 R2 B2").corner_skeleton.alg)
        self.assertEqual("U F2 U F2 U' F2 U F2 U F2", DrSolution.parse("D B2 D' R2 L2 U L2 D' R2 U R2 D' F2 U' B2").corner_skeleton.alg)
        self.assertEqual("U R2 U2 F2", DrSolution.parse("U R2 U D R2").corner_skeleton.alg)
        self.assertEqual("U' F2 U R2 U2 F2 U' F2 U R2 U F2", DrSolution.parse("U' F2 U F2 L2 U D F2 U L2 U' F2 L2 U L2").corner_skeleton.alg)
        self.assertEqual("U F2 U' F2 U2 R2", DrSolution.parse("R2 F2 R2 U' R2 U R2 F2 U2 F2 U2").corner_skeleton.alg)
        self.assertEqual("U2 R2 U R2 U F2 U2", DrSolution.parse("U2 R2 U L2 D B2 U2").corner_skeleton.alg)
        self.assertEqual("F2 U' R2 U R2 U R2 U R2", DrSolution.parse("F2 D' F2 U F2 D2 R2 L2 U' F2 R2 D' L2 B2").corner_skeleton.alg)
        self.assertEqual("F2 U' F2 U F2 U R2 U F2", DrSolution.parse("R2 L2 F2 D' L2 D R2 D L2 B2 D' F2 R2").corner_skeleton.alg)
        self.assertEqual("R2 U2 F2 U' F2 U", DrSolution.parse("U R2 F2 R2 B2 R2 F2 U B2 U2 R2 U L2 U'").corner_skeleton.alg)
        self.assertEqual("U' F2 U' F2 U R2 U2", DrSolution.parse("D R2 D2 R2 F2 B2 U R2 U B2 L2 B2 L2 D2").corner_skeleton.alg)

    def test_debug(self):
        self.assertEqual("U F2 U' F2 U2 R2", DrSolution.parse("R2 F2 R2 U' R2 U R2 F2 U2 F2 U2").corner_skeleton.alg)
        self.assertEqual("U' F2 U' F2 U R2 U2", DrSolution.parse("D R2 D2 R2 F2 B2 U R2 U B2 L2 B2 L2 D2").corner_skeleton.alg)
        pass
