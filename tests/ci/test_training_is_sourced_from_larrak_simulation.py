"""Ensure training workflows are sourced from the external `larrak-simulation` package."""

from __future__ import annotations


def test_training_workflows_module_routes_to_larrak_simulation() -> None:
    from larrak2.training.workflows import train_stack_surrogate_workflow

    assert train_stack_surrogate_workflow.__module__.startswith("larrak_simulation.")

