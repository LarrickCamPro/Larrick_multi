"""Tests for workflow ownership and branch validation."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_module():
    module_path = REPO_ROOT / "scripts" / "check_branch_ownership.py"
    spec = importlib.util.spec_from_file_location("check_branch_ownership", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_manifest_contains_expected_workflows() -> None:
    module = _load_module()
    config = module.load_config(REPO_ROOT / "workflow_ownership.yml")
    rules = module.load_workflow_rules(config)

    assert set(rules) == {
        "analysis",
        "cem-orchestration",
        "optimization",
        "simulation",
        "training",
    }
    assert "src/larrak2/architecture/**" in config["main_only_paths"]


def test_codex_workflow_branch_requires_matching_dev_base() -> None:
    module = _load_module()
    config = module.load_config(REPO_ROOT / "workflow_ownership.yml")
    policy = module.classify_branch("codex/simulation/fix-doe-paths", config)

    assert module.validate_base(policy, "dev/simulation") == []
    findings = module.validate_base(policy, "dev/training")
    assert [finding.message for finding in findings] == [
        "Branch 'codex/simulation/fix-doe-paths' must target 'dev/simulation', not 'dev/training'.",
    ]
    assert findings[0].code == "ownership"


def test_codex_workflow_branch_blocks_shared_contract_and_foreign_paths() -> None:
    module = _load_module()
    config = module.load_config(REPO_ROOT / "workflow_ownership.yml")
    policy = module.classify_branch("codex/simulation/fix-doe-paths", config)

    violations = module.validate_changed_paths(
        policy,
        [
            "src/larrak2/architecture/workflow_contracts.py",
            "src/larrak2/training/basic.py",
        ],
        config,
    )

    messages = [violation.message for violation in violations]
    assert any("reserved for codex/main tasks" in message for message in messages)
    assert any("outside the branch ownership manifest" in message for message in messages)
    assert (
        module.validate_changed_paths(
            policy,
            ["src/larrak2/simulation_validation/source_rules.py"],
            config,
        )
        == []
    )


def test_codex_main_branch_owns_shared_contract_and_governance() -> None:
    module = _load_module()
    config = module.load_config(REPO_ROOT / "workflow_ownership.yml")
    policy = module.classify_branch("codex/main/parallel-branch-hardening", config)

    assert (
        module.validate_changed_paths(
            policy,
            [
                "src/larrak2/architecture/workflow_contracts.py",
                ".github/workflows/ci.yml",
                "workflow_ownership.yml",
            ],
            config,
        )
        == []
    )
    violations = module.validate_changed_paths(policy, ["src/larrak2/training/basic.py"], config)
    assert any(
        "outside the branch ownership manifest" in violation.message for violation in violations
    )


def test_cem_branch_excludes_simulation_inputs() -> None:
    module = _load_module()
    config = module.load_config(REPO_ROOT / "workflow_ownership.yml")
    policy = module.classify_branch("codex/cem-orchestration/realworld-fix", config)

    violations = module.validate_changed_paths(
        policy,
        ["src/larrak2/orchestration/simulation_inputs.py"],
        config,
    )

    assert any(
        "excluded from the 'cem-orchestration' workflow" in violation.message
        for violation in violations
    )


def test_dev_branch_promotes_only_to_main() -> None:
    module = _load_module()
    config = module.load_config(REPO_ROOT / "workflow_ownership.yml")
    policy = module.classify_branch("dev/training", config)

    assert module.validate_base(policy, "main") == []
    findings = module.validate_base(policy, "dev/training")
    assert [finding.message for finding in findings] == [
        "Branch 'dev/training' must target 'main', not 'dev/training'.",
    ]


def test_json_report_surfaces_structured_policy_findings(tmp_path: Path) -> None:
    module = _load_module()
    changed_file = tmp_path / "changed.txt"
    changed_file.write_text("src/larrak2/training/basic.py\n", encoding="utf-8")

    result = module.subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "check_branch_ownership.py"),
            "--branch",
            "codex/simulation/fix-doe-paths",
            "--base",
            "dev/training",
            "--changed-file",
            str(changed_file),
            "--root",
            str(REPO_ROOT),
            "--json",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 1
    payload = module.json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["policy"]["expected_base"] == "dev/simulation"
    assert payload["findings"][0]["code"] == "ownership"
    assert any(item.get("path") == "src/larrak2/training/basic.py" for item in payload["findings"])
