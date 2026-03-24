# GitHub Copilot Coding Agent Instructions — Larrick Multi-Workflow Repository

This file is read automatically by GitHub Copilot Coding Agent when assigned to an issue.

## Repository Purpose

Larrick Multi is an engine simulation and surrogate-model optimization platform.
It is organized into five long-lived workflow branches, each owned by a distinct
engineering domain. Code never moves directly between workflow branches — all
cross-workflow sharing goes through `main`.

## Branch Ownership

| Branch | Owner Domain | Owned Paths |
|---|---|---|
| `dev/simulation` | Simulation pipeline | `src/larrak2/simulation_validation/`, `src/larrak2/pipelines/openfoam.py`, `src/larrak2/adapters/openfoam.py`, `src/larrak2/adapters/docker_openfoam.py`, `openfoam_custom_solvers/`, `openfoam_templates/`, `mechanisms/openfoam/` |
| `dev/training` | Surrogate training | `src/larrak2/training/`, `src/larrak2/surrogate/`, `src/larrak2/cli/train.py` |
| `dev/optimization` | Optimization & orchestration | `src/larrak2/optimization/`, `src/larrak2/promote/`, `src/larrak2/cli/run.py`, `src/larrak2/cli/run_workflows.py`, `src/larrak2/orchestration/simulation_inputs.py` |
| `dev/analysis` | Analysis & telemetry | `src/larrak2/analysis/` |
| `dev/cem-orchestration` | CEM & real-world backends | `src/larrak2/cem/`, `src/larrak2/realworld/`, `src/larrak2/orchestration/` (except `simulation_inputs.py`) |

Shared contract layer (read by all, modified via `main` PRs only):
- `src/larrak2/architecture/`

## Task Branch Naming

When Copilot creates a branch for an issue, use this format:

```
codex/<workflow>/<short-topic>
```

The `<workflow>` must match the owning branch for the paths being changed.
Examples: `codex/simulation/fix-doe-paths`, `codex/training/add-manifest-schema`

## Promotion Rules

1. Land code on the owning `dev/<workflow>` branch first (via PR from `codex/*` task branch).
2. Promote to `main` via PR from `dev/<workflow>`.
3. Other workflow branches pull from `main` — never directly from each other.
4. Artifacts (bundles, manifests) may be shared across branches for validation, but artifact sharing never substitutes for the code-promotion rule.

## What NOT to Touch

- Do **not** push directly to `main` or any `dev/*` branch — PRs are required.
- Do **not** edit files outside the owning workflow's paths unless explicitly instructed.
- Do **not** force-push to any protected branch.
- Do **not** add `contents: write` permission to any CI workflow.
- Do **not** merge one `dev/*` branch directly into another `dev/*` branch.

## CI Contract

Every PR must pass `Fast Checks (<workflow-name>)` before merge. The fast lane runs:
- `ruff format --check` + `ruff check` (lint)
- `mypy` on workflow-scoped paths
- `pytest -q` (full test suite or targeted subset per workflow)

Self-hosted heavy lanes (`heavy-self-hosted` jobs) are scaffolded but inactive
until hardware is attached. They are gated on `vars.LARRAK_ENABLE_SELF_HOSTED_*`
repo variables.

## Simulation Dataset Contract

Simulation outputs are shared through versioned manifest bundles
(`simulation_dataset_bundle.json`). Training and replay consumers must support
the current simulation API version and the immediately previous version.
Use `load_simulation_dataset_bundle()` from `src/larrak2/architecture/workflow_contracts.py`
to read these bundles — do not parse the JSON directly.
