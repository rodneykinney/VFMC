use crate::{Algorithm, Solvable};
use cubelib::cube::Cube333;
use pyo3::PyResult;
use crate::finish::Finish;

pub struct Insertions;
impl Solvable for Insertions {
    fn is_solved(&self, cube: &Cube333) -> bool {
        Finish.is_solved(cube)
    }

    fn is_eligible(&self, cube: &Cube333) -> bool { Finish.is_eligible(cube) }

    fn case_name(&self, cube: &Cube333) -> String {
        Finish.case_name(cube)
    }

    fn edge_visibility(&self, cube: &Cube333, pos: usize, _facelet: u8) -> u8 {
        Finish.edge_visibility(cube, pos, _facelet)
    }

    fn corner_visibility(&self, cube: &Cube333, pos: usize, _facelet: u8) -> u8 {
        Finish.corner_visibility(cube, pos, _facelet)
    }
    fn solve(&self, _cube: &Cube333, _count: usize) -> PyResult<Vec<Algorithm>> {
        Err(pyo3::exceptions::PyValueError::new_err(
            "No solver for insertions",
        ))
    }
}