use crate::htr::HTRUD;
use crate::solver::{solve_step, step_config};
use crate::{Algorithm, Solvable};
use cubelib::cube::Cube333;
use cubelib::defs::StepKind;
use cubelib::steps::coord::Coord;
use cubelib::steps::finish::coords::HTRFinishCoord;
use pyo3::PyResult;

pub struct Finish;
impl Solvable for Finish {
    fn is_solved(&self, cube: &Cube333) -> bool {
        HTRFinishCoord::from(cube).val() == 0
    }

    fn is_eligible(&self, cube: &Cube333) -> bool {
        HTRUD.is_solved(cube)
    }

    fn case_name(&self, cube: &Cube333) -> String {
        let edges = cube.edges.get_edges();
        let corners = cube.corners.get_corners();
        let bad_edge_count =
            edges.iter().enumerate().filter(
                    |(i, e)| (**e).id as usize != *i
            ).count();
        let bad_corner_count =
            corners.iter().enumerate().filter(
                |(i, c)| (**c).id as usize != *i
            ).count();
        let c_string = if bad_corner_count > 0 {format!("{}c", bad_corner_count) } else {"".to_string()};
        let e_string = if bad_edge_count > 0 {format!("{}e", bad_edge_count) } else {"".to_string()};
        format!("{}{}", c_string, e_string)
    }

    fn should_draw_edge(&self, _cube: &Cube333, _pos: usize, _facelet: u8) -> bool {
        true
    }

    fn should_draw_corner(&self, _cube: &Cube333, _pos: usize, _facelet: u8) -> bool {
        true
    }
    fn solve(&self, cube: &Cube333, count: usize) -> PyResult<Vec<Algorithm>> {
        solve_step(cube, step_config(StepKind::FIN, ""), count, false)
    }
}