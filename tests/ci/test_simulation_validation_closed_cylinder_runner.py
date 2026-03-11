"""Integration test — closed-cylinder runner against fixture pressure-trace datasets."""

from __future__ import annotations

from larrak2.simulation_validation.models import (
    ComparisonMode,
    RegimeStatus,
    SourceType,
    ValidationCaseSpec,
    ValidationDatasetManifest,
    ValidationMetricSpec,
)
from larrak2.simulation_validation.runners.closed_cylinder import ClosedCylinderRunner


def _pressure_trace_dataset() -> ValidationDatasetManifest:
    return ValidationDatasetManifest(
        dataset_id="engine_pressure_trace_v1",
        regime="closed_cylinder",
        fuel_family="gasoline",
        source_type=SourceType.MEASURED,
        provenance={"source": "engine_dyno", "data_type": "four_stroke"},
        metrics=[
            ValidationMetricSpec(
                metric_id="peak_pressure_bar",
                units="bar",
                comparison_mode=ComparisonMode.ABSOLUTE,
                tolerance_band=3.0,
                source_type=SourceType.MEASURED,
            ),
            ValidationMetricSpec(
                metric_id="ca50_deg",
                units="deg",
                comparison_mode=ComparisonMode.ABSOLUTE,
                tolerance_band=2.0,
                source_type=SourceType.MEASURED,
            ),
            ValidationMetricSpec(
                metric_id="ca10_deg",
                units="deg",
                comparison_mode=ComparisonMode.ABSOLUTE,
                tolerance_band=3.0,
                source_type=SourceType.MEASURED,
            ),
            ValidationMetricSpec(
                metric_id="ca90_deg",
                units="deg",
                comparison_mode=ComparisonMode.ABSOLUTE,
                tolerance_band=5.0,
                source_type=SourceType.MEASURED,
            ),
            ValidationMetricSpec(
                metric_id="apparent_heat_release_kJ",
                units="kJ",
                comparison_mode=ComparisonMode.RELATIVE,
                tolerance_band=0.10,
                source_type=SourceType.MEASURED,
            ),
            ValidationMetricSpec(
                metric_id="work_imep_bar",
                units="bar",
                comparison_mode=ComparisonMode.ABSOLUTE,
                tolerance_band=0.5,
                source_type=SourceType.MEASURED,
            ),
        ],
    )


class TestClosedCylinderRunnerIntegration:
    def test_all_pass(self):
        runner = ClosedCylinderRunner()
        ds = _pressure_trace_dataset()
        case = ValidationCaseSpec(case_id="cc_pass", regime="closed_cylinder")
        sim = {
            "peak_pressure_bar": 78.0,
            "peak_pressure_bar_measured": 80.0,
            "ca50_deg": 9.5,
            "ca50_deg_measured": 10.0,
            "ca10_deg": -2.0,
            "ca10_deg_measured": -1.0,
            "ca90_deg": 28.0,
            "ca90_deg_measured": 30.0,
            "apparent_heat_release_kJ": 0.82,
            "apparent_heat_release_kJ_measured": 0.80,
            "work_imep_bar": 10.2,
            "work_imep_bar_measured": 10.0,
        }
        run = runner.run(ds, case, sim)
        assert run.status == RegimeStatus.PASSED
        assert len(run.metric_results) == 6

    def test_peak_pressure_failure(self):
        runner = ClosedCylinderRunner()
        ds = _pressure_trace_dataset()
        case = ValidationCaseSpec(case_id="cc_fail", regime="closed_cylinder")
        sim = {
            "peak_pressure_bar": 90.0,
            "peak_pressure_bar_measured": 80.0,
            "ca50_deg": 10.0,
            "ca50_deg_measured": 10.0,
            "ca10_deg": -1.0,
            "ca10_deg_measured": -1.0,
            "ca90_deg": 30.0,
            "ca90_deg_measured": 30.0,
            "apparent_heat_release_kJ": 0.80,
            "apparent_heat_release_kJ_measured": 0.80,
            "work_imep_bar": 10.0,
            "work_imep_bar_measured": 10.0,
        }
        run = runner.run(ds, case, sim)
        assert run.status == RegimeStatus.FAILED
        failed = [r for r in run.metric_results if not r.passed]
        assert any("peak_pressure" in f.metric_id for f in failed)

    def test_acceptance_outputs(self):
        runner = ClosedCylinderRunner()
        ds = _pressure_trace_dataset()
        case = ValidationCaseSpec(case_id="cc_out", regime="closed_cylinder")
        sim = {
            "peak_pressure_bar": 80.0,
            "peak_pressure_bar_measured": 80.0,
            "ca50_deg": 10.0,
            "ca50_deg_measured": 10.0,
            "ca10_deg": -1.0,
            "ca10_deg_measured": -1.0,
            "ca90_deg": 30.0,
            "ca90_deg_measured": 30.0,
            "apparent_heat_release_kJ": 0.80,
            "apparent_heat_release_kJ_measured": 0.80,
            "work_imep_bar": 10.0,
            "work_imep_bar_measured": 10.0,
            "closed_cylinder_provenance": {"source": "engine_dyno"},
        }
        run = runner.run(ds, case, sim)
        outputs = runner.build_acceptance_outputs(run)
        assert "pressure_trace_comparisons" in outputs
        assert "burn_metrics" in outputs
        assert "heat_release_comparisons" in outputs
        assert "work_comparisons" in outputs
