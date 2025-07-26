use crate::eo::{EOFB, EORL, EOUD};
use crate::solver::{solve_step, step_config};
use crate::Visibility::{Any, BadFace, BadPiece};
use crate::{
    Algorithm, DrawableCorner, Solvable, EDGE_FB_FACELETS, EDGE_RL_FACELETS, EDGE_UD_FACELETS,
};
use cubelib::cube::turn::TransformableMut;
use cubelib::cube::{Corner, Cube333, Transformation333};
use cubelib::defs::{NissSwitchType, StepKind};
use cubelib::steps::coord::Coord;
use cubelib::steps::dr::coords::DRUDEOFBCoord;
use cubelib::steps::eo::coords::BadEdgeCount;
use pyo3::PyResult;

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
    fn edge_visibility(&self, cube: &Cube333, pos: usize, facelet: u8) -> u8 {
        let e = cube.edges.get_edges()[pos];
        let mut v = Any as u8;
        if !e.oriented_fb || !e.oriented_rl {
            v |= BadPiece as u8;
            match pos {
                4 | 5 | 6 | 7 if e.oriented_fb && (Some(facelet) == EDGE_FB_FACELETS[pos]) => {
                    v |= BadFace as u8
                }
                4 | 5 | 6 | 7 if e.oriented_rl && (Some(facelet) == EDGE_RL_FACELETS[pos]) => {
                    v |= BadFace as u8
                }
                _ if Some(facelet) == EDGE_UD_FACELETS[pos] => v |= BadFace as u8,
                _ => (),
            }
        }
        v
    }
    fn corner_visibility(&self, cube: &Cube333, pos: usize, facelet: u8) -> u8 {
        let c = cube.corners.get_corners()[pos];
        let mut v = Any as u8;
        if !c.oriented_ud(pos as u8) {
            v |= BadPiece as u8;
            if facelet == c.facelet_showing_ud() {
                v |= BadFace as u8;
            }
        }
        v
    }
    fn solve(&self, cube: &Cube333, count: usize) -> PyResult<Vec<Algorithm>> {
        solve_step(cube, step_config(StepKind::DR, "ud", NissSwitchType::Never), count, true)
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
    fn edge_visibility(&self, cube: &Cube333, pos: usize, facelet: u8) -> u8 {
        let e = cube.edges.get_edges()[pos];
        let mut v = Any as u8;
        if !e.oriented_ud || !e.oriented_rl {
            v |= BadPiece as u8;
            match pos {
                1 | 3 | 9 | 11 if e.oriented_ud && (Some(facelet) == EDGE_UD_FACELETS[pos]) => {
                    v |= BadFace as u8
                }
                1 | 3 | 9 | 11 if e.oriented_rl && (Some(facelet) == EDGE_RL_FACELETS[pos]) => {
                    v |= BadFace as u8
                }
                _ if Some(facelet) == EDGE_FB_FACELETS[pos] => v |= BadFace as u8,
                _ => (),
            }
        }
        v
    }
    fn corner_visibility(&self, cube: &Cube333, pos: usize, facelet: u8) -> u8 {
        let c = cube.corners.get_corners()[pos];
        let mut v = Any as u8;
        if !c.oriented_fb(pos as u8) {
            v |= BadPiece as u8;
            if facelet == c.facelet_showing_fb() {
                v |= BadFace as u8;
            }
        }
        v
    }
    fn solve(&self, cube: &Cube333, count: usize) -> PyResult<Vec<Algorithm>> {
        solve_step(cube, step_config(StepKind::DR, "fb", NissSwitchType::Never), count, true)
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
    fn edge_visibility(&self, cube: &Cube333, pos: usize, facelet: u8) -> u8 {
        let e = cube.edges.get_edges()[pos];
        let mut v = Any as u8;
        if !e.oriented_fb || !e.oriented_ud {
            v |= BadPiece as u8;
            match pos {
                0 | 2 | 8 | 10 if e.oriented_fb && (Some(facelet) == EDGE_FB_FACELETS[pos]) => {
                    v |= BadFace as u8
                }
                0 | 2 | 8 | 10 if e.oriented_ud && (Some(facelet) == EDGE_UD_FACELETS[pos]) => {
                    v |= BadFace as u8
                }
                _ if Some(facelet) == EDGE_RL_FACELETS[pos] => v |= BadFace as u8,
                _ => (),
            }
        }
        v
    }
    fn corner_visibility(&self, cube: &Cube333, pos: usize, facelet: u8) -> u8 {
        let c = cube.corners.get_corners()[pos];
        let mut v = Any as u8;
        if !c.oriented_rl(pos as u8) {
            v |= BadPiece as u8;
            if facelet == c.facelet_showing_rl() {
                v |= BadFace as u8;
            }
        }
        v
    }
    fn solve(&self, cube: &Cube333, count: usize) -> PyResult<Vec<Algorithm>> {
        solve_step(cube, step_config(StepKind::DR, "lr", NissSwitchType::Never), count, true)
    }
}

pub struct AR;
impl AR {
    pub fn arm_uf(&self, cube: &Cube333) -> (u8, u8, u8) {
        let corners = cube.corners.get_corners();
        let mut arm_c_r = 0;
        let mut arm_c_l = 0;
        for i in 0..8 {
            match (i, corners[i].orientation) {
                (0, 1) | (3, 2) | (4, 1) | (7, 2) => arm_c_l += 1,
                (1, 2) | (2, 1) | (5, 2) | (6, 1) => arm_c_r += 1,
                _ => (),
            }
        }
        let edges = cube.edges.get_edges();
        let mut arm_e = 0;
        for i in [0,2,8,10] {
            if !edges[i].oriented_rl || !edges[i].oriented_fb {
                arm_e += 1;
            }
        }
        (arm_c_r, arm_e, arm_c_l)
    }
    pub fn arm_rf(&self, cube: &Cube333) -> (u8, u8, u8) {
        let mut cube = cube.clone();
        cube.transform(Transformation333::Z);
        self.arm_uf(&cube)
    }
    pub fn arm_ur(&self, cube: &Cube333) -> (u8, u8, u8) {
        let mut cube = cube.clone();
        cube.transform(Transformation333::Y);
        self.arm_uf(&cube)
    }
    pub fn arm_br(&self, cube: &Cube333) -> (u8, u8, u8) {
        let mut cube = cube.clone();
        cube.transform(Transformation333::Y);
        cube.transform(Transformation333::Z);
        self.arm_uf(&cube)
    }
    pub fn arm_bu(&self, cube: &Cube333) -> (u8, u8, u8) {
        let mut cube = cube.clone();
        cube.transform(Transformation333::Xi);
        self.arm_uf(&cube)
    }
    pub fn arm_ru(&self, cube: &Cube333) -> (u8, u8, u8) {
        let mut cube = cube.clone();
        cube.transform(Transformation333::Xi);
        cube.transform(Transformation333::Z);
        self.arm_uf(&cube)
    }
}


#[cfg(test)]
mod tests {
    use cubelib::defs::StepKind::DR;
    use cubelib::steps::coord::Coord;
    use cubelib::steps::dr::coords::DRUDEOFBCoord;
    use crate::{Cube, Solvable, Algorithm};
    use crate::dr::{DRUD, AR};

    #[test]
    fn test_drud_edge_visibility() {
        let mut cube = Cube::new("R".to_string()).unwrap();
        let drud = DRUD;
        for pos in 4..8 {
            for face in 0..2 {
                let viz = DRUD.edge_visibility(&cube.0, pos, face);
                print!("{}", viz);
            }
        }
    }

    #[test]
    fn test_ar() {
        let ar = AR;
        let mut cube = Cube::new("R U R'".to_string()).unwrap();
        assert_eq!(ar.arm_uf(&cube.0), (1, 1, 1));
        cube = Cube::new("R U F2 U R".to_string()).unwrap();
        assert_eq!(ar.arm_uf(&cube.0), (1, 1, 2));

        cube = Cube::new("D R D'".to_string()).unwrap();
        assert_eq!(ar.arm_rf(&cube.0), (1, 1, 1));
        cube = Cube::new("B U B'".to_string()).unwrap();
        assert_eq!(ar.arm_ur(&cube.0), (1, 1, 1));
        cube = Cube::new("D B D'".to_string()).unwrap();
        assert_eq!(ar.arm_br(&cube.0), (1, 1, 1));
        cube = Cube::new("R B R'".to_string()).unwrap();
        assert_eq!(ar.arm_bu(&cube.0), (1, 1, 1));
        cube = Cube::new("F R F'".to_string()).unwrap();
        assert_eq!(ar.arm_ru(&cube.0), (1, 1, 1));
    }

    #[test]
    fn test_drud_coord() {
        let mut cube = Cube::new("".to_string()).unwrap();
        let mut coord = DRUDEOFBCoord::from(&cube.0);
        cube.apply(&Algorithm::new("R").unwrap());
        coord = DRUDEOFBCoord::from(&cube.0);
        cube.apply(&Algorithm::new("U2").unwrap());
        coord = DRUDEOFBCoord::from(&cube.0);
        assert_eq!(coord.val(), 0);
    }
}
