"""Ensure canonical contracts/types are sourced from larrak-core.

This test makes refactors explicit and traceable: the legacy `larrak2.*` import
paths must remain available in the control-plane shell, but the implementation
must come from the external `larrak-core` runtime package (`larrak_runtime`).
"""

from __future__ import annotations


def test_core_types_come_from_larrak_runtime() -> None:
    from larrak2.core.types import EvalContext

    assert EvalContext.__module__.startswith("larrak_runtime.")


def test_core_encoding_comes_from_larrak_runtime() -> None:
    from larrak2.core.encoding import decode_candidate

    assert decode_candidate.__module__.startswith("larrak_runtime.")


def test_contract_tracer_comes_from_larrak_runtime() -> None:
    from larrak2.architecture.contracts import ContractTracer

    assert ContractTracer.__module__.startswith("larrak_runtime.")


def test_workflow_contract_loader_comes_from_larrak_runtime() -> None:
    from larrak2.architecture.workflow_contracts import load_simulation_dataset_bundle

    assert load_simulation_dataset_bundle.__module__.startswith("larrak_runtime.")


def test_surrogate_quality_contract_comes_from_larrak_runtime() -> None:
    from larrak2.surrogate.quality_contract import validate_artifact_quality

    assert validate_artifact_quality.__module__.startswith("larrak_runtime.")


def test_training_workflows_come_from_larrak_simulation() -> None:
    from larrak2.training.workflows import main

    assert main.__module__.startswith("larrak_simulation.")

