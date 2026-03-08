from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_runner_module():
    root = Path(__file__).resolve().parents[2]
    module_path = root / "tools" / "readiness" / "run_architecture_readiness.py"
    spec = importlib.util.spec_from_file_location("run_architecture_readiness", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_probe_fidelities_deduplicates_and_sorts() -> None:
    module = _load_runner_module()
    assert module._parse_probe_fidelities("2,0,2") == (0, 2)


def test_critical_real_key_report_skips_when_f1_not_requested() -> None:
    module = _load_runner_module()
    report = module.build_critical_real_key_report({}, {}, (0, 2))
    assert report["evaluated"] is False
    assert report["required_for_current_scope"] is False
    assert report["skipped_reason"] == "fidelity_1_not_requested"


def test_classify_failure_marks_openfoam_provenance_gap() -> None:
    module = _load_runner_module()
    assert (
        module._classify_failure(
            "OpenFOAM strict F2 provenance gate failed: synthetic_artifact_not_allowed_in_strict_f2"
        )
        == "runtime_provenance_gap"
    )
