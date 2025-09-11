use std::cell::RefCell;
use std::collections::HashSet;
use std::hash::Hash;

use cubelib::algs::Algorithm as LibAlgorithm;
use cubelib::cube::turn::ApplyAlgorithm;
use cubelib::cube::Cube333;
use cubelib::defs::{NissSwitchType, StepKind};
use cubelib::solver::solution::Solution;
use cubelib::solver_new::dr::DRBuilder;
use cubelib::solver_new::eo::EOBuilder;
use cubelib::solver_new::finish::HTRFinishBuilder;
use cubelib::solver_new::fr::FRBuilder;
use cubelib::solver_new::group::{StepGroup, StepPredicate, StepPredicateResult};
use cubelib::solver_new::htr::HTRBuilder;
use cubelib::solver_new::util_steps::{FilterFirstN, FilterLastMoveNotPrime};
use cubelib::steps::step::StepConfig;
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

    let solution = steps
        .into_worker(cube)
        .next()
        .ok_or_else(|| "No solutions found".to_string())
        .map_err(|e| PyValueError::new_err(e))?;
    let alg = Into::<LibAlgorithm>::into(solution).to_uninverted();
    Ok(format!("{}", alg))
}

pub fn group(active_step: StepKind, steps_to_solve: &Vec<StepConfig>) -> Result<StepGroup, String> {
    if steps_to_solve.is_empty() {
        return Err("No steps provided".to_string());
    }
    match (active_step.clone(), &steps_to_solve[0].kind) {
        (StepKind::Other(s), StepKind::DR | StepKind::HTR | StepKind::FR | StepKind::FIN)
            if s == "" =>
        {
            return Err(format!("Cannot jump to {}", &steps_to_solve[0].kind))
        }
        (StepKind::EO, StepKind::DR | StepKind::HTR | StepKind::FR | StepKind::FIN)
        | (StepKind::DR, StepKind::HTR | StepKind::FR | StepKind::FIN) => {
            return Err(format!(
                "Must solve {} before {}",
                active_step, &steps_to_solve[0].kind
            ))
        }
        (StepKind::DR | StepKind::HTR | StepKind::FR | StepKind::FIN, StepKind::EO)
        | (StepKind::HTR | StepKind::FR | StepKind::FIN, StepKind::DR)
        | (StepKind::FR | StepKind::FIN, StepKind::HTR)
        | (StepKind::FIN, StepKind::FR) => {
            return Err(format!("Already in {}", &steps_to_solve[0].kind))
        }
        (StepKind::Other(s), _) if s == "insertions" => {
            return Err(format!("Already in {}", &steps_to_solve[0].kind))
        }
        _ => (),
    }
    let step_groups = steps_to_solve
        .into_iter()
        .map(single_step)
        .collect::<Result<Vec<StepGroup>, _>>()?;
    let mut group = StepGroup::sequential(step_groups);
    if vec![StepKind::EO, StepKind::DR, StepKind::HTR]
        .contains(&steps_to_solve.last().unwrap().kind)
    {
        group.with_predicates(vec![FilterLastMoveNotPrime::new()]);
    }
    Ok(group)
}

fn single_step(step: &StepConfig) -> Result<StepGroup, String> {
    match step.kind {
        StepKind::EO => EOBuilder::try_from(step.clone())
            .map(|b| b.build())
            .map_err(|_| "Bad EO configuration".to_string()),
        StepKind::DR => DRBuilder::try_from(step.clone())
            .map(|b| b.build())
            .map_err(|_| "Bad DR configuration".to_string()),
        StepKind::HTR => HTRBuilder::try_from(step.clone())
            .map(|b| b.build())
            .map_err(|_| "Bad HTR configuration".to_string()),
        StepKind::FR | StepKind::FRLS => FRBuilder::try_from(step.clone())
            .map(|b| b.build())
            .map_err(|_| "Bad FR configuration".to_string()),
        StepKind::FIN | StepKind::FINLS => HTRFinishBuilder::try_from(step.clone())
            .map(|b| b.build())
            .map_err(|_| "Bad FIN configuration".to_string()),
        _ => Err(format!("Unsupported step kind: {:?}", step.kind)),
    }
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
    let mut step_config = single_step(&cfg).map_err(|e| PyValueError::new_err(e))?;

    let mut predicates = vec![];
    if require_canonical {
        predicates.push(FilterLastMoveNotPrime::new());
    }
    predicates.push(FilterFirstN::new(10000));
    predicates.push(FilterDupCaseID::new(cube.clone(), case_id));
    step_config.with_predicates(predicates);
    Ok(step_config
        .into_worker(cube.clone())
        .take(count)
        .map(|x| Algorithm(x.into()))
        .collect())
}

struct FilterDupCaseID<
    F: Fn(&Cube333, &LibAlgorithm) -> T + Sync + Send,
    T: Eq + Hash + Sync + Send,
>(Cube333, F, RefCell<HashSet<T>>);

impl<
        F: Fn(&Cube333, &LibAlgorithm) -> T + Sync + Send + 'static,
        T: Eq + Hash + Sync + Send + 'static,
    > FilterDupCaseID<F, T>
{
    pub fn new(cube: Cube333, case_id_fn: F) -> Box<dyn StepPredicate> {
        Box::new(Self(cube, case_id_fn, RefCell::new(Default::default())))
    }
}

impl<F: Fn(&Cube333, &LibAlgorithm) -> T + Sync + Send, T: Eq + Hash + Sync + Send> StepPredicate
    for FilterDupCaseID<F, T>
{
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

pub fn parse_steps(steps_str: &str) -> Result<Vec<StepConfig>, String> {
    let parts: Vec<&str> = steps_str.split(" > ").map(|s| s.trim()).collect();
    let mut steps = Vec::new();

    for part in parts {
        if part.is_empty() {
            continue;
        }

        // Parse each step like "EO[ud;fb;min=2;max=5;niss=always;limit=10]"
        let step_group = parse_single_step(part)?;
        steps.push(step_group);
    }
    if steps.is_empty() {
        return Err("No valid steps found".to_string());
    }
    Ok(steps)
}

pub fn parse_single_step(step_str: &str) -> Result<StepConfig, String> {
    // Find the step name and parameters
    let bracket_start = step_str.find('[');
    let bracket_end = step_str.find(']');

    let (step_name, params_str) = match (bracket_start, bracket_end) {
        (Some(start), Some(end)) if start < end => {
            let name = step_str[..start].trim().to_uppercase();
            let params = &step_str[start + 1..end];
            (name, Some(params))
        }
        _ => {
            let name = step_str.trim().to_uppercase();
            (name, None)
        }
    };

    // Parse parameters into a map
    let mut params = std::collections::HashMap::new();
    if let Some(params_str) = params_str {
        for param in params_str.split(';') {
            let param = param.trim();
            if param.is_empty() {
                continue;
            }

            if let Some(eq_pos) = param.find('=') {
                let key = param[..eq_pos].trim();
                let value = param[eq_pos + 1..].trim();
                params.insert(key.to_string(), value.to_string());
            } else {
                // No key means it's a variant
                params.insert("variant".to_string(), param.to_string());
            }
        }
    }

    // Parse niss parameter
    let niss_type = if let Some(niss_str) = params.get("niss") {
        match niss_str.as_str() {
            "never" => Some(NissSwitchType::Never),
            "before" => Some(NissSwitchType::Before),
            "always" => Some(NissSwitchType::Always),
            _ => return Err(format!("Unknown value niss={}", niss_str)),
        }
    } else {
        None
    };

    let step = StepConfig {
        kind: match step_name.as_str() {
            "EO" => StepKind::EO,
            "DR" => StepKind::DR,
            "HTR" => StepKind::HTR,
            "FR" => StepKind::FR,
            "FIN" => StepKind::FIN,
            "FINLS" => StepKind::FINLS,
            _ => return Err(format!("Unknown step type: {}", step_name)),
        },
        substeps: params
            .get("variant")
            .and_then(|s| Some(s.split(',').map(|s| s.trim().to_string()).collect())),
        min: None,
        max: params
            .get("max")
            .map(|s| {
                s.parse::<u8>()
                    .map_err(|_| format!("Invalid value max={}", s))
            })
            .transpose()?,
        absolute_min: None,
        absolute_max: params
            .get("abs-max")
            .map(|s| {
                s.parse::<u8>()
                    .map_err(|_| format!("Invalid value value abs-max={}", s))
            })
            .transpose()?,
        step_limit: params
            .get("limit")
            .map(|s| {
                s.parse::<usize>()
                    .map_err(|_| format!("Invalid value value limit={}", s))
            })
            .transpose()?,
        quality: 0,
        niss: niss_type,
        params: Default::default(),
    };
    Ok(step)
}
