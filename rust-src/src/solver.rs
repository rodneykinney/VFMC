use cubelib::algs::Algorithm as LibAlgorithm;
use cubelib::cube::turn::{ApplyAlgorithm, CubeOuterTurn};
use cubelib::cube::Cube333;
use cubelib::cube::Direction;
use cubelib::defs::StepKind;
use cubelib::solver::df_search::CancelToken;
use cubelib::solver::solve_steps;
use cubelib::steps::solver::{build_steps, gen_tables};
use cubelib::steps::step::StepConfig;
use cubelib::steps::tables::PruningTables333;
use pyo3::exceptions::PyValueError;
use pyo3::{pyfunction, PyResult};

use crate::Algorithm;

#[pyfunction]
pub fn scramble() -> PyResult<String> {
    let cube = Cube333::random(&mut rand::rng());

    let mut tables = PruningTables333::new();

    let mut step_configs = vec![
        step_config(StepKind::EO, ""),
        step_config(StepKind::DR, ""),
        step_config(StepKind::HTR, ""),
        step_config(StepKind::FIN, ""),
    ];
    step_configs
        .iter_mut()
        .for_each(|config| config.quality = 100);
    gen_tables(&step_configs, &mut tables);

    let steps = build_steps(step_configs, &tables).map_err(|e| PyValueError::new_err(e))?;
    let cancel_token = CancelToken::default();
    let mut solutions = solve_steps(cube, &steps, &cancel_token);

    let solution = solutions
        .next()
        .ok_or_else(|| PyValueError::new_err("No solutions found"))?;
    let alg = Into::<LibAlgorithm>::into(solution);
    let mut moves = alg.normal_moves.clone();
    let mut imoves = alg.inverse_moves.clone();
    imoves.reverse();
    moves.append(&mut imoves);
    let alg = LibAlgorithm {
        normal_moves: moves,
        inverse_moves: vec![],
    };
    Ok(format!("{}", alg))
}

pub fn step_config(kind: StepKind, variant: &str) -> StepConfig {
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
        niss: None,
        params: Default::default(),
    }
}

fn raw(cube: &Cube333, alg: &Algorithm) -> [u64; 3] {
    let mut cube = cube.clone();
    cube.apply_alg(&alg.0);
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
    F: Fn(&Cube333, &Algorithm) -> T,
    T: Eq + std::hash::Hash,
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
    F: Fn(&Cube333, &Algorithm) -> T,
    T: Eq + std::hash::Hash,
{
    let mut tables = Box::new(PruningTables333::new());
    let mut step_configs = match cfg.kind {
        StepKind::DR => vec![step_config(StepKind::EO, "")],
        StepKind::HTR => vec![step_config(StepKind::EO, ""), step_config(StepKind::DR, "")],
        StepKind::FR | StepKind::FRLS | StepKind::FINLS | StepKind::FIN => vec![
            step_config(StepKind::EO, ""),
            step_config(StepKind::DR, ""),
            step_config(StepKind::HTR, ""),
        ],
        _ => vec![],
    };
    step_configs.iter_mut().for_each(|config| {
        config.step_limit = Some(1);
        config.max = Some(0);
    });
    step_configs.push(cfg);
    gen_tables(&step_configs, &mut tables);

    let steps = build_steps(step_configs, &tables).map_err(PyValueError::new_err)?;
    let cancel_token = CancelToken::default();
    let algs = solve_steps(cube.clone(), &steps, &cancel_token)
        .map(Into::<LibAlgorithm>::into)
        .map(Algorithm);
    let algs = algs.filter(|a| !require_canonical || is_canonical(a));
    let mut seen_ids = std::collections::HashSet::new();
    let mut deduped_algs = Vec::new();
    let mut seen = 0;
    for alg in algs {
        seen += 1;
        let mut c = cube.clone();
        c.apply_alg(&alg.0);
        let id = case_id(&c, &alg);
        if seen_ids.insert(id) {
            deduped_algs.push(alg);
        }
        if deduped_algs.len() >= count || seen > 10000 {
            break;
        }
    }
    Ok(deduped_algs)
}

pub fn is_canonical(alg: &Algorithm) -> bool {
    fn is_canonical(vec: &Vec<CubeOuterTurn>) -> bool {
        match vec.len() {
            0 => true,
            1 => vec[0].dir != Direction::CounterClockwise,
            n => {
                vec[n - 1].dir != Direction::CounterClockwise
                    && (vec[n - 2].face != vec[n - 1].face.opposite()
                        || vec[n - 2].dir != Direction::CounterClockwise)
            }
        }
    }
    is_canonical(&alg.0.normal_moves) && is_canonical(&alg.0.inverse_moves)
}
