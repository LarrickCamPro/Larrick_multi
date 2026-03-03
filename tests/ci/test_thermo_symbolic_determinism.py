"""Determinism and roundtrip checks for thermo symbolic artifacts."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from larrak2.thermo.symbolic_artifact import (
    load_thermo_symbolic_artifact,
    save_thermo_symbolic_artifact,
    train_thermo_symbolic_affine,
)


def _build_dataset() -> tuple[
    np.ndarray, np.ndarray, tuple[str, ...], tuple[str, ...], tuple[str, ...]
]:
    rng = np.random.default_rng(123)
    n = 80
    X = rng.normal(size=(n, 6)).astype(np.float64)
    y0 = 0.6 * X[:, 0] - 0.2 * X[:, 1] + 0.05 * X[:, 4]
    y1 = -0.3 * X[:, 2] + 0.4 * X[:, 3] - 0.02 * X[:, 5]
    Y = np.column_stack([y0, y1]).astype(np.float64)
    feature_names = ("x_000", "x_001", "x_002", "x_003", "rpm", "torque")
    objective_names = ("eta_comb_gap",)
    constraint_names = ("mass_balance",)
    return X, Y, feature_names, objective_names, constraint_names


def test_train_thermo_symbolic_is_deterministic_for_fixed_seed() -> None:
    X, Y, feature_names, objective_names, constraint_names = _build_dataset()
    a1, m1 = train_thermo_symbolic_affine(
        X,
        Y,
        feature_names=feature_names,
        objective_names=objective_names,
        constraint_names=constraint_names,
        fidelity=1,
        seed=7,
        val_frac=0.2,
    )
    a2, m2 = train_thermo_symbolic_affine(
        X,
        Y,
        feature_names=feature_names,
        objective_names=objective_names,
        constraint_names=constraint_names,
        fidelity=1,
        seed=7,
        val_frac=0.2,
    )

    assert a1.version_hash == a2.version_hash
    assert np.allclose(a1.weight, a2.weight)
    assert np.allclose(a1.bias, a2.bias)
    assert m1["train_idx"] == m2["train_idx"]
    assert m1["val_idx"] == m2["val_idx"]
    assert m1["test_idx"] == m2["test_idx"]


def test_thermo_symbolic_load_save_roundtrip_preserves_version_hash(tmp_path: Path) -> None:
    X, Y, feature_names, objective_names, constraint_names = _build_dataset()
    artifact, _ = train_thermo_symbolic_affine(
        X,
        Y,
        feature_names=feature_names,
        objective_names=objective_names,
        constraint_names=constraint_names,
        fidelity=1,
        seed=9,
        val_frac=0.2,
    )
    p1 = tmp_path / "thermo_symbolic_a.npz"
    p2 = tmp_path / "thermo_symbolic_b.npz"
    save_thermo_symbolic_artifact(artifact, p1)
    loaded = load_thermo_symbolic_artifact(p1, validation_mode="strict")
    save_thermo_symbolic_artifact(loaded, p2)
    loaded2 = load_thermo_symbolic_artifact(p2, validation_mode="strict")

    assert loaded.version_hash == artifact.version_hash
    assert loaded2.version_hash == artifact.version_hash
    assert np.allclose(loaded.weight, loaded2.weight)
    assert np.allclose(loaded.bias, loaded2.bias)
