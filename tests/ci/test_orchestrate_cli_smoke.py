"""CLI smoke test for orchestrate run type."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from larrak2.cli.run import main as run_main


def test_orchestrate_cli_smoke(tmp_path: Path) -> None:
    outdir = tmp_path / "orchestrate_smoke"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "larrak2.cli.run",
            "orchestrate",
            "--outdir",
            str(outdir),
            "--rpm",
            "2200",
            "--torque",
            "120",
            "--seed",
            "123",
            "--sim-budget",
            "4",
            "--batch-size",
            "4",
            "--max-iterations",
            "2",
            "--truth-dispatch-mode",
            "off",
            "--allow-heuristic-surrogate-fallback",
            "--surrogate-validation-mode",
            "off",
            "--thermo-symbolic-mode",
            "off",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr

    manifest_path = outdir / "orchestrate_manifest.json"
    provenance_path = outdir / "provenance_events.jsonl"
    assert manifest_path.exists()
    assert provenance_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["workflow"] == "orchestrate"
    assert manifest["result"]["n_iterations"] >= 1
    assert manifest["files"]["orchestrate_manifest"] == str(manifest_path)


def test_orchestrate_cli_defaults(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def _mock_workflow(args):
        captured["thermo_symbolic_mode"] = str(args.thermo_symbolic_mode)
        return 0

    monkeypatch.setattr("larrak2.cli.run.run_orchestrate_workflow", _mock_workflow)
    with patch.object(sys, "argv", ["run.py", "orchestrate"]):
        code = run_main()
    assert code == 0
    assert captured["thermo_symbolic_mode"] == "strict"
