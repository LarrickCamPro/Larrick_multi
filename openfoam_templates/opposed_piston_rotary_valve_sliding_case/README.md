# OpenFOAM Sliding-Case Template

This is the tracked default template directory for the chemistry-capable
`openfoam-doe` and real-authority OpenFOAM training path.

The runtime DOE path substitutes `{{...}}` placeholders in this case tree,
injects geometry under `constant/triSurface/`, stages the tracked Chem323
package into `constant/`, and seeds the case from a reduced-state handoff
bundle before building and running the repo-owned `larrakEngineFoam`.

Expected generated STL names:
- `cylinder.stl`
- `intakeValve.stl`
- `exhaustValveLeft.stl`
- `exhaustValveRight.stl`
- `intakeManifold.stl`
- `exhaustManifoldLeft.stl`
- `exhaustManifoldRight.stl`
- `intakeValveInterface.stl`
- `exhaustValveLeftInterface.stl`
- `exhaustValveRightInterface.stl`
