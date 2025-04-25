use crate::htr::{HTRFB, HTRUD, HTRRL};
use crate::solver::{solve_step, step_config};
use crate::{Algorithm, Solvable, Visibility};
use cubelib::cube::turn::TransformableMut;
use cubelib::cube::{Cube333, Transformation333};
use cubelib::defs::StepKind;
use cubelib::steps::coord::Coord;
use cubelib::steps::finish::coords::HTRLeaveSliceFinishCoord;
use pyo3::PyResult;
use crate::Visibility::{GoodFace, BadFace};

pub struct SliceUD;
impl Solvable for SliceUD {
    fn is_solved(&self, cube: &Cube333) -> bool {
        HTRLeaveSliceFinishCoord::from(cube).val() == 0
    }

    fn is_eligible(&self, cube: &Cube333) -> bool {
        HTRUD.is_solved(cube)
    }

    fn case_name(&self, cube: &Cube333) -> String {
        let mut bad_edge_count = 0;
        let mut bad_corner_count = 0;
        let edges = cube.edges.get_edges();
        let corners = cube.corners.get_corners();
        for i in 0..4 {
            if edges[i].id as usize != i {
                bad_edge_count += 1;
            }
        }
        for i in 8.. 12 {
            if edges[i].id as usize != i {
                bad_edge_count += 1;
            }
        }
        for i in 0..8 {
            if corners[i].id as usize != i {
                bad_corner_count += 1;
            }
        }
        format!("{}c{}e", bad_corner_count, bad_edge_count).to_string()
    }

    fn edge_visibility(&self, _cube: &Cube333, pos: usize, _facelet: u8) -> Visibility {
        if pos < 4 || pos > 7 {
            BadFace
        } else {
            GoodFace
        }
    }

    fn corner_visibility(&self, _cube: &Cube333, _pos: usize, _facelet: u8) -> Visibility {
        BadFace
    }
    fn solve(&self, cube: &Cube333, count: usize) -> PyResult<Vec<Algorithm>> {
        solve_step(cube, step_config(StepKind::FINLS, ""), count, false)
    }
}
pub struct SliceFB;
impl Solvable for SliceFB {
    fn is_solved(&self, cube: &Cube333) -> bool {
        let mut cube = cube.clone();
        cube.transform(Transformation333::X);
        SliceUD.is_solved(&cube)
    }

    fn is_eligible(&self, cube: &Cube333) -> bool {
        HTRFB.is_solved(cube)
    }

    fn case_name(&self, cube: &Cube333) -> String {
        let mut cube = cube.clone();
        cube.transform(Transformation333::X);
        SliceUD.case_name(&cube)
    }

    fn edge_visibility(&self, _cube: &Cube333, pos: usize, _facelet: u8) -> Visibility {
        match pos {
            1 | 3 | 9 | 11 => GoodFace,
            _ => BadFace,
        }
    }

    fn corner_visibility(&self, _cube: &Cube333, _pos: usize, _facelet: u8) -> Visibility {
        BadFace
    }
    fn solve(&self, cube: &Cube333, count: usize) -> PyResult<Vec<Algorithm>> {
        solve_step(cube, step_config(StepKind::FINLS, ""), count, false)
    }
}

pub struct SliceRL;
impl Solvable for SliceRL {
    fn is_solved(&self, cube: &Cube333) -> bool {
        let mut cube = cube.clone();
        cube.transform(Transformation333::Z);
        SliceUD.is_solved(&cube)
    }

    fn is_eligible(&self, cube: &Cube333) -> bool {
        HTRRL.is_solved(cube)
    }

    fn case_name(&self, cube: &Cube333) -> String {
        let mut cube = cube.clone();
        cube.transform(Transformation333::Z);
        SliceUD.case_name(&cube)
    }

    fn edge_visibility(&self, _cube: &Cube333, pos: usize, _facelet: u8) -> Visibility {
        match pos {
            0 | 2 | 8 | 10 => GoodFace,
            _ => BadFace,
        }
    }

    fn corner_visibility(&self, _cube: &Cube333, _pos: usize, _facelet: u8) -> Visibility {
        BadFace
    }
    fn solve(&self, cube: &Cube333, count: usize) -> PyResult<Vec<Algorithm>> {
        solve_step(cube, step_config(StepKind::FINLS, ""), count, false)
    }
}

#[cfg(test)]
mod tests {
    use crate::Cube;
    use super::*;
    use cubelib::cube::turn::TurnableMut;
    use cubelib::cube::Cube333;
    use cubelib::cube::CubeFace;
    use cubelib::cube::Direction;

    #[test]
    fn test_slice_ud() {
        let cube = Cube::new("U2 L' B2 R' U2 F L2 B2 D2 L2 F2 U2 L2 R' F2 U2 R' F2 U B' R2 B R' B R F2 R D' L2 D' B2 R U F2 B2 U L2 D".to_string()).unwrap().0;
        let slice_ud = SliceUD {};
        assert!(slice_ud.is_eligible(&cube));
    }
}
