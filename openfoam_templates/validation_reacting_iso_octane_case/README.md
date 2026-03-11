# Validation Reacting Iso-Octane Case

This tracked OpenFOAM validation template anchors the reacting-flow leg of the
gas-combustion truth suite.

The template now includes a repo-contained OpenFOAM case deck:
- `0/`, `constant/`, and `system/`
- materialized mesh and field snapshots under `0.0001/`, `0.0002/`, `0.0003/`
- `constant/polyMesh/` and `constant/triSurface/`

Those case files were promoted from the local materialized tracer-backed run at
`outputs/openfoam_tracer_smoke_escalated_v2/runs/case_000000` so the reacting
validation path is no longer sidecar-only.

The regime-specific reacting metrics still come from the tracked
`openfoam_metrics.json` sidecar. This makes the template a full case deck with
real field artifacts, while the final solver-specific `reactingFoam` validation
deck and metric extractor are still being hardened.
