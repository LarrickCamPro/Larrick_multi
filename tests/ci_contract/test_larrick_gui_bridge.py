"""Contract tests for the Larrick GUI Python bridge."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run_bridge(tmp_path: Path, mode: str, payload: dict[str, object]) -> dict[str, object]:
    bridge_script = Path(__file__).resolve().parents[2] / "scripts" / "larrick_gui_bridge.py"
    input_path = tmp_path / f"{mode}_input.json"
    output_path = tmp_path / f"{mode}_output.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")

    cmd = [
        sys.executable,
        str(bridge_script),
        "--mode",
        mode,
        "--input",
        str(input_path),
        "--output",
        str(output_path),
        "--output-dir",
        str(tmp_path),
    ]
    subprocess.run(cmd, check=True)
    return json.loads(output_path.read_text(encoding="utf-8"))


def _run_bridge_real(tmp_path: Path, mode: str, payload: dict[str, object]) -> dict[str, object]:
    bridge_script = Path(__file__).resolve().parents[2] / "scripts" / "larrick_gui_bridge.py"
    input_path = tmp_path / f"{mode}_input.json"
    output_path = tmp_path / f"{mode}_output.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")

    cmd = [
        sys.executable,
        str(bridge_script),
        "--mode",
        mode,
        "--real",
        "--input",
        str(input_path),
        "--output",
        str(output_path),
        "--output-dir",
        str(tmp_path),
    ]
    # Real mode is allowed to return unavailable but should not crash the bridge.
    subprocess.run(cmd, check=True)
    return json.loads(output_path.read_text(encoding="utf-8"))


def test_optimize_mode_emits_legacy_compatible_payload(tmp_path: Path) -> None:
    output = _run_bridge(
        tmp_path=tmp_path,
        mode="optimize",
        payload={"rpm": 2800.0, "gearRatio": 2.2, "strokeLengthMm": 110.0},
    )
    assert output["status"] == "success"
    assert output["mode"] == "optimize"
    assert "motion_law" in output
    assert "optimal_profiles" in output
    assert "payload" in output


def test_orchestrate_stub_mode_emits_uniform_contract(tmp_path: Path) -> None:
    output = _run_bridge(
        tmp_path=tmp_path,
        mode="orchestrate",
        payload={"rpm": 3000.0, "sim_budget": 2, "max_iterations": 1},
    )
    assert output["status"] == "success"
    assert output["mode"] == "orchestrate"
    assert output["backend"] == "larrick-stub"
    assert "payload" in output
    assert "diagnostics" in output


def test_orchestrate_real_mode_gracefully_reports_unavailable_when_deps_missing(
    tmp_path: Path,
) -> None:
    output = _run_bridge_real(
        tmp_path=tmp_path,
        mode="orchestrate",
        payload={"rpm": 3000.0, "sim_budget": 1, "max_iterations": 1, "truth_dispatch_mode": "off"},
    )
    assert output["mode"] == "orchestrate"
    assert output["backend"] == "larrick-real"
    assert output["status"] in {"success", "failed", "unavailable"}
    assert "payload" in output


def test_bridge_exits_zero_and_writes_failed_json_on_invalid_input(tmp_path: Path) -> None:
    """Contract: exit code stays 0 so GUI can always prefer parsing output JSON."""
    bridge_script = Path(__file__).resolve().parents[2] / "scripts" / "larrick_gui_bridge.py"
    input_path = tmp_path / "bad_input.json"
    output_path = tmp_path / "bad_output.json"
    input_path.write_text("{ not valid json", encoding="utf-8")

    cmd = [
        sys.executable,
        str(bridge_script),
        "--mode",
        "optimize",
        "--input",
        str(input_path),
        "--output",
        str(output_path),
        "--output-dir",
        str(tmp_path),
    ]
    proc = subprocess.run(cmd, check=False)
    assert proc.returncode == 0
    body = json.loads(output_path.read_text(encoding="utf-8"))
    assert body["status"] == "failed"
    assert body.get("error")
