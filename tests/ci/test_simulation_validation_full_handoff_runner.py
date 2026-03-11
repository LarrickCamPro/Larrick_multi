"""Integration test — full-handoff runner with mocked OpenFOAM/Cantera outputs."""

from __future__ import annotations

from larrak2.simulation_validation.models import (
    ComparisonMode,
    RegimeStatus,
    SourceType,
    ValidationCaseSpec,
    ValidationDatasetManifest,
    ValidationMetricSpec,
)
from larrak2.simulation_validation.runners.full_handoff import FullHandoffRunner


def _handoff_dataset() -> ValidationDatasetManifest:
    return ValidationDatasetManifest(
        dataset_id="engine_handoff_v1",
        regime="full_handoff",
        fuel_family="gasoline",
        source_type=SourceType.DERIVED_CONSTRAINT,
        governing_basis="Conservation laws across phase transitions",
        metrics=[
            ValidationMetricSpec(
                metric_id="state_conservation_mass",
                units="kg",
                comparison_mode=ComparisonMode.ABSOLUTE,
                tolerance_band=1e-6,
                source_type=SourceType.DERIVED_CONSTRAINT,
            ),
            ValidationMetricSpec(
                metric_id="state_conservation_energy",
                units="J",
                comparison_mode=ComparisonMode.ABSOLUTE,
                tolerance_band=1e-3,
                source_type=SourceType.DERIVED_CONSTRAINT,
            ),
        ],
    )


class TestFullHandoffRunnerIntegration:
    def test_passing_handoff(self):
        runner = FullHandoffRunner()
        ds = _handoff_dataset()
        case = ValidationCaseSpec(case_id="fh_pass", regime="full_handoff")
        sim = {
            "state_conservation_mass": 1e-8,
            "state_conservation_mass_measured": 0.0,
            "state_conservation_energy": 5e-5,
            "state_conservation_energy_measured": 0.0,
            "handoff_states": [
                {
                    "from_phase": "scavenging",
                    "to_phase": "compression",
                    "conservation_error": 1e-9,
                    "conservation_tolerance": 1e-6,
                },
                {
                    "from_phase": "compression",
                    "to_phase": "combustion",
                    "conservation_error": 5e-8,
                    "conservation_tolerance": 1e-6,
                },
            ],
        }
        run = runner.run(ds, case, sim)
        assert run.status == RegimeStatus.PASSED

    def test_conservation_violation_fails(self):
        runner = FullHandoffRunner()
        ds = _handoff_dataset()
        case = ValidationCaseSpec(case_id="fh_fail", regime="full_handoff")
        sim = {
            "state_conservation_mass": 1e-8,
            "state_conservation_mass_measured": 0.0,
            "state_conservation_energy": 5e-5,
            "state_conservation_energy_measured": 0.0,
            "handoff_states": [
                {
                    "from_phase": "scavenging",
                    "to_phase": "compression",
                    "conservation_error": 0.01,  # exceeds tolerance
                    "conservation_tolerance": 1e-6,
                },
            ],
        }
        run = runner.run(ds, case, sim)
        assert run.status == RegimeStatus.FAILED
        failed = [r for r in run.metric_results if not r.passed]
        assert any("handoff_conservation" in f.metric_id for f in failed)

    def test_acceptance_outputs(self):
        runner = FullHandoffRunner()
        ds = _handoff_dataset()
        case = ValidationCaseSpec(case_id="fh_out", regime="full_handoff")
        sim = {
            "state_conservation_mass": 0.0,
            "state_conservation_mass_measured": 0.0,
            "state_conservation_energy": 0.0,
            "state_conservation_energy_measured": 0.0,
            "handoff_states": [],
            "full_handoff_provenance": {"solver": "OpenFOAM+Cantera"},
        }
        run = runner.run(ds, case, sim)
        outputs = runner.build_acceptance_outputs(run)
        assert "state_conservation_checks" in outputs
        assert "transition_residual_reports" in outputs
        assert "end_to_end_comparisons" in outputs
