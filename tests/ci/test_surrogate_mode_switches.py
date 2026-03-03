"""CI coverage for explicit surrogate mode switches (no implicit fallback)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from larrak2.core.encoding import decode_candidate, mid_bounds_candidate
from larrak2.core.evaluator import evaluate_candidate
from larrak2.core.types import EvalContext
from larrak2.thermo import two_zone


def _write_relaxed_anchor_manifest(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "version": "test-relaxed",
                "validated_envelope": {
                    "rpm_min": 0.0,
                    "rpm_max": 1e9,
                    "torque_min": 0.0,
                    "torque_max": 1e9,
                },
                "thresholds": {
                    "delta_m_air_rel_max": 1e6,
                    "delta_residual_abs_max": 1e6,
                    "delta_scavenging_abs_max": 1e6,
                },
                "anchors": [{"rpm": 3000.0, "torque": 200.0, "label": "test_anchor"}],
            }
        ),
        encoding="utf-8",
    )
    return path


def _install_realworld_stub(monkeypatch) -> None:
    from larrak2.realworld.surrogates import PhaseResolvedResult, RealWorldSurrogateResult

    def _fake_phase(*_args, **_kwargs):
        return PhaseResolvedResult(
            lambda_min=1.5,
            scuff_margin_flash_C=25.0,
            scuff_margin_integral_C=24.0,
            scuff_margin_C=24.0,
            micropitting_safety=1.2,
            lube_regime="FULL_FILM",
            tribology_method_used="flash",
            tribology_data_status="ok",
            material_temp_margin_C=30.0,
            total_cost_index=1.0,
            feature_importance=[("tribology_stub", 1.0)],
            worst_phase_deg=0.0,
            n_bins_analyzed=1,
            force_threshold_N=1.0,
            lambda_profile=np.ones(360, dtype=np.float64),
        )

    def _fake_scalar(*_args, **_kwargs):
        return RealWorldSurrogateResult(
            lambda_min=1.5,
            scuff_margin_flash_C=25.0,
            scuff_margin_integral_C=24.0,
            scuff_margin_C=24.0,
            micropitting_safety=1.2,
            lube_regime="FULL_FILM",
            tribology_method_used="flash",
            tribology_data_status="ok",
            material_temp_margin_C=30.0,
            total_cost_index=1.0,
            feature_importance=[("tribology_stub", 1.0)],
            min_snap_distance=0.0,
        )

    monkeypatch.setattr("larrak2.realworld.surrogates.evaluate_realworld_phase_resolved", _fake_phase)
    monkeypatch.setattr("larrak2.realworld.surrogates.evaluate_realworld_surrogates", _fake_scalar)


def test_calculix_nn_mode_requires_model(monkeypatch):
    monkeypatch.setenv("LARRAK2_CALCULIX_NN_PATH", "/tmp/does_not_exist_calculix.pt")

    x = mid_bounds_candidate()
    ctx = EvalContext(rpm=3000.0, torque=200.0, fidelity=0, seed=1, calculix_stress_mode="nn")

    with pytest.raises(FileNotFoundError):
        evaluate_candidate(x, ctx)


def test_calculix_analytical_mode_is_explicit_bypass(monkeypatch):
    monkeypatch.setenv("LARRAK2_CALCULIX_NN_PATH", "/tmp/does_not_exist_calculix.pt")
    _install_realworld_stub(monkeypatch)

    x = mid_bounds_candidate()
    ctx = EvalContext(
        rpm=3000.0,
        torque=200.0,
        fidelity=0,
        seed=1,
        calculix_stress_mode="analytical",
        strict_data=False,
        strict_tribology_data=False,
    )

    res = evaluate_candidate(x, ctx)
    assert np.all(np.isfinite(res.F))
    assert np.all(np.isfinite(res.G))
    assert res.diag["gear"]["radius_strategy"]["calculix_stress_mode"] == "analytical"
    assert res.diag["gear"]["radius_strategy"]["stress_source"] == "analytical_proxy"


def test_gear_loss_nn_mode_requires_model_dir(monkeypatch, tmp_path: Path):
    x = mid_bounds_candidate()
    _install_realworld_stub(monkeypatch)
    anchor_manifest = _write_relaxed_anchor_manifest(tmp_path / "anchors_relaxed.json")
    candidate = decode_candidate(x)
    base = two_zone.evaluate_two_zone_thermo(
        candidate.thermo,
        EvalContext(rpm=3000.0, torque=200.0, fidelity=1, seed=1),
    )
    pred = {
        "m_air_trapped": float(base.diag["m_air_trapped"]),
        "residual_fraction": float(base.diag["residual_fraction"]),
        "scavenging_efficiency": float(base.diag["scavenging_efficiency"]),
    }

    def _fake_predict(**_: object) -> dict[str, float]:
        return pred

    monkeypatch.setattr(two_zone, "_predict_openfoam_breathing", _fake_predict)

    ctx = EvalContext(
        rpm=3000.0,
        torque=200.0,
        fidelity=2,
        seed=1,
        gear_loss_mode="nn",
        gear_loss_model_dir="/tmp/does_not_exist_gear_loss_dir",
        thermo_anchor_manifest_path=str(anchor_manifest),
        strict_tribology_data=False,
    )

    with pytest.raises(FileNotFoundError):
        evaluate_candidate(x, ctx)
