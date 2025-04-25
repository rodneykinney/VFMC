use crate::solver::{solve_step, step_config};
use crate::{Algorithm, Solvable, Visibility};
use cubelib::cube::Cube333;
use cubelib::defs::StepKind;
use cubelib::steps::eo::coords::BadEdgeCount;
use pyo3::PyResult;
use crate::Visibility::{GoodFace, BadFace};

pub struct EOUD;
impl Solvable for EOUD {
    fn is_solved(&self, cube: &Cube333) -> bool {
        cube.count_bad_edges_ud() == 0
    }

    fn is_eligible(&self, _cube: &Cube333) -> bool {
        true
    }
    fn case_name(&self, cube: &Cube333) -> String {
        format!("{}e", cube.count_bad_edges_ud())
    }
    fn edge_visibility(&self, cube: &Cube333, pos: usize, _facelet: u8) -> Visibility {
        if !cube.edges.get_edges()[pos].oriented_ud {
            BadFace
        }
        else {
            GoodFace
        }
    }
    fn corner_visibility(&self, _cube: &Cube333, _pos: usize, _facelet: u8) -> Visibility {
        GoodFace
    }
    fn solve(&self, cube: &Cube333, count: usize) -> PyResult<Vec<Algorithm>> {
        solve_step(cube, step_config(StepKind::EO, "ud"), count, true)
    }
}
pub struct EOFB;
impl Solvable for EOFB {
    fn is_solved(&self, cube: &Cube333) -> bool {
        cube.count_bad_edges_fb() == 0
    }

    fn is_eligible(&self, _cube: &Cube333) -> bool {
        true
    }
    fn case_name(&self, cube: &Cube333) -> String {
        format!("{}e", cube.count_bad_edges_fb())
    }
    fn edge_visibility(&self, cube: &Cube333, pos: usize, _facelet: u8) -> Visibility {
        if !cube.edges.get_edges()[pos].oriented_fb {
            BadFace
        }
        else {
            GoodFace
        }
    }
    fn corner_visibility(&self, _cube: &Cube333, _pos: usize, _facelet: u8) -> Visibility {
        GoodFace
    }
    fn solve(&self, cube: &Cube333, count: usize) -> PyResult<Vec<Algorithm>> {
      solve_step(cube, step_config(StepKind::EO, "fb"), count, true)
    }
}
pub struct EORL;
impl Solvable for EORL {
    fn is_solved(&self, cube: &Cube333) -> bool {
        cube.count_bad_edges_lr() == 0
    }

    fn is_eligible(&self, _cube: &Cube333) -> bool {
        true
    }
    fn case_name(&self, cube: &Cube333) -> String {
        format!("{}e", cube.count_bad_edges_lr())
    }
    fn edge_visibility(&self, cube: &Cube333, pos: usize, _facelet: u8) -> Visibility {
        if !cube.edges.get_edges()[pos].oriented_rl {
            BadFace
        }
        else {
            GoodFace
        }
    }
    fn corner_visibility(&self, _cube: &Cube333, _pos: usize, _facelet: u8) -> Visibility {
        GoodFace
    }
    fn solve(&self, cube: &Cube333, count: usize) -> PyResult<Vec<Algorithm>> {
        solve_step(cube, step_config(StepKind::EO, "lr"), count, true)
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn test_piece_roles() {
        let x = (1,2,3);
    }
}