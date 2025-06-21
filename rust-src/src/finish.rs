use crate::solver::{solve_step, step_config};
use crate::Visibility::{Any, BadFace, BadPiece};
use crate::{Algorithm, Solvable};
use cubelib::cube::Cube333;
use cubelib::defs::{NissSwitchType, StepKind};
use cubelib::steps::coord::Coord;
use cubelib::steps::finish::coords::HTRFinishCoord;
use pyo3::PyResult;

pub struct Finish;
impl Solvable for Finish {
    fn is_solved(&self, cube: &Cube333) -> bool {
        HTRFinishCoord::from(cube).val() == 0
    }

    fn is_eligible(&self, _cube: &Cube333) -> bool {
        true
    }

    fn case_name(&self, cube: &Cube333) -> String {
        let edges = cube.edges.get_edges();
        let corners = cube.corners.get_corners();
        let bad_edge_count = edges
            .iter()
            .enumerate()
            .filter(|(i, e)| (**e).id as usize != *i)
            .count();
        let bad_corner_count = corners
            .iter()
            .enumerate()
            .filter(|(i, c)| (**c).id as usize != *i)
            .count();
        let c_string = if bad_corner_count > 0 {
            format!("{}c", bad_corner_count)
        } else {
            "".to_string()
        };
        let e_string = if bad_edge_count > 0 {
            format!("{}e", bad_edge_count)
        } else {
            "".to_string()
        };
        format!("{}{}", c_string, e_string)
    }

    fn edge_visibility(&self, cube: &Cube333, pos: usize, _facelet: u8) -> u8 {
        let mut v = Any as u8;
        if cube.edges.get_edges()[pos].id as usize != pos {
            v |= BadPiece as u8 | BadFace as u8;
        }
        v
    }

    fn corner_visibility(&self, cube: &Cube333, pos: usize, _facelet: u8) -> u8 {
        let mut v = Any as u8;
        if cube.corners.get_corners()[pos].id as usize != pos {
            v |= BadPiece as u8 | BadFace as u8;
        }
        v
    }
    fn solve(&self, cube: &Cube333, count: usize) -> PyResult<Vec<Algorithm>> {
        let mut cfg = step_config(StepKind::FIN, "", NissSwitchType::Never);
        cfg.max = Some(20);
        solve_step(cube, cfg, count, false)
    }
}

#[cfg(test)]
mod tests {
    use crate::finish::Finish;
    use crate::{Cube, Solvable};

    #[test]
    fn htr_to_finish() {
        let mut cube = Cube::new("U' F2 U2 L2 U' R2 U F2 L2 R' U' F B' R D2 U' F R2 F U R2 B2 U2 R2 L2 F2 R2 U2 R2 B R2 F' L' F' R' U' F B D' R' F L' U L B2 U R2 F2 L".to_string()).unwrap().0;
        let finish = Finish;
        let solutions = finish.solve(&cube, 2).unwrap();
        assert!(solutions.len() > 0);
    }
}
