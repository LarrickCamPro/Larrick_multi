"""Ensure analysis helpers are sourced from external `larrak-analysis`."""

from __future__ import annotations


def test_analysis_workflows_route_to_larrak_analysis() -> None:
    from larrak2.analysis.workflows import sensitivity_workflow

    assert sensitivity_workflow.__module__.startswith("larrak_analysis.")


def test_analysis_sensitivity_routes_to_larrak_analysis() -> None:
    from larrak2.analysis.sensitivity import sensitivity_scan

    assert sensitivity_scan.__module__.startswith("larrak_analysis.")

