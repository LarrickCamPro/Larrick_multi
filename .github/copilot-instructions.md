# GitHub Copilot Coding Agent Instructions — Larrick Multi Repository

This file is read automatically by GitHub Copilot Coding Agent when assigned to
an issue.

## Repository Purpose

Larrick Multi is an engine simulation and surrogate-model optimization platform.
The codebase still groups work by engineering domain, but branch governance is
no longer part of the repo workflow. The domain map below is kept as
documentation only and is intended to help a future split into separate
projects.

## Workflow Model

- `main` is the only documented repo workflow branch.
- Direct commits to `main` are the default working model for this repository.
- Temporary Git branches may still exist, but the repo does not define,
  validate, or automate any branch naming convention.
- Do not assume any workflow-routing, promotion, or branch-ownership automation
  exists.

### Optional: Cursor worktree plugin

This repo may ship the in-tree plugin at [`.cursor/plugins/larrick-worktree-workflow/`](.cursor/plugins/larrick-worktree-workflow/). When that plugin is **enabled** in Cursor, it adds stricter conventions on top of the baseline above: see [`rules/workflow-ownership.mdc`](.cursor/plugins/larrick-worktree-workflow/rules/workflow-ownership.mdc) and [`hooks/hooks.json`](.cursor/plugins/larrick-worktree-workflow/hooks/hooks.json). Plain terminal git users are not required to follow plugin rules unless the team adopts them.

### Umbrella documentation (CamPro parent checkout)

When this repository lives inside the Larrick-CamPro umbrella (sibling `docs/`, `larrak-*` trees), also see [`../docs/developer-experience/agent-workflow-playbook.md`](../docs/developer-experience/agent-workflow-playbook.md), [`../docs/solutions/`](../docs/solutions/), and [`../docs/project_status/agent_native_architecture_audit.md`](../docs/project_status/agent_native_architecture_audit.md).

## Domain Ownership (Documentation Only)

| Domain | Primary Paths |
|---|---|
| Simulation validation (CLI glue) | `src/larrak2/cli/validate_simulation.py` (imports `larrak_simulation.simulation_validation.*`); repo data under `data/simulation_validation/` |
| OpenFOAM and CFD adapters | `src/larrak2/adapters/openfoam.py`, `src/larrak2/adapters/docker_openfoam.py`, `openfoam_custom_solvers/`, `openfoam_templates/`, `mechanisms/openfoam/` |
| Pipelines (principles, explore–exploit) | `src/larrak2/pipelines/` |
| Surrogate stack and training entrypoints | `src/larrak2/surrogate/`, `src/larrak2/cli/train.py` |
| Optimization | `src/larrak2/optimization/` (solvers, scaling, slicing, IPOPT glue) |
| Promotion and workflow CLI | `src/larrak2/promote/`, `src/larrak2/cli/run.py`, `src/larrak2/cli/run_workflows.py`, `src/larrak2/cli/run_pareto.py`, `src/larrak2/cli/refine_pareto.py` |
| Orchestration and adapters | `src/larrak2/orchestration/` (`orchestrator.py`, `multi_start.py`, `parameters.py`, `adapters/{cem,simulation,surrogate}_adapter.py`) |
| Gear, geometry, machining | `src/larrak2/gear/`, `src/larrak2/geometry/`, `src/larrak2/machining/` |
| Core, artifacts, ports | `src/larrak2/core/`, `src/larrak2/artifacts/`, `src/larrak2/ports/` |
| External algorithm adapters | `src/larrak2/adapters/pymoo_problem.py`, `casadi_refine.py`, `calculix.py` |
| Shared architecture contracts | `src/larrak2/architecture/` |

Treat this mapping as guidance for review and future extraction work, not as an
enforced branch or PR policy.

## Working Expectations

- Prefer small, reviewable changes even when working directly on `main`.
- If a change spans multiple domains, call that out clearly in the summary and
  keep interfaces stable where possible.
- Do not force-push protected branches.
- Do not add `contents: write` permission to CI workflows.

## CI Contract

The repository uses a single `CI` workflow for pushes to `main` and pull
requests targeting `main`. The fast lane runs:

- `ruff format --check` and `ruff check`
- `mypy` on the maintained typed entrypoints
- `pytest -q` (default `testpaths`: `tests/ci_contract` only per `[tool.pytest.ini_options]` in `pyproject.toml`)

Self-hosted heavy lanes may still exist in the future, but they are not tied to
branch-specific workflow wrappers anymore.

## Simulation Dataset Contract

Simulation outputs are shared through versioned manifest bundles
(`simulation_dataset_bundle.json`). Training and replay consumers must support
the current simulation API version and the immediately previous version.
Use `load_simulation_dataset_bundle()` from
`src/larrak2/architecture/workflow_contracts.py` to read these bundles rather
than parsing the JSON directly.
