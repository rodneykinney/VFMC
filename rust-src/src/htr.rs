use crate::solver::{solve_step_deduplicated, step_config};
use crate::Visibility::{Any, BadFace, BadPiece, HtrD, TopColor};
use crate::{
    Algorithm, DrawableCorner, Solvable, CORNER_FB_FACELETS, CORNER_RL_FACELETS,
    CORNER_UD_FACELETS, EDGE_FB_FACELETS, EDGE_RL_FACELETS, EDGE_UD_FACELETS,
};
use cubelib::cube::turn::{ApplyAlgorithm, TransformableMut};
use cubelib::cube::{Cube333, Transformation333};
use cubelib::defs::StepKind;
use cubelib::steps::coord::Coord;
use cubelib::steps::fr::coords::FRUDNoSliceCoord;
use pyo3::PyResult;

pub struct HTRUD;
impl Solvable for HTRUD {
    fn is_solved(&self, cube: &Cube333) -> bool {
        match cube.get_dr_subset() {
            Some(s) => s.qt == 0,
            _ => false,
        }
    }
    fn is_eligible(&self, cube: &Cube333) -> bool {
        match cube.get_dr_subset() {
            Some(_) => true,
            _ => false,
        }
    }
    fn case_name(&self, cube: &Cube333) -> String {
        match cube.get_dr_subset() {
            Some(s) => s.to_string(),
            _ => "".to_string(),
        }
    }
    fn edge_visibility(&self, cube: &Cube333, pos: usize, facelet: u8) -> u8 {
        let e = cube.edges.get_edges()[pos];
        if !e.oriented_ud {
            let mut v = BadPiece as u8;
            if Some(facelet) != EDGE_UD_FACELETS[pos] {
                v |= BadFace as u8;
            }
            v
        } else {
            Any as u8
        }
    }
    fn corner_visibility(&self, cube: &Cube333, pos: usize, facelet: u8) -> u8 {
        let c = cube.corners.get_corners()[pos];
        let mut v = Any as u8;
        if facelet == c.facelet_showing_ud() {
            // D sticker
            if c.id / 4 == 1 {
                v |= HtrD as u8;
            } else {
                v |= TopColor as u8;
            }
        }
        if !c.oriented_fb(pos as u8) {
            v |= BadPiece as u8;
            if facelet != CORNER_UD_FACELETS[pos] {
                v |= BadFace as u8;
            }
        }
        v
    }
    fn solve(&self, cube: &Cube333, count: usize) -> PyResult<Vec<Algorithm>> {
        solve_step_deduplicated(
            cube,
            step_config(StepKind::HTR, ""),
            count,
            true,
            is_equivalent(Transformation333::Y),
        )
    }
}
fn is_equivalent(transform: Transformation333) -> impl Fn(&Cube333, &Algorithm) -> usize {
    move |cube: &Cube333, _alg: &Algorithm| {
        let mut cube = cube.clone();
        cube.transform(transform);
        let coord1 = FRUDNoSliceCoord::from(&cube);
        let mut c = cube.clone();
        c.apply_alg(&Algorithm::new("U2 D2").unwrap().0);
        let coord2 = FRUDNoSliceCoord::from(&c);
        std::cmp::min(coord1.val(), coord2.val())
    }
}
pub struct HTRFB;
impl Solvable for HTRFB {
    fn is_solved(&self, cube: &Cube333) -> bool {
        match cube.get_dr_subset() {
            Some(s) => s.qt == 0,
            _ => false,
        }
    }
    fn is_eligible(&self, cube: &Cube333) -> bool {
        match cube.get_dr_subset() {
            Some(_) => true,
            _ => false,
        }
    }
    fn case_name(&self, cube: &Cube333) -> String {
        match cube.get_dr_subset() {
            Some(s) => s.to_string(),
            _ => "".to_string(),
        }
    }
    fn edge_visibility(&self, cube: &Cube333, pos: usize, facelet: u8) -> u8 {
        let e = cube.edges.get_edges()[pos];
        let mut v = Any as u8;
        if !e.oriented_fb {
            v |= BadPiece as u8;
            if Some(facelet) != EDGE_FB_FACELETS[pos] {
                v |= BadFace as u8;
            }
        }
        v
    }
    fn corner_visibility(&self, cube: &Cube333, pos: usize, facelet: u8) -> u8 {
        let c = cube.corners.get_corners()[pos];
        let mut v = Any as u8;
        if facelet == c.facelet_showing_fb() {
            if vec![0, 1, 6, 7].contains(&c.id) {
                v |= HtrD as u8; // B sticker
            } else {
                v |= TopColor as u8;
            }
        }
        if !c.oriented_rl(pos as u8) {
            v |= BadPiece as u8;
            if facelet != CORNER_FB_FACELETS[pos] {
                v |= BadFace as u8;
            }
        }
        v
    }
    fn solve(&self, cube: &Cube333, count: usize) -> PyResult<Vec<Algorithm>> {
        solve_step_deduplicated(
            cube,
            step_config(StepKind::HTR, ""),
            count,
            true,
            is_equivalent(Transformation333::X),
        )
    }
}
pub struct HTRRL;
impl Solvable for HTRRL {
    fn is_solved(&self, cube: &Cube333) -> bool {
        HTRUD.is_solved(cube)
    }
    fn is_eligible(&self, cube: &Cube333) -> bool {
        HTRUD.is_eligible(cube)
    }
    fn case_name(&self, cube: &Cube333) -> String {
        HTRUD.case_name(cube)
    }
    fn edge_visibility(&self, cube: &Cube333, pos: usize, facelet: u8) -> u8 {
        let e = cube.edges.get_edges()[pos];
        let mut v = Any as u8;
        if !e.oriented_rl {
            v |= BadPiece as u8;
            if Some(facelet) != EDGE_RL_FACELETS[pos] {
                v |= BadFace as u8;
            }
        }
        v
    }
    fn corner_visibility(&self, cube: &Cube333, pos: usize, facelet: u8) -> u8 {
        let c = cube.corners.get_corners()[pos];
        let mut v = Any as u8;
        if facelet == c.facelet_showing_rl() {
            if vec![1, 2, 5, 6].contains(&c.id) {
                v |= HtrD as u8; // L sticker
            } else {
                v |= TopColor as u8;
            }
        }
        if !c.oriented_ud(pos as u8) {
            v |= BadPiece as u8;
            if facelet != CORNER_RL_FACELETS[pos] {
                v |= BadFace as u8;
            }
        }
        v
    }
    fn solve(&self, cube: &Cube333, count: usize) -> PyResult<Vec<Algorithm>> {
        solve_step_deduplicated(
            cube,
            step_config(StepKind::HTR, ""),
            count,
            true,
            is_equivalent(Transformation333::Z),
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{Solvable, StepInfo};
    use cubelib::algs::Algorithm as LibAlgorithm;
    use cubelib::steps::htr::coords::HTRDRUDCoord;
    use std::str::FromStr;

    #[test]
    fn test_unique_htr() {
        let mut cube = Cube333::default();
        cube.apply_alg(&LibAlgorithm::from_str("U2 F2").unwrap());
        let coord_1 = FRUDNoSliceCoord::from(&cube);
        let mut cube2 = Cube333::default();
        cube2.apply_alg(&LibAlgorithm::from_str("U D R2 U D'").unwrap());
        let coord_2 = FRUDNoSliceCoord::from(&cube2);
        assert_eq!(coord_1, coord_2);
    }

    #[test]
    fn test_find() {
        let scramble =
            "F2 U R' D F2 D F2 B2 U B2 R2 U2 L2 R2 B2 U2 R2 B' U' B D' F' R2 B' R U2 B R U' L2 F D F U' B U";
        // R U2 B R U' L2 F D F U' B U R2 F R2 U2 F D2 F' D2 F R2 B (23)
        let mut cube = Cube333::default();
        cube.apply_alg(&LibAlgorithm::from_str(scramble).unwrap());
        let algs = HTRFB.solve(&cube, 100).unwrap();
        assert_ne!(algs.len(), 0);
    }

    #[test]
    fn test_htr() {
        let scramble = "R U2 F2 U2 R";
        let mut cube = Cube333::default();
        cube.apply_alg(&LibAlgorithm::from_str(scramble).unwrap());
        let state = cube.get_cube_state();
        let coord = HTRDRUDCoord::from(&cube).val();
        let subset = cube.get_dr_subset().unwrap();
        let case = HTRRL.case_name(&cube);
        assert_eq!(HTRRL.is_solved(&cube), false);
    }

    #[test]
    fn test_allowed() {
        let moves = "R L' U2 R' L U2";
        assert_eq!(
            StepInfo::new("htr", "ud")
                .unwrap()
                .are_moves_allowed(moves)
                .unwrap(),
            true
        );
    }
}
