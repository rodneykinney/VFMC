mod dr;
mod eo;
mod finish;
mod fr;
mod htr;
mod slice;
mod solver;

use pyo3::prelude::*;
use std::str::FromStr;

use pyo3::exceptions::PyValueError;

use crate::dr::{DRFB, DRRL, DRUD};
use crate::eo::{EOFB, EORL, EOUD};
use crate::finish::Finish;
use crate::fr::{FRFB, FRRL, FRUD};
use crate::htr::{HTRFB, HTRRL, HTRUD};
use crate::slice::{SliceFB, SliceRL, SliceUD};
use crate::solver::scramble;
use crate::Visibility::Any;
use cubelib::algs::Algorithm as LibAlgorithm;
use cubelib::cube::turn::{ApplyAlgorithm, Direction, Invertible, InvertibleMut};
use cubelib::cube::{Corner, Cube333, Edge, Turn333};

#[pyclass]
struct Algorithm(LibAlgorithm);

#[pymethods]
impl Algorithm {
    #[new]
    fn new(s: &str) -> PyResult<Self> {
        let alg = LibAlgorithm::from_str(s)
            .map_err(|_| PyValueError::new_err(format!("Invalid algorithm: {}", s)))?;
        Ok(Algorithm(alg))
    }

    fn normal_moves(&self) -> Vec<String> {
        self.0
            .normal_moves
            .iter()
            .map(|t| format!("{}", t))
            .collect()
    }

    fn inverse_moves(&self) -> Vec<String> {
        self.0
            .inverse_moves
            .iter()
            .map(|t| format!("{}", t))
            .collect()
    }

    fn is_empty(&self) -> bool {
        self.0.normal_moves.is_empty() && self.0.inverse_moves.is_empty()
    }

    fn len(&self) -> usize {
        self.0.normal_moves.len() + self.0.inverse_moves.len()
    }

    fn append(&self, s: &str, inverse: bool) -> PyResult<Algorithm> {
        let turn = Turn333::from_str(s)
            .map_err(|_| PyValueError::new_err(format!("Invalid move: {}", s)))?;
        let alg = append_move(&self.0, turn, inverse);
        Ok(Algorithm(alg))
    }

    fn merge(&self, other: &Algorithm) -> Algorithm {
        let mut alg = self.0.clone();
        for turn in other.0.normal_moves.iter() {
            alg = append_move(&alg, *turn, false);
        }
        for turn in other.0.inverse_moves.iter() {
            alg = append_move(&alg, *turn, true);
        }
        Algorithm(alg)
    }

    fn inverted(&self) -> Algorithm {
        let mut alg = self.0.clone();
        alg.invert();
        Algorithm(alg)
    }

    fn on_inverse(&self) -> Algorithm {
        let alg = self.0.clone();
        let alg = LibAlgorithm {
            normal_moves: alg.inverse_moves,
            inverse_moves: alg.normal_moves,
        };
        Algorithm(alg)
    }

    fn __repr__(&self) -> String {
        format!("{}", self.0)
    }
}

fn append_move(alg: &LibAlgorithm, turn: Turn333, inverse: bool) -> LibAlgorithm {
    let mut new_moves = if inverse {
        alg.inverse_moves.clone()
    } else {
        alg.normal_moves.clone()
    };
    let mut cancels = false;
    for i in (0..new_moves.len()).rev() {
        let last_move = new_moves[i];
        if last_move == turn.invert() {
            cancels = true;
            new_moves.remove(i);
            break;
        } else if last_move.face == turn.face {
            match (last_move.dir, turn.dir) {
                (Direction::Half, _) => {
                    cancels = true;
                    new_moves[i] = turn.invert();
                    break;
                }
                (_, Direction::Half) => {
                    cancels = true;
                    new_moves[i] = last_move.invert();
                    break;
                }
                (_, _) => {
                    cancels = true;
                    new_moves[i] = Turn333 {
                        face: turn.face,
                        dir: Direction::Half,
                    };
                    break;
                }
            }
        } else if last_move.face != turn.face.opposite() {
            break;
        }
    }
    if !cancels {
        new_moves.push(turn);
    }
    if inverse {
        LibAlgorithm {
            normal_moves: alg.normal_moves.clone(),
            inverse_moves: new_moves,
        }
    } else {
        LibAlgorithm {
            normal_moves: new_moves,
            inverse_moves: alg.inverse_moves.clone(),
        }
    }
}

#[pyclass]
#[derive(Clone)]
struct Cube(Cube333);

#[pymethods]
impl Cube {
    #[new]
    fn new(scramble: String) -> PyResult<Self> {
        let alg = LibAlgorithm::from_str(&scramble)
            .map_err(|_| PyValueError::new_err("Invalid scramble"))?;
        let mut cube = Cube333::default();
        cube.apply_alg(&alg);
        Ok(Cube(cube))
    }

    fn edges(&self) -> PyResult<Vec<(u8, u8)>> {
        let bytes = self.0.edges.get_edges_raw();
        let mut edges = vec![];
        for i in 0..8 {
            let id = (bytes[0] >> (8 * i + 4) & 0xf) as u8;
            let orientation = (bytes[0] >> (8 * i + 1) & 0x7) as u8;
            edges.push((id, orientation));
        }
        for i in 0..4 {
            let id = (bytes[1] >> (8 * i + 4) & 0xf) as u8;
            let orientation = (bytes[1] >> (8 * i + 1) & 0x7) as u8;
            edges.push((id, orientation));
        }
        Ok(edges)
    }

    fn corners(&self) -> PyResult<Vec<(u8, u8)>> {
        let bytes = self.0.corners.get_corners_raw();
        let mut corners = vec![];
        for i in 0..8 {
            let id = (bytes >> (8 * i + 5) & 0x7) as u8;
            let orientation = (bytes >> (8 * i) & 0x3) as u8;
            corners.push((id, orientation));
        }
        Ok(corners)
    }

    fn apply(&mut self, alg: &Algorithm) {
        self.0.apply_alg(&alg.0.clone());
    }

    fn invert(&mut self) {
        self.0.invert()
    }
}

// The Python module definition
#[pymodule]
fn vfmc_core(_py: Python, m: &PyModule) -> PyResult<()> {
    // Register the classes
    m.add_class::<Cube>()?;
    m.add_class::<Algorithm>()?;
    m.add_class::<StepInfo>()?;

    m.add_function(wrap_pyfunction!(debug, m)?)?;
    m.add_function(wrap_pyfunction!(scramble, m)?)?;
    Ok(())
}

trait DrawableEdge {
    fn facelet_showing_ud(&self) -> Option<u8>;
    fn facelet_showing_fb(&self) -> Option<u8>;
    fn facelet_showing_rl(&self) -> Option<u8>;
}
impl DrawableEdge for Edge {
    fn facelet_showing_ud(&self) -> Option<u8> {
        match self.id / 4 {
            1 => None,
            _ => Some(0),
        }
    }
    fn facelet_showing_fb(&self) -> Option<u8> {
        match self.id / 4 {
            1 => Some(0),
            _ if self.id % 2 == 0 => Some(1),
            _ => None,
        }
    }
    fn facelet_showing_rl(&self) -> Option<u8> {
        match self.id / 4 {
            1 => Some(1),
            _ if self.id % 2 == 1 => Some(1),
            _ => None,
        }
    }
}

#[pyfunction]
fn debug(cube: &Cube) -> String {
    let cube = cube.0;
    let e = cube.edges.get_edges();
    format!(
        "4: {} 5: {} 6: {} 7: {}",
        e[4].id, e[5].id, e[6].id, e[7].id
    )
}

trait DrawableCorner {
    fn oriented_ud(&self, pos: u8) -> bool;
    fn oriented_fb(&self, pos: u8) -> bool;
    fn oriented_rl(&self, pos: u8) -> bool;
    fn facelet_showing_ud(&self) -> u8;
    fn facelet_showing_fb(&self) -> u8;
    fn facelet_showing_rl(&self) -> u8;
}
impl DrawableCorner for Corner {
    fn oriented_ud(&self, _pos: u8) -> bool {
        self.orientation == 0
    }

    fn oriented_fb(&self, pos: u8) -> bool {
        match (self.id + pos) % 2 {
            0 => self.orientation == 0,
            _ => self.orientation == 2 - (self.id % 2),
        }
    }

    fn oriented_rl(&self, pos: u8) -> bool {
        match (self.id + pos) % 2 {
            0 => self.orientation == 0,
            _ => self.orientation == 1 + (self.id % 2),
        }
    }

    fn facelet_showing_ud(&self) -> u8 {
        self.orientation
    }

    fn facelet_showing_fb(&self) -> u8 {
        (self.orientation + 2 - (self.id % 2)) % 3
    }

    fn facelet_showing_rl(&self) -> u8 {
        (self.orientation + 1 + (self.id % 2)) % 3
    }
}

#[pyclass]
pub struct StepInfo {
    #[pyo3(get)]
    pub kind: String,
    #[pyo3(get)]
    pub variant: String,
}

impl StepInfo {
    fn step(&self) -> Result<Box<dyn Solvable>, String> {
        StepBuilder::from_kind(&self.kind, &self.variant)
    }
}

#[pymethods]
impl StepInfo {
    fn are_moves_allowed(&self, alg: &Algorithm) -> PyResult<bool> {
        let mut cube = Cube333::default();
        cube.apply_alg(&alg.0);
        self.is_solved(&Cube(cube))
    }

    fn is_solved(&self, cube: &Cube) -> PyResult<bool> {
        Ok(self
            .step()
            .map_err(|e| PyValueError::new_err(e.to_string()))?
            .is_solved(&cube.0))
    }

    fn is_eligible(&self, cube: &Cube) -> PyResult<bool> {
        Ok(self
            .step()
            .map_err(|e| PyValueError::new_err(e.to_string()))?
            .is_eligible(&cube.0))
    }

    fn case_name(&self, cube: &Cube) -> PyResult<String> {
        Ok(self
            .step()
            .map_err(|e| PyValueError::new_err(e.to_string()))?
            .case_name(&cube.0))
    }

    fn edge_visibility(&self, cube: &Cube) -> PyResult<Vec<(u8, u8)>> {
        let step = self
            .step()
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        let mut vec = vec![];
        for i in 0..12 {
            vec.push((
                step.edge_visibility(&cube.0, i, 0) as u8,
                step.edge_visibility(&cube.0, i, 1) as u8,
            ));
        }
        Ok(vec)
    }

    fn corner_visibility(&self, cube: &Cube) -> PyResult<Vec<(u8, u8, u8)>> {
        let step = self
            .step()
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        let mut vec = vec![];
        for i in 0..8 {
            vec.push((
                step.corner_visibility(&cube.0, i, 0) as u8,
                step.corner_visibility(&cube.0, i, 1) as u8,
                step.corner_visibility(&cube.0, i, 2) as u8,
            ));
        }
        Ok(vec)
    }

    fn solve(&self, cube: &Cube, count: usize) -> PyResult<Vec<Algorithm>> {
        self.step()
            .map_err(|e| PyValueError::new_err(e.to_string()))?
            .solve(&cube.0, count)
    }

    #[new]
    fn new(kind: &str, variant: &str) -> PyResult<Self> {
        Ok(StepInfo {
            kind: kind.to_string(),
            variant: variant.to_string(),
        })
    }
}

pub enum Visibility {
    Any = 1,
    BadFace = 2,
    BadPiece = 4,
    HtrD = 8,
    TopColor = 16,
}

trait Solvable {
    fn is_solved(&self, cube: &Cube333) -> bool;
    fn is_eligible(&self, cube: &Cube333) -> bool;
    fn case_name(&self, cube: &Cube333) -> String;
    fn edge_visibility(&self, cube: &Cube333, pos: usize, facelet: u8) -> u8;
    fn corner_visibility(&self, cube: &Cube333, pos: usize, facelet: u8) -> u8;
    fn solve(&self, cube: &Cube333, count: usize) -> PyResult<Vec<Algorithm>>;
}
struct StepBuilder;
impl StepBuilder {
    fn from_kind(kind: &str, variant: &str) -> Result<Box<dyn Solvable>, String> {
        match kind {
            "eo" => match variant {
                "fb" => Ok(Box::new(EOFB)),
                "rl" => Ok(Box::new(EORL)),
                "ud" => Ok(Box::new(EOUD)),
                _ => Err(format!("Unknown variant '{}' for eo", variant).into()),
            },
            "dr" => match variant {
                "fb" => Ok(Box::new(DRFB)),
                "rl" => Ok(Box::new(DRRL)),
                "ud" => Ok(Box::new(DRUD)),
                _ => Err(format!("Unknown variant '{}' for dr", variant).into()),
            },
            "htr" => match variant {
                "fb" => Ok(Box::new(HTRFB)),
                "rl" => Ok(Box::new(HTRRL)),
                "ud" => Ok(Box::new(HTRUD)),
                _ => Err(format!("Unknown variant '{}' for dr", variant).into()),
            },
            "fr" => match variant {
                "ud" => Ok(Box::new(FRUD)),
                "fb" => Ok(Box::new(FRFB)),
                "rl" => Ok(Box::new(FRRL)),
                _ => Err(format!("Unknown variant '{}' for dr", variant).into()),
            },
            "slice" => match variant {
                "ud" => Ok(Box::new(SliceUD)),
                "fb" => Ok(Box::new(SliceFB)),
                "rl" => Ok(Box::new(SliceRL)),
                _ => Err(format!("Unknown variant '{}' for dr", variant).into()),
            },
            "finish" => Ok(Box::new(Finish)),
            "" => Ok(Box::new(SCRAMBLED)),
            _ => Err(format!("Unknown step '{}'", kind).into()),
        }
    }
}

pub struct SCRAMBLED;
impl Solvable for SCRAMBLED {
    fn is_solved(&self, _cube: &Cube333) -> bool {
        true
    }
    fn is_eligible(&self, _cube: &Cube333) -> bool {
        true
    }
    fn case_name(&self, _cube: &Cube333) -> String {
        "".to_string()
    }
    fn edge_visibility(&self, _cube: &Cube333, _pos: usize, _facelet: u8) -> u8 {
        Any as u8
    }
    fn corner_visibility(&self, _cube: &Cube333, _pos: usize, _facelet: u8) -> u8 {
        Any as u8
    }
    fn solve(&self, _cube: &Cube333, _count: usize) -> PyResult<Vec<Algorithm>> {
        Err(PyValueError::new_err("Direct solver is not implemented"))
    }
}

const EDGE_UD_FACELETS: [Option<u8>; 12] = [
    Some(0),
    Some(0),
    Some(0),
    Some(0),
    None,
    None,
    None,
    None,
    Some(0),
    Some(0),
    Some(0),
    Some(0),
];
const EDGE_FB_FACELETS: [Option<u8>; 12] = [
    Some(1),
    None,
    Some(1),
    None,
    Some(0),
    Some(0),
    Some(0),
    Some(0),
    Some(1),
    None,
    Some(1),
    None,
];
const EDGE_RL_FACELETS: [Option<u8>; 12] = [
    None,
    Some(1),
    None,
    Some(1),
    Some(1),
    Some(1),
    Some(1),
    Some(1),
    None,
    Some(1),
    None,
    Some(1),
];
const CORNER_UD_FACELETS: [u8; 8] = [0, 0, 0, 0, 0, 0, 0, 0];
const CORNER_FB_FACELETS: [u8; 8] = [2, 1, 2, 1, 2, 1, 2, 1];
const CORNER_RL_FACELETS: [u8; 8] = [1, 2, 1, 2, 1, 2, 1, 2];

const EDGE_OPPOSITE_E_SLICE: [u8; 12] = [10, 9, 8, 11, 4, 5, 6, 7, 2, 1, 0, 3];
const EDGE_OPPOSITE_S_SLICE: [u8; 12] = [2, 1, 0, 3, 6, 7, 4, 5, 10, 9, 8, 11];
const EDGE_OPPOSITE_M_SLICE: [u8; 12] = [0, 3, 2, 1, 5, 4, 7, 6, 8, 11, 10, 9];

const CORNER_OPPOSITE_E_SLICE: [u8; 8] = [7, 6, 5, 4, 3, 2, 1, 0];
const CORNER_OPPOSITE_S_SLICE: [u8; 8] = [3, 2, 1, 0, 7, 6, 5, 4];
const CORNER_OPPOSITE_M_SLICE: [u8; 8] = [1, 0, 3, 2, 5, 4, 7, 6];

#[cfg(test)]
mod tests {
    use super::*;
    use crate::Solvable;
    use crate::Visibility::BadFace;

    #[test]
    fn algorithm_append() {
        let alg = Algorithm::new("").unwrap();
        let alg = alg.append("F", false).unwrap();
        assert_eq!(format!("{}", alg.0), "F");
        let alg = alg.append("F'", false).unwrap();
        assert_eq!(format!("{}", alg.0), "");
        let alg = alg.append("F", false).unwrap();
        let alg = alg.append("F", false).unwrap();
        assert_eq!(format!("{}", alg.0), "F2");
        let alg = alg.append("B2", false).unwrap();
        assert_eq!(format!("{}", alg.0), "F2 B2");
        let alg = alg.append("F", false).unwrap();
        assert_eq!(format!("{}", alg.0), "F' B2");

        let alg = Algorithm::new("").unwrap();
        let alg = alg.append("F", true).unwrap();
        assert_eq!(format!("{}", alg.0), "(F)");
        let alg = alg.append("F'", true).unwrap();
        assert_eq!(format!("{}", alg.0), "");
        let alg = alg.append("F", true).unwrap();
        let alg = alg.append("F", true).unwrap();
        assert_eq!(format!("{}", alg.0), "(F2)");
        let alg = alg.append("B2", true).unwrap();
        assert_eq!(format!("{}", alg.0), "(F2 B2)");
        let alg = alg.append("F", true).unwrap();
        assert_eq!(format!("{}", alg.0), "(F' B2)");
        let alg = alg.append("F", false).unwrap();
        assert_eq!(format!("{}", alg.0), "F (F' B2)");
    }

    #[test]
    fn scramble_gen() {
        let s = scramble().unwrap();
        assert!(s.len() > 0);
    }

    #[test]
    fn test_visibility() {
        let cube = Cube::new("R U F".to_string()).unwrap();
        let s = StepInfo {
            kind: "eo".to_string(),
            variant: "fb".to_string(),
        };
        let visibility = s.edge_visibility(&cube).unwrap();
        assert!(visibility[2].0 & BadFace as u8 > 0);
        let s = StepInfo {
            kind: "htr".to_string(),
            variant: "ud".to_string(),
        };
        let visibility = s.edge_visibility(&cube).unwrap();
        assert!(visibility[0].0 & BadFace as u8 > 0);
    }
}
