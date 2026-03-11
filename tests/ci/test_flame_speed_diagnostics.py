"""Coverage for LLNL flame-speed diagnostic classification."""

from __future__ import annotations

from larrak2.simulation_validation.flame_speed_diagnostics import (
    FlameDiagnosticResult,
    classify_diagnostic_results,
    default_case_set,
)


def test_default_quick_case_set_contains_load_and_flame_cases() -> None:
    cases = default_case_set("quick")
    assert [case.case_id for case in cases] == [
        "load_transport_none",
        "free_flame_staged_mixture_averaged",
    ]


def test_default_benchmark_case_set_is_more_aggressive_for_reduced_mechanisms() -> None:
    cases = default_case_set("benchmark")
    assert [case.case_id for case in cases] == [
        "load_transport_none",
        "free_flame_benchmark_mixture_averaged",
    ]
    assert cases[1].timeout_s == 300
    assert cases[1].grid_points == 5
    assert cases[1].refine_ratio == 50.0
    assert cases[1].refine_grid is False


def test_classify_results_marks_reduced_mechanism_when_flame_never_completes() -> None:
    results = [
        FlameDiagnosticResult(
            case_id="load_transport_none",
            mode="load_only",
            transport_model=None,
            timeout_s=900,
            success=True,
            timed_out=False,
            load_time_s=390.0,
            total_time_s=390.0,
            n_species=1387,
            n_reactions=9599,
        ),
        FlameDiagnosticResult(
            case_id="free_flame_staged_mixture_averaged",
            mode="free_flame",
            transport_model="mixture-averaged",
            timeout_s=900,
            success=False,
            timed_out=True,
            total_time_s=900.0,
            error_type="TimeoutExpired",
            error_message="Case exceeded 900s timeout",
        ),
    ]

    classification, summary = classify_diagnostic_results(results)
    assert classification == "reduced_mechanism_recommended"
    assert "no flame-speed solve completed" in summary


def test_classify_results_marks_tractable_when_flame_completes_quickly() -> None:
    results = [
        FlameDiagnosticResult(
            case_id="free_flame_staged_mixture_averaged",
            mode="free_flame",
            transport_model="mixture-averaged",
            timeout_s=900,
            success=True,
            timed_out=False,
            load_time_s=40.0,
            solve_time_s=120.0,
            total_time_s=160.0,
            flame_speed_m_s=0.41,
        )
    ]

    classification, summary = classify_diagnostic_results(results)
    assert classification == "tractable"
    assert "completed within the tractable threshold" in summary


def test_classify_results_marks_load_only_success_when_no_flame_case_is_run() -> None:
    results = [
        FlameDiagnosticResult(
            case_id="load_mixture_averaged",
            mode="load_only",
            transport_model="mixture-averaged",
            timeout_s=900,
            success=True,
            timed_out=False,
            load_time_s=378.0,
            total_time_s=378.0,
            n_species=1387,
            n_reactions=9599,
        )
    ]

    classification, summary = classify_diagnostic_results(results)
    assert classification == "load_only_success"
    assert "loads successfully" in summary


def test_classify_results_marks_transport_data_missing_when_flame_transport_fails() -> None:
    results = [
        FlameDiagnosticResult(
            case_id="load_transport_none",
            mode="load_only",
            transport_model=None,
            timeout_s=900,
            success=True,
            timed_out=False,
            load_time_s=39.0,
            total_time_s=39.0,
            n_species=100,
            n_reactions=553,
        ),
        FlameDiagnosticResult(
            case_id="free_flame_staged_mixture_averaged",
            mode="free_flame",
            transport_model="mixture-averaged",
            timeout_s=900,
            success=False,
            timed_out=False,
            total_time_s=38.0,
            error_type="CanteraError",
            error_message="Missing gas-phase transport data for species 'c12h26'.",
        ),
    ]

    classification, summary = classify_diagnostic_results(results)
    assert classification == "transport_data_missing"
    assert "transport model is unavailable" in summary
