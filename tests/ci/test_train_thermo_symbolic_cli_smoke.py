"""CLI smoke test for train-thermo-symbolic workflow."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np


def test_train_thermo_symbolic_cli_smoke(tmp_path: Path) -> None:
    n = 20
    x_cols = 12
    y_cols = 5
    X = np.random.default_rng(21).normal(size=(n, x_cols)).astype(np.float64)
    Y = np.random.default_rng(22).normal(size=(n, y_cols)).astype(np.float64)
    dataset_path = tmp_path / "thermo_symbolic_train.npz"
    np.savez(
        dataset_path,
        X=X,
        Y=Y,
        feature_names=np.array([f"x_{i:03d}" for i in range(10)] + ["rpm", "torque"], dtype=object),
        objective_names=np.array(
            ["eta_comb_gap", "eta_exp_gap", "motion_law_penalty"], dtype=object
        ),
        constraint_names=np.array(["thermo_power_balance", "thermo_pressure_limit"], dtype=object),
    )

    outdir = tmp_path / "train_out"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "larrak2.cli.run",
            "train-thermo-symbolic",
            "--dataset",
            str(dataset_path),
            "--outdir",
            str(outdir),
            "--name",
            "thermo_symbolic_f1.npz",
            "--fidelity",
            "1",
            "--rpm",
            "2600",
            "--torque",
            "130",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr

    artifact_path = outdir / "thermo_symbolic_f1.npz"
    report_path = outdir / "quality_report.json"
    summary_path = outdir / "thermo_symbolic_training_summary.json"
    manifest_path = outdir / "train_thermo_symbolic_manifest.json"

    assert artifact_path.exists()
    assert report_path.exists()
    assert summary_path.exists()
    assert manifest_path.exists()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert report["surrogate_kind"] == "thermo_symbolic"
    assert report["quality_profile"]["normalization_method"] == "p95_p05_range"
    assert report["metrics"]["val"]["per_target"]
    assert manifest["workflow"] == "train_thermo_symbolic"
    assert manifest["ok"] is True
