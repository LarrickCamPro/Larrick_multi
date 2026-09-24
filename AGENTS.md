# Agent Context — Larrick Multi Repository

This file is read by OpenAI Codex, Google Gemini, and other AI coding agents.
Before making changes, read this file in full.

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

This repo may ship the in-tree plugin at [`.cursor/plugins/larrick-worktree-workflow/`](.cursor/plugins/larrick-worktree-workflow/). When that plugin is **enabled** in Cursor, it adds **stricter** conventions on top of the baseline above: see [`rules/workflow-ownership.mdc`](.cursor/plugins/larrick-worktree-workflow/rules/workflow-ownership.mdc) (branch naming, promotion branches, no direct push to `main` or `dev/*` from the agent shell) and [`hooks/hooks.json`](.cursor/plugins/larrick-worktree-workflow/hooks/hooks.json) (guarded `git push` / `git checkout`). Contributors using only a terminal and plain git are **not** required to follow those plugin rules unless their team chooses to adopt them.

In Cursor, `alwaysApply: true` on that plugin’s `.mdc` rules only controls **whether the rule file is loaded** for sessions using this repo—not a claim that every contributor must follow branch naming outside the plugin. Baseline policy remains this section unless your team turns on the plugin and agrees to its workflow.

## External modules

- **Umbrella / local dev (CamPro):** `larrak-core` (Python import **`larrak_runtime`**), `larrak-engines`, `larrak-simulation`, `larrak-optimization`, `larrak-analysis`, and `larrak-orchestration` are declared in [`pyproject.toml`](pyproject.toml). In the CamPro umbrella layout, the `[tool.uv.sources]` table there resolves them to **editable** sibling checkouts (`path = "../larrak-…"`). Use `uv sync` (and `--extra dev` for lint/tests). None are git submodules.
- **Standalone / wheels:** Without sibling path sources, install from **pinned git URLs** in [`requirements-external.txt`](requirements-external.txt), normally via [`scripts/install_external_larrak.sh`](scripts/install_external_larrak.sh) (pip install and monorepo `data/` symlink for wheel-installed `larrak_runtime`).
- LEAP71 PicoGK/ShapeKernel vendor trees remain external clones. Set **`LARRICK_MULTI_ROOT`** to this repository root when packaged code must resolve `data/` paths.

## Umbrella documentation (CamPro parent)

When this checkout lives inside the Larrick-CamPro umbrella (sibling `docs/`, `larrak-*` trees):

- **`../docs/solutions/`** — documented solutions (bugs, workflow, best practices) by category, with YAML frontmatter (`module`, `tags`, `problem_type`). Useful when debugging integration across packages.
- **`../docs/project_status/`** — port manifests, parity checklists, and the [agent native architecture audit](../docs/project_status/agent_native_architecture_audit.md).
- In-repo **agent workflow parity** (document / refresh / review / architecture passes): [agent-workflow-playbook.md](../docs/developer-experience/agent-workflow-playbook.md).
- Example umbrella learning: [engine-suite-campro-umbrella-and-uv-sources-2026-04-19.md](../docs/solutions/workflow-issues/engine-suite-campro-umbrella-and-uv-sources-2026-04-19.md).

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
- `pytest -q` (default `testpaths`: `tests/ci_contract` only)

Self-hosted heavy lanes may still exist in the future, but they are not tied to
branch-specific workflow wrappers anymore.

The **Repo Layout** workflow also runs `scripts/check_json_no_absolute_paths.py` on tracked `*.json` (machine-local path markers). Allowlisted Cursor command stubs live under [`.cursor/commands/`](.cursor/commands/); the umbrella documents the full CLI contract and artifact retirement rules in [`../docs/project_status/cli_contract_for_agents.md`](../docs/project_status/cli_contract_for_agents.md) and [`../docs/project_status/artifact_lifecycle_for_agents.md`](../docs/project_status/artifact_lifecycle_for_agents.md).

## Cursor Worktree Workflow

- Manual domain separation: open one Cursor window per `git worktree` directory.
- Cursor Parallel Agents create Cursor-managed worktrees and apply edits back via
  the Cursor "Apply" action.
- Keep branch naming short, descriptive, and consistent within your team.
- In Cursor-created worktrees, rely on CLI checks (`ruff`, `mypy`, `pytest`) for
  validation because LSP diagnostics are not available in that environment.
- Cursor-specific hooks/setup should delegate to portable stubs in
  `scripts/worktree_agent/` so open-source editor/agent replacements can reuse
  the same workflow contract across all five development branches.

## Simulation Dataset Contract

Simulation outputs are shared through versioned manifest bundles
(`simulation_dataset_bundle.json`). Training and replay consumers must support
the current simulation API version and the immediately previous version.
Use `load_simulation_dataset_bundle()` from
`src/larrak2/architecture/workflow_contracts.py` to read these bundles rather
than parsing the JSON directly.
