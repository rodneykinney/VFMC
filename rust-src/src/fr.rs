use crate::solver::{solve_step, step_config};
use crate::Visibility::{Any, BadFace, BadPiece};
use crate::{
    Algorithm, Solvable, CORNER_FB_FACELETS, CORNER_OPPOSITE_E_SLICE, CORNER_OPPOSITE_M_SLICE,
    CORNER_OPPOSITE_S_SLICE, CORNER_RL_FACELETS, CORNER_UD_FACELETS, EDGE_FB_FACELETS,
    EDGE_OPPOSITE_E_SLICE, EDGE_OPPOSITE_M_SLICE, EDGE_OPPOSITE_S_SLICE, EDGE_RL_FACELETS,
    EDGE_UD_FACELETS, HTRFB, HTRRL, HTRUD,
};
use cubelib::cube::turn::TransformableMut;
use cubelib::cube::{Cube333, Transformation333};
use cubelib::defs::StepKind;
use cubelib::steps::coord::Coord;
use cubelib::steps::fr::coords::{FRCPOrbitCoord, FROrbitParityCoord, FRUDNoSliceCoord};
use pyo3::PyResult;

pub struct FRUD;
impl Solvable for FRUD {
    fn is_solved(&self, cube: &Cube333) -> bool {
        FRUDNoSliceCoord::from(cube).val() == 0
    }

    fn is_eligible(&self, cube: &Cube333) -> bool {
        HTRUD.is_solved(cube)
    }

    fn case_name(&self, cube: &Cube333) -> String {
        let parity = FROrbitParityCoord::from(cube).val() == 1;
        let corner_case = match (FRCPOrbitCoord::from(&cube.corners).val(), parity) {
            (0, true) => "0c3",
            (0, false) => "0c0",
            (3, true) => "4c1",
            (3, false) => "4c2",
            (_, true) => "6c1",
            (_, false) => "6c2",
        };
        let bad_edge_count = cube
            .edges
            .get_edges()
            .iter()
            .enumerate()
            .filter(|(pos, e)| {
                *pos as u8 != EDGE_OPPOSITE_E_SLICE[*pos]
                    && e.id != *pos as u8
                    && e.id != EDGE_OPPOSITE_E_SLICE[*pos]
            })
            .count() as u8;
        let bad_edge_count = bad_edge_count.min(bad_edge_count);

        format!("{} {}e", corner_case, bad_edge_count).to_string()
    }

    fn edge_visibility(&self, cube: &Cube333, pos: usize, facelet: u8) -> u8 {
        let e = cube.edges.get_edges()[pos];
        let mut v = Any as u8;
        if pos as u8 != EDGE_OPPOSITE_E_SLICE[pos]
            && e.id != pos as u8
            && e.id != EDGE_OPPOSITE_E_SLICE[pos]
        {
            v |= BadPiece as u8;
            if Some(facelet) != EDGE_UD_FACELETS[pos] {
                v |= BadFace as u8;
            }
        }
        v
    }

    fn corner_visibility(&self, cube: &Cube333, pos: usize, facelet: u8) -> u8 {
        let c = cube.corners.get_corners()[pos];
        let mut v = Any as u8;
        let c_opp = cube.corners.get_corners()[CORNER_OPPOSITE_E_SLICE[pos] as usize];
        match c.id {
            2 | 5 => {
                if c_opp.id != CORNER_OPPOSITE_E_SLICE[c.id as usize] {
                    v |= BadPiece as u8;
                    if facelet != CORNER_UD_FACELETS[pos] {
                        v |= BadFace as u8;
                    }
                }
            }
            _ => (),
        }
        v
    }
    fn solve(&self, cube: &Cube333, count: usize) -> PyResult<Vec<Algorithm>> {
        solve_step(cube, step_config(StepKind::FRLS, "ud"), count, false)
    }
}
pub struct FRFB;
impl Solvable for FRFB {
    fn is_solved(&self, cube: &Cube333) -> bool {
        let mut cube = cube.clone();
        cube.transform(Transformation333::X);
        FRUD.is_solved(&cube)
    }

    fn is_eligible(&self, cube: &Cube333) -> bool {
        HTRFB.is_solved(cube)
    }

    fn case_name(&self, cube: &Cube333) -> String {
        let mut ud_cube = cube.clone();
        ud_cube.transform(Transformation333::X);
        FRUD.case_name(&ud_cube)
    }

    fn edge_visibility(&self, cube: &Cube333, pos: usize, facelet: u8) -> u8 {
        let e = cube.edges.get_edges()[pos];
        let mut v = Any as u8;
        if pos as u8 != EDGE_OPPOSITE_S_SLICE[pos]
            && e.id != pos as u8
            && e.id != EDGE_OPPOSITE_S_SLICE[pos]
        {
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
        let c_opp = cube.corners.get_corners()[CORNER_OPPOSITE_S_SLICE[pos] as usize];
        match c.id {
            1 | 2 => {
                if c_opp.id != CORNER_OPPOSITE_S_SLICE[c.id as usize] {
                    v |= BadPiece as u8;
                    if facelet != CORNER_FB_FACELETS[pos] {
                        v |= BadFace as u8;
                    }
                }
            }
            _ => (),
        }
        v
    }
    fn solve(&self, cube: &Cube333, count: usize) -> PyResult<Vec<Algorithm>> {
        solve_step(cube, step_config(StepKind::FRLS, "fb"), count, false)
    }
}

pub struct FRRL;
impl Solvable for FRRL {
    fn is_solved(&self, cube: &Cube333) -> bool {
        let mut cube = cube.clone();
        cube.transform(Transformation333::Z);
        FRUD.is_solved(&cube)
    }

    fn is_eligible(&self, cube: &Cube333) -> bool {
        HTRRL.is_solved(cube)
    }

    fn case_name(&self, cube: &Cube333) -> String {
        let mut ud_cube = cube.clone();
        ud_cube.transform(Transformation333::Z);
        FRUD.case_name(&ud_cube)
    }

    fn edge_visibility(&self, cube: &Cube333, pos: usize, facelet: u8) -> u8 {
        let e = cube.edges.get_edges()[pos];
        let mut v = Any as u8;
        if pos as u8 != EDGE_OPPOSITE_M_SLICE[pos]
            && e.id != pos as u8
            && e.id != EDGE_OPPOSITE_M_SLICE[pos]
        {
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
        let c_opp = cube.corners.get_corners()[CORNER_OPPOSITE_M_SLICE[pos] as usize];
        match c.id {
            2 | 3 => {
                if c_opp.id != CORNER_OPPOSITE_M_SLICE[c.id as usize] {
                    v |= BadPiece as u8;
                    if facelet != CORNER_RL_FACELETS[pos] {
                        v |= BadFace as u8;
                    }
                }
            }
            _ => (),
        }
        v
    }
    fn solve(&self, cube: &Cube333, count: usize) -> PyResult<Vec<Algorithm>> {
        solve_step(cube, step_config(StepKind::FRLS, "lr"), count, false)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::Cube;
    use cubelib::algs::Algorithm as LibAlgorithm;
    use cubelib::cube::turn::ApplyAlgorithm;
    use std::str::FromStr;

    #[test]
    fn test_8e() {
        let mut cube = Cube333::default();
        cube.apply_alg(&LibAlgorithm::from_str("U2 D2").unwrap());
        let coord = FRUDNoSliceCoord::from(&cube).val();
        assert_ne!(coord, 0);
    }

    #[test]
    fn test_solve() {
        let cube = Cube::new("R' F' D2 F R F2 L' U2 B F2 D2 B2 D2 R2 F2 B2 U2 U F R2 U2 U D' R2 F R U2 D L2 R' U2 D' R U' F2 R2 U2 F2 D".to_string()).unwrap().0;
        let solutions = FRUD.solve(&cube, 10).unwrap();
        assert_ne!(solutions.len(), 0);
    }
}
