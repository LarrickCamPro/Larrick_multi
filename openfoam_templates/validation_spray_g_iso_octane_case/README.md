# Validation Spray G Iso-Octane Case

This tracked OpenFOAM validation template anchors the Spray G leg of the
gas-combustion truth suite.

The template now includes a repo-contained OpenFOAM case deck:
- `0/`, `constant/`, and `system/`
- materialized mesh and field snapshots under `0.0001/`, `0.0002/`, `0.0003/`
- `constant/polyMesh/` and `constant/triSurface/`

Those case files were promoted from the local materialized authority run at
`outputs/openfoam_doe_small_real/runs/case_000000` so the validation path is no
longer sidecar-only.

The regime-specific validation metrics still come from the tracked
`openfoam_metrics.json` sidecar. That means this template is structurally a full
case deck, but the Spray G metric extraction remains artifact-backed until a
dedicated `sprayFoam` validation deck and post-processor are finalized.
