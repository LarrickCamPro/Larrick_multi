"""Integration test — reacting-flow runner against fixture TNF-style data."""

from __future__ import annotations

from larrak2.simulation_validation.models import (
    ComparisonMode,
    RegimeStatus,
    SourceType,
    ValidationCaseSpec,
    ValidationDatasetManifest,
    ValidationMetricSpec,
)
from larrak2.simulation_validation.runners.reacting_flow import ReactingFlowRunner


def _tnf_dataset() -> ValidationDatasetManifest:
    return ValidationDatasetManifest(
        dataset_id="tnf_piloted_flame_d",
        regime="reacting_flow",
        fuel_family="gasoline",
        source_type=SourceType.MEASURED,
        provenance={"source": "TNF Workshop", "case": "Flame D"},
        metrics=[
            ValidationMetricSpec(
                metric_id="temperature_x5d",
                units="K",
                comparison_mode=ComparisonMode.ABSOLUTE,
                tolerance_band=50.0,
                source_type=SourceType.MEASURED,
            ),
            ValidationMetricSpec(
                metric_id="species_OH_x5d",
                units="mol_frac",
                comparison_mode=ComparisonMode.RELATIVE,
                tolerance_band=0.15,
                source_type=SourceType.MEASURED,
            ),
            ValidationMetricSpec(
                metric_id="velocity_axial_x5d",
                units="m/s",
                comparison_mode=ComparisonMode.ABSOLUTE,
                tolerance_band=3.0,
                source_type=SourceType.MEASURED,
            ),
            ValidationMetricSpec(
                metric_id="scalar_dissipation_x5d",
                units="1/s",
                comparison_mode=ComparisonMode.RELATIVE,
                tolerance_band=0.25,
                source_type=SourceType.MEASURED,
                required=False,
            ),
        ],
    )


class TestReactingFlowRunnerIntegration:
    def test_passing_case(self):
        runner = ReactingFlowRunner()
        ds = _tnf_dataset()
        case = ValidationCaseSpec(case_id="rf_pass", regime="reacting_flow")
        sim = {
            "temperature_x5d": 1850.0,
            "temperature_x5d_measured": 1820.0,
            "species_OH_x5d": 0.0032,
            "species_OH_x5d_measured": 0.0030,
            "velocity_axial_x5d": 28.0,
            "velocity_axial_x5d_measured": 27.0,
            "scalar_dissipation_x5d": 45.0,
            "scalar_dissipation_x5d_measured": 40.0,
        }
        run = runner.run(ds, case, sim)
        assert run.status == RegimeStatus.PASSED

    def test_temperature_failure(self):
        runner = ReactingFlowRunner()
        ds = _tnf_dataset()
        case = ValidationCaseSpec(case_id="rf_fail", regime="reacting_flow")
        sim = {
            "temperature_x5d": 1500.0,  # way off
            "temperature_x5d_measured": 1820.0,
            "species_OH_x5d": 0.0030,
            "species_OH_x5d_measured": 0.0030,
            "velocity_axial_x5d": 27.0,
            "velocity_axial_x5d_measured": 27.0,
        }
        run = runner.run(ds, case, sim)
        assert run.status == RegimeStatus.FAILED

    def test_acceptance_outputs(self):
        runner = ReactingFlowRunner()
        ds = _tnf_dataset()
        case = ValidationCaseSpec(case_id="rf_out", regime="reacting_flow")
        sim = {
            "temperature_x5d": 1820.0,
            "temperature_x5d_measured": 1820.0,
            "species_OH_x5d": 0.0030,
            "species_OH_x5d_measured": 0.0030,
            "velocity_axial_x5d": 27.0,
            "velocity_axial_x5d_measured": 27.0,
            "reacting_flow_provenance": {"source": "TNF"},
        }
        run = runner.run(ds, case, sim)
        outputs = runner.build_acceptance_outputs(run)
        assert "temperature_comparisons" in outputs
        assert "species_comparisons" in outputs
        assert "velocity_comparisons" in outputs
