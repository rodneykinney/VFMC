use crate::eo::{EOFB, EORL, EOUD};
use crate::solver::{solve_step, step_config};
use crate::{Algorithm, DrawableCorner, Solvable, Visibility};
use cubelib::cube::turn::TransformableMut;
use cubelib::cube::{Corner, Cube333, Transformation333};
use cubelib::defs::StepKind;
use cubelib::steps::coord::Coord;
use cubelib::steps::dr::coords::DRUDEOFBCoord;
use cubelib::steps::eo::coords::BadEdgeCount;
use pyo3::PyResult;
use crate::Visibility::{GoodFace, BadFace, BadPieceGoodFace};

pub struct DRUD;
impl Solvable for DRUD {
    fn is_solved(&self, cube: &Cube333) -> bool {
        let solved = cube.count_bad_edges_fb() == 0
            && cube.count_bad_edges_lr() == 0
            && DRUDEOFBCoord::from(cube).val() == 0;
        solved
    }

    fn is_eligible(&self, cube: &Cube333) -> bool {
        EORL.is_solved(cube) || EOFB.is_solved(cube)
    }
    fn case_name(&self, cube: &Cube333) -> String {
        let bad_corner_count = cube
            .corners
            .get_corners()
            .into_iter()
            .filter(|c: &Corner| c.orientation != 0)
            .count();
        let bad_edge_count = cube.count_bad_edges_lr() + cube.count_bad_edges_fb();
        format!("{}c{}e", bad_corner_count, bad_edge_count)
    }
    fn edge_visibility(&self, cube: &Cube333, pos: usize, _facelet: u8) -> Visibility {
        let e = cube.edges.get_edges()[pos];
        if !e.oriented_fb || !e.oriented_rl {
            BadFace
        } else {
            GoodFace
        }
    }
    fn corner_visibility(&self, cube: &Cube333, pos: usize, facelet: u8) -> Visibility {
        let c = cube.corners.get_corners()[pos];
        if !c.oriented_ud(pos as u8) {
            if facelet == c.facelet_showing_ud() {
                BadFace
            } else {
                BadPieceGoodFace
            }
        }
        else {
            GoodFace
        }
    }
    fn solve(&self, cube: &Cube333, count: usize) -> PyResult<Vec<Algorithm>> {
        solve_step(cube, step_config(StepKind::DR, "ud"), count, true)
    }
}

pub struct DRFB;
impl Solvable for DRFB {
    fn is_solved(&self, cube: &Cube333) -> bool {
        let mut cube = cube.clone();
        cube.transform(Transformation333::X);
        DRUD.is_solved(&cube)
    }
    fn is_eligible(&self, cube: &Cube333) -> bool {
        EORL.is_solved(cube) || EOUD.is_solved(cube)
    }
    fn case_name(&self, cube: &Cube333) -> String {
        let mut cube = cube.clone();
        cube.transform(Transformation333::X);
        DRUD.case_name(&cube)
    }
    fn edge_visibility(&self, cube: &Cube333, pos: usize, _facelet: u8) -> Visibility {
        let e = cube.edges.get_edges()[pos];
        if !e.oriented_ud || !e.oriented_rl {
            BadFace
        } else {
            GoodFace
        }
    }
    fn corner_visibility(&self, cube: &Cube333, pos: usize, facelet: u8) -> Visibility {
        let c = cube.corners.get_corners()[pos];
        if !c.oriented_fb(pos as u8) {
            if facelet == c.facelet_showing_fb() {
                BadFace
            } else {
                BadPieceGoodFace
            }
        }
        else {
            GoodFace
        }
    }
    fn solve(&self, cube: &Cube333, count: usize) -> PyResult<Vec<Algorithm>> {
        solve_step(cube, step_config(StepKind::DR, "fb"), count, true)
    }
}
pub struct DRRL;
impl Solvable for DRRL {
    fn is_solved(&self, cube: &Cube333) -> bool {
        let mut cube = cube.clone();
        cube.transform(Transformation333::Z);
        DRUD.is_solved(&cube)
    }
    fn is_eligible(&self, cube: &Cube333) -> bool {
        EOUD.is_solved(cube) || EOFB.is_solved(cube)
    }
    fn case_name(&self, cube: &Cube333) -> String {
        let mut cube = cube.clone();
        cube.transform(Transformation333::Z);
        DRUD.case_name(&cube)
    }
    fn edge_visibility(&self, cube: &Cube333, pos: usize, _facelet: u8) -> Visibility {
        let e = cube.edges.get_edges()[pos];
        if !e.oriented_fb || !e.oriented_ud {
            BadFace
        }
        else {
            GoodFace
        }
    }
    fn corner_visibility(&self, cube: &Cube333, pos: usize, facelet: u8) -> Visibility {
        let c = cube.corners.get_corners()[pos];
        if !c.oriented_rl(pos as u8) {
            if facelet == c.facelet_showing_rl() {
                BadFace
            }
            else {
                BadPieceGoodFace
            }
        }
        else {
            GoodFace
        }
    }
    fn solve(&self, cube: &Cube333, count: usize) -> PyResult<Vec<Algorithm>> {
        solve_step(cube, step_config(StepKind::DR, "lr"), count, true)
    }
}
