# Validation Reacting Iso-Octane Case

This tracked OpenFOAM validation template anchors the reacting-flow leg of the
gas-combustion truth suite.

The template now includes a repo-contained solver-specific case deck:
- `0/`, `constant/`, and `system/`
- materialized mesh and field snapshots under `0.0001/`, `0.0002/`, `0.0003/`
- `constant/polyMesh/` and `constant/triSurface/`
- `constant/combustionProperties` and `constant/chemistryProperties`
- species fields in `0/CO2` and `0/OH`
- `system/reactingValidationDict`
- sampled validation outputs under `postProcessing/reactingValidation/`

Those case files were promoted from the local materialized tracer-backed run at
`outputs/openfoam_tracer_smoke_escalated_v2/runs/case_000000` so the reacting
validation path is no longer sidecar-only.

The live validation adapter now reads temperature, species, and bulk-velocity
metrics from `postProcessing/reactingValidation/` artifacts produced by the
`reactingFoam` case deck. The legacy `openfoam_metrics.json` file remains for
compatibility only and is not the strict-authority source.
