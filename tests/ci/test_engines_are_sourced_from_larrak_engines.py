"""Ensure engine implementations are sourced from the external `larrak-engines` package."""

from __future__ import annotations


def test_core_evaluator_routes_to_larrak_engines() -> None:
    from larrak2.core.evaluator import evaluate_candidate

    assert evaluate_candidate.__module__.startswith("larrak_engines.")


def test_cem_routes_to_larrak_engines() -> None:
    from larrak2.cem.tribology import compute_lambda

    assert compute_lambda.__module__.startswith("larrak_engines.")


def test_realworld_routes_to_larrak_engines() -> None:
    from larrak2.realworld.constraints import compute_realworld_constraints

    assert compute_realworld_constraints.__module__.startswith("larrak_engines.")


def test_thermo_symbolic_artifact_routes_to_larrak_engines() -> None:
    from larrak2.thermo.symbolic_artifact import ThermoSymbolicArtifact

    assert ThermoSymbolicArtifact.__module__.startswith("larrak_engines.")

