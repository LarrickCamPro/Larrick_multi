"""Workflow CI layout tests for branch-specific wrappers."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"

WRAPPER_BRANCHES = {
    "simulation.yml": ("dev/simulation", "codex/simulation/**"),
    "training.yml": ("dev/training", "codex/training/**"),
    "optimization.yml": ("dev/optimization", "codex/optimization/**"),
    "analysis.yml": ("dev/analysis", "codex/analysis/**"),
    "cem-orchestration.yml": ("dev/cem-orchestration", "codex/cem-orchestration/**"),
}


def _load_yaml(path: Path) -> dict:
    return yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def test_reusable_fast_workflow_exists_and_is_read_only() -> None:
    workflow = _load_yaml(WORKFLOW_DIR / "reusable-fast.yml")
    assert "workflow_call" in workflow["on"]
    assert workflow["permissions"]["contents"] == "read"
    steps = workflow["jobs"]["fast"]["steps"]
    rendered = "\n".join(str(step) for step in steps)
    assert "ruff format --check ." in rendered
    assert "ruff check ." in rendered
    assert "mypy" in rendered
    assert "git push" not in rendered


def test_main_ci_uses_reusable_fast_and_no_write_permissions() -> None:
    workflow = _load_yaml(WORKFLOW_DIR / "ci.yml")
    assert workflow["permissions"]["contents"] == "read"
    assert workflow["jobs"]["fast"]["uses"] == "./.github/workflows/reusable-fast.yml"
    text = (WORKFLOW_DIR / "ci.yml").read_text(encoding="utf-8")
    assert "git push" not in text
    assert "contents: write" not in text


def test_workflow_branch_wrappers_target_expected_branches() -> None:
    for filename, expected in WRAPPER_BRANCHES.items():
        workflow = _load_yaml(WORKFLOW_DIR / filename)
        push_branches = tuple(workflow["on"]["push"]["branches"])
        assert push_branches == expected
        assert workflow["jobs"]["fast"]["uses"] == "./.github/workflows/reusable-fast.yml"


def test_workflow_branch_wrappers_define_self_hosted_stubs() -> None:
    for filename in WRAPPER_BRANCHES:
        workflow = _load_yaml(WORKFLOW_DIR / filename)
        heavy_job = workflow["jobs"]["heavy-self-hosted"]
        runs_on = list(heavy_job["runs-on"])
        assert "self-hosted" in runs_on
        assert "larrak-placeholder" in runs_on
        assert "vars.LARRAK_ENABLE_SELF_HOSTED" in str(heavy_job["if"])


def test_reusable_fast_has_pip_cache_step() -> None:
    workflow = _load_yaml(WORKFLOW_DIR / "reusable-fast.yml")
    steps = workflow["jobs"]["fast"]["steps"]
    cache_steps = [s for s in steps if str(s.get("uses", "")).startswith("actions/cache")]
    assert cache_steps, "reusable-fast.yml must have an actions/cache step for pip"
    cache_step = cache_steps[0]
    assert "pip" in str(cache_step.get("with", {}).get("path", ""))
    key = str(cache_step.get("with", {}).get("key", ""))
    assert "pyproject.toml" in key or "hashFiles" in key


def test_ci_telemetry_workflow_exists_and_has_correct_trigger() -> None:
    telemetry_path = WORKFLOW_DIR / "ci-telemetry.yml"
    assert telemetry_path.exists(), "ci-telemetry.yml must exist"
    workflow = _load_yaml(telemetry_path)
    assert "workflow_run" in workflow["on"], "ci-telemetry must be triggered by workflow_run"
    assert workflow["permissions"].get("actions") == "read"
