use std::hash::Hash;
use std::cell::RefCell;
use std::collections::HashSet;

use cubelib::algs::Algorithm as LibAlgorithm;
use cubelib::cube::turn::{ApplyAlgorithm, CubeOuterTurn};
use cubelib::cube::Cube333;
use cubelib::cube::Direction;
use cubelib::defs::{NissSwitchType, StepKind};
use cubelib::solver::df_search::CancelToken;
use cubelib::solver::solve_steps;
use cubelib::solver::solution::Solution;
use cubelib::solver_new::dr::DRBuilder;
use cubelib::solver_new::eo::EOBuilder;
use cubelib::solver_new::htr::HTRBuilder;
use cubelib::solver_new::finish::HTRFinishBuilder;
use cubelib::solver_new::fr::FRBuilder;
use cubelib::solver_new::util_steps::{FilterFirstN, FilterLastMoveNotPrime};
use cubelib::solver_new::group::{StepGroup, StepPredicate, StepPredicateResult};
use cubelib::steps::solver::{build_steps, gen_tables};
use cubelib::steps::step::StepConfig;
use cubelib::steps::tables::PruningTables333;
use pyo3::exceptions::PyValueError;
use pyo3::{pyfunction, PyResult};

use crate::Algorithm;

#[pyfunction]
pub fn scramble() -> PyResult<String> {
    let cube = Cube333::random(&mut rand::rng());

    let eo = EOBuilder::default().build();
    let dr = DRBuilder::default().build();
    let htr = HTRBuilder::default().build();
    let finish = HTRFinishBuilder::default().build();

    let mut steps = StepGroup::sequential(vec![eo, dr, htr, finish]);
    steps.apply_step_limit(100);

    let solution = steps.into_worker(cube)
        .next()
        .ok_or_else(|| "No solutions found".to_string()).map_err(|e| PyValueError::new_err(e))?;
    let alg = Into::<LibAlgorithm>::into(solution).to_uninverted();
    Ok(format!("{}", alg))
}

pub fn step_config(kind: StepKind, variant: &str, niss: NissSwitchType) -> StepConfig {
    let substeps = match variant {
        "" => None,
        s => Some(vec![s.to_string()]),
    };
    StepConfig {
        kind: kind,
        substeps: substeps,
        min: None,
        max: Some(40),
        absolute_min: None,
        absolute_max: None,
        step_limit: None,
        quality: 0,
        niss: Some(niss),
        params: Default::default(),
    }
}

fn raw(cube: &Cube333, alg: &LibAlgorithm) -> [u64; 3] {
    let mut cube = cube.clone();
    cube.apply_alg(alg);
    let edges = cube.edges.get_edges_raw();
    let corners = cube.corners.get_corners_raw();
    [edges[0], edges[1], corners]
}

pub fn solve_step(
    cube: &Cube333,
    cfg: StepConfig,
    count: usize,
    require_canonical: bool,
) -> PyResult<Vec<Algorithm>> {
    solve_step_impl(cube, cfg, count, require_canonical, raw)
}

pub fn solve_step_deduplicated<F, T>(
    cube: &Cube333,
    cfg: StepConfig,
    n: usize,
    require_canonical: bool,
    case_id: F,
) -> PyResult<Vec<Algorithm>>
where
    F: Fn(&Cube333, &LibAlgorithm) -> T + Sync + Send + 'static,
    T: Eq + std::hash::Hash + Sync + Send + 'static,
{
    solve_step_impl(cube, cfg, n, require_canonical, case_id)
}

fn solve_step_impl<F, T>(
    cube: &Cube333,
    cfg: StepConfig,
    count: usize,
    require_canonical: bool,
    case_id: F,
) -> PyResult<Vec<Algorithm>>
where
    F: Fn(&Cube333, &LibAlgorithm) -> T + Sync + Send + 'static,
    T: Eq + std::hash::Hash + Sync + Send + 'static,
{
    let mut tables = Box::new(PruningTables333::new());
    let mut step_config = match cfg.kind {
        StepKind::EO => EOBuilder::try_from(cfg).map(|b| b.build()),
        StepKind::DR => DRBuilder::try_from(cfg).map(|b| b.build()),
        StepKind::HTR => HTRBuilder::try_from(cfg).map(|b| b.build()),
        StepKind::FR | StepKind::FRLS => FRBuilder::try_from(cfg).map(|b|b.build()),
        StepKind::FIN | StepKind::FINLS => HTRFinishBuilder::try_from(cfg).map(|b|b.build()),
        _ => unreachable!("Unexpected target step {}", cfg.kind)
    }.map_err(|e| PyValueError::new_err(e))?;

    let mut predicates = vec![];
    if require_canonical {
        predicates.push(FilterLastMoveNotPrime::new());
    }
    predicates.push(FilterFirstN::new(10000));
    predicates.push(FilterDupCaseID::new(cube.clone(), case_id));
    step_config.with_predicates(predicates);
    Ok(step_config.into_worker(cube.clone())
        .take(count)
        .map(|x| Algorithm(x.into()))
        .collect()
    )
}

struct FilterDupCaseID<F: Fn(&Cube333, &LibAlgorithm) -> T + Sync + Send, T: Eq + Hash + Sync + Send>(Cube333, F, RefCell<HashSet<T>>);

impl <F: Fn(&Cube333, &LibAlgorithm) -> T + Sync + Send + 'static, T: Eq + Hash + Sync + Send + 'static> FilterDupCaseID<F, T> {

    pub fn new(cube: Cube333, case_id_fn: F) -> Box<dyn StepPredicate> {
        Box::new(Self(
            cube,
            case_id_fn,
            RefCell::new(Default::default()),
        ))
    }
}

impl <F: Fn(&Cube333, &LibAlgorithm) -> T + Sync + Send, T: Eq + Hash + Sync + Send> StepPredicate for FilterDupCaseID<F, T> {
    fn check_solution(&self, solution: &Solution) -> StepPredicateResult {
        let alg: LibAlgorithm = solution.clone().into();
        let mut c = self.0.clone();
        c.apply_alg(&alg);
        let case_id = self.1(&c, &alg);
        if self.2.borrow_mut().insert(case_id) {
            StepPredicateResult::Accepted
        } else {
            StepPredicateResult::Rejected
        }
    }
}