"""Lifetime scalar-fallback behavior and diagnostics."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from larrak2.core.encoding import mid_bounds_candidate
from larrak2.core.evaluator import evaluate_candidate
from larrak2.core.types import EvalContext


def _stub_thermo(*_args, **_kwargs):
    return SimpleNamespace(
        requested_ratio_profile=np.ones(360, dtype=np.float64),
        G=np.zeros(5, dtype=np.float64),
        efficiency=0.4,
        diag={
            "Q_chem": 1000.0,
            "Q_rel": 500.0,
            "W": 200.0,
            "T_wall_C": 180.0,
            "T_mean_wall": 180.0,
            "ratio_profile_stats": {"max_slope": 1.0, "max_jerk": 1.0},
            "ratio_slope_limit_used": 10.0,
            "motion_law": "Sine",
            "thermo_solver_status": "ok",
            "thermo_model_version": "two_zone_eq_v1",
            "thermo_constants_version": "test",
            "thermo_mass_residual": 0.0,
            "thermo_energy_residual": 0.0,
            "thermo_benchmark_status": "pass",
        },
    )


def _stub_gear_no_profiles(*_args, **_kwargs):
    return SimpleNamespace(
        loss_total=50.0,
        G=np.zeros(9, dtype=np.float64),
        diag={
            "hertz_stress_max": 1250.0,
            "sliding_speed_max": 4.0,
            "entrainment_velocity_mean": 12.0,
            "radius_strategy": {
                "selected_strategy": "test",
                "stress_source": "analytical_proxy",
                "calculix_stress_mode": "analytical",
            },
        },
    )


def _stub_gear_missing_hertz(*_args, **_kwargs):
    return SimpleNamespace(
        loss_total=50.0,
        G=np.zeros(9, dtype=np.float64),
        diag={
            "sliding_speed_max": 4.0,
            "entrainment_velocity_mean": 12.0,
            "radius_strategy": {
                "selected_strategy": "test",
                "stress_source": "analytical_proxy",
                "calculix_stress_mode": "analytical",
            },
        },
    )


def test_scalar_lifetime_fallback_computes_damage(monkeypatch) -> None:
    monkeypatch.setattr("larrak2.core.evaluator.eval_thermo", _stub_thermo)
    monkeypatch.setattr("larrak2.core.evaluator.eval_gear", _stub_gear_no_profiles)

    x = mid_bounds_candidate()
    ctx = EvalContext(
        rpm=3000.0,
        torque=200.0,
        fidelity=0,
        seed=1,
        strict_data=True,
        strict_tribology_data=False,
        surrogate_validation_mode="warn",
    )
    res = evaluate_candidate(x, ctx)
    life = res.diag["realworld"]["life_damage"]

    assert life["life_damage_input_mode"] == "scalar_proxy"
    assert float(life["D_total"]) > 0.0
    assert isinstance(life["N_set"], int)
    assert int(life["N_set"]) >= 1
    assert float(res.diag["objectives"]["life_damage_total"]) == pytest.approx(
        float(life["D_total"])
    )
    assert res.diag["realworld"]["life_damage_status"] == life["life_damage_status"]


def test_scalar_lifetime_strict_missing_hertz_fails(monkeypatch) -> None:
    monkeypatch.setattr("larrak2.core.evaluator.eval_thermo", _stub_thermo)
    monkeypatch.setattr("larrak2.core.evaluator.eval_gear", _stub_gear_missing_hertz)

    x = mid_bounds_candidate()
    ctx = EvalContext(
        rpm=3000.0,
        torque=200.0,
        fidelity=0,
        seed=1,
        strict_data=True,
        strict_tribology_data=False,
        surrogate_validation_mode="warn",
    )
    with pytest.raises(ValueError, match="hertz_stress_max"):
        evaluate_candidate(x, ctx)
