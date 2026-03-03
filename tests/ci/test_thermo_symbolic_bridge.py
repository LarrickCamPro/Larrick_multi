"""Thermo symbolic bridge tests."""

from __future__ import annotations

import numpy as np
import pytest

from larrak2.core.encoding import N_TOTAL
from larrak2.core.types import EvalContext
from larrak2.thermo.symbolic_artifact import (
    ThermoSymbolicArtifact,
    save_thermo_symbolic_artifact,
)
from larrak2.thermo.symbolic_bridge import (
    apply_thermo_symbolic_overlay,
    assemble_thermo_symbolic_feature_vector,
    numeric_thermo_forward,
    symbolic_thermo_forward,
)


def _test_artifact() -> ThermoSymbolicArtifact:
    return ThermoSymbolicArtifact(
        feature_names=("x_000", "x_010", "rpm", "torque"),
        objective_names=("eta_comb_gap",),
        constraint_names=("mass_balance",),
        fidelity=1,
        x_mean=np.zeros(4, dtype=np.float64),
        x_std=np.ones(4, dtype=np.float64),
        y_mean=np.zeros(2, dtype=np.float64),
        y_std=np.ones(2, dtype=np.float64),
        weight=np.array([[0.5, -0.2, 1e-4, 2e-4], [-0.1, 0.3, 5e-5, -1e-4]], dtype=np.float64),
        bias=np.array([0.25, -0.15], dtype=np.float64),
    )


def test_symbolic_and_numeric_forward_match() -> None:
    ca = pytest.importorskip("casadi")
    artifact = _test_artifact()

    x_full = np.linspace(0.1, 0.9, N_TOTAL, dtype=np.float64)
    rpm = 2450.0
    torque = 135.0

    x_sym = ca.MX.sym("x", N_TOTAL)
    feats_sym = assemble_thermo_symbolic_feature_vector(
        artifact=artifact,
        x_full_sym=x_sym,
        rpm=rpm,
        torque=torque,
    )
    y_sym = symbolic_thermo_forward(artifact, feats_sym)
    fn = ca.Function("thermo_sym", [x_sym], [y_sym])
    y_sym_val = np.asarray(fn(x_full), dtype=np.float64).reshape(-1)

    y_obj, y_con = numeric_thermo_forward(artifact, x_full, rpm=rpm, torque=torque)
    y_num_val = np.concatenate([y_obj, y_con], axis=0)

    assert np.allclose(y_sym_val, y_num_val, rtol=1e-10, atol=1e-10)


def test_apply_overlay_strict_replaces_named_terms_and_emits_diag(tmp_path) -> None:
    ca = pytest.importorskip("casadi")
    artifact = ThermoSymbolicArtifact(
        feature_names=("x_000", "rpm", "torque"),
        objective_names=("eta_comb_gap",),
        constraint_names=("mass_balance",),
        fidelity=1,
        x_mean=np.zeros(3, dtype=np.float64),
        x_std=np.ones(3, dtype=np.float64),
        y_mean=np.zeros(2, dtype=np.float64),
        y_std=np.ones(2, dtype=np.float64),
        weight=np.zeros((2, 3), dtype=np.float64),
        bias=np.array([2.0, -3.0], dtype=np.float64),
    )
    artifact_path = tmp_path / "thermo_symbolic_f1.npz"
    save_thermo_symbolic_artifact(artifact, artifact_path)

    x_sym = ca.MX.sym("x", N_TOTAL)
    F_hat = ca.vertcat(x_sym[0], x_sym[1])
    G_hat = ca.vertcat(x_sym[2], x_sym[3])
    ctx = EvalContext(
        rpm=2600.0,
        torque=145.0,
        fidelity=1,
        seed=1,
        thermo_symbolic_mode="strict",
        thermo_symbolic_artifact_path=str(artifact_path),
    )

    F_new, G_new, diag = apply_thermo_symbolic_overlay(
        ctx=ctx,
        x_full_sym=x_sym,
        stack_objective_names=("obj_static", "eta_comb_gap"),
        stack_constraint_names=("g_static", "mass_balance"),
        F_hat=F_hat,
        G_hat=G_hat,
    )
    fn = ca.Function("overlay_eval", [x_sym], [F_new, G_new])
    x_val = np.linspace(0.2, 0.8, N_TOTAL, dtype=np.float64)
    f_val, g_val = fn(x_val)
    f_arr = np.asarray(f_val, dtype=np.float64).reshape(-1)
    g_arr = np.asarray(g_val, dtype=np.float64).reshape(-1)

    assert np.isclose(f_arr[0], x_val[0])
    assert np.isclose(f_arr[1], 2.0)
    assert np.isclose(g_arr[0], x_val[2])
    assert np.isclose(g_arr[1], -3.0)
    assert diag["thermo_symbolic_used"] is True
    assert diag["thermo_symbolic_mode"] == "strict"
    assert diag["thermo_symbolic_version"] == artifact.version_hash
    assert diag["thermo_symbolic_overlay_objectives"] == ["eta_comb_gap"]
    assert diag["thermo_symbolic_overlay_constraints"] == ["mass_balance"]


def test_apply_overlay_warn_missing_artifact_falls_back() -> None:
    ca = pytest.importorskip("casadi")
    x_sym = ca.MX.sym("x", N_TOTAL)
    F_hat = ca.vertcat(x_sym[0])
    G_hat = ca.vertcat(x_sym[1])
    ctx = EvalContext(
        rpm=2500.0,
        torque=120.0,
        fidelity=1,
        seed=2,
        thermo_symbolic_mode="warn",
        thermo_symbolic_artifact_path="missing_thermo_symbolic.npz",
    )

    F_new, G_new, diag = apply_thermo_symbolic_overlay(
        ctx=ctx,
        x_full_sym=x_sym,
        stack_objective_names=("obj0",),
        stack_constraint_names=("g0",),
        F_hat=F_hat,
        G_hat=G_hat,
    )
    assert F_new.shape == F_hat.shape
    assert G_new.shape == G_hat.shape
    assert diag["thermo_symbolic_mode"] == "warn"
    assert diag["thermo_symbolic_used"] is False
    assert "thermo_symbolic_error" in diag
