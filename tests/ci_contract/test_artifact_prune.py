"""Tests for ``scripts/artifact_prune.py``."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "artifact_prune",
    _REPO / "scripts" / "artifact_prune.py",
)
assert _SPEC and _SPEC.loader
mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mod)


def test_prune_staged_failures_dry_run_leaves_tree(tmp_path: Path) -> None:
    auth = tmp_path / "outputs" / "openfoam_authority" / "bundle_a"
    auth.mkdir(parents=True)
    manifest = {
        "status": "staged",
        "promotable": False,
    }
    (auth / "promotion_manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    code = mod.cmd_prune_staged_failures(tmp_path, apply=False, confirm_delete=False)
    assert code == 0
    assert auth.is_dir()


def test_prune_staged_failures_apply_requires_confirm(tmp_path: Path) -> None:
    auth = tmp_path / "outputs" / "openfoam_authority" / "bundle_b"
    auth.mkdir(parents=True)
    (auth / "promotion_manifest.json").write_text(
        json.dumps({"status": "staged", "promotable": False}),
        encoding="utf-8",
    )

    code = mod.cmd_prune_staged_failures(tmp_path, apply=True, confirm_delete=False)
    assert code == 2
    assert auth.is_dir()


def test_prune_staged_failures_apply_removes_only_non_promotable_staged(
    tmp_path: Path,
) -> None:
    root = tmp_path / "outputs" / "openfoam_authority"
    bad = root / "bad"
    good_staged = root / "good_staged"
    promoted = root / "promoted"
    bad.mkdir(parents=True)
    good_staged.mkdir(parents=True)
    promoted.mkdir(parents=True)
    (bad / "promotion_manifest.json").write_text(
        json.dumps({"status": "staged", "promotable": False}),
        encoding="utf-8",
    )
    (good_staged / "promotion_manifest.json").write_text(
        json.dumps({"status": "staged", "promotable": True}),
        encoding="utf-8",
    )
    (promoted / "promotion_manifest.json").write_text(
        json.dumps({"status": "promoted", "promotable": False}),
        encoding="utf-8",
    )

    code = mod.cmd_prune_staged_failures(tmp_path, apply=True, confirm_delete=True)
    assert code == 0
    assert not bad.exists()
    assert good_staged.is_dir()
    assert promoted.is_dir()


def test_cli_invocation_list(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(_REPO / "scripts" / "artifact_prune.py"),
            "--root",
            str(tmp_path),
            "list",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
