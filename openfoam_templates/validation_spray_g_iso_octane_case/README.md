# Validation Spray G Iso-Octane Case

This tracked OpenFOAM validation template anchors the Spray G leg of the
gas-combustion truth suite.

The template now includes a repo-contained solver-specific case deck:
- `0/`, `constant/`, and `system/`
- materialized mesh and field snapshots under `0.0001/`, `0.0002/`, `0.0003/`
- `constant/polyMesh/` and `constant/triSurface/`
- `constant/sprayCloudProperties`, `constant/fuelProperties`, and `constant/injectorProperties`
- `system/sprayValidationDict`
- sampled validation outputs under `postProcessing/sprayValidation/`

Those case files were promoted from the local materialized authority run at
`outputs/openfoam_doe_small_real/runs/case_000000` so the validation path is no
longer sidecar-only.

The live validation adapter now reads Spray G metrics from the sampled
`postProcessing/sprayValidation/` artifacts produced by the `sprayFoam` case
deck. The legacy `openfoam_metrics.json` file remains for compatibility only and
is not the strict-authority source.
