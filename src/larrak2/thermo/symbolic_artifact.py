"""Artifact format and training utilities for thermo symbolic surrogates."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ..surrogate.quality_contract import (
    regression_metrics,
    sha256_file,
    validate_artifact_quality,
    write_quality_report,
)


@dataclass(frozen=True)
class ThermoSymbolicArtifact:
    """Affine surrogate artifact used to overlay thermo terms in symbolic NLP."""

    feature_names: tuple[str, ...]
    objective_names: tuple[str, ...]
    constraint_names: tuple[str, ...]
    fidelity: int
    x_mean: np.ndarray
    x_std: np.ndarray
    y_mean: np.ndarray
    y_std: np.ndarray
    weight: np.ndarray  # shape: (n_out, n_in)
    bias: np.ndarray  # shape: (n_out,)
    version_hash: str = ""

    def __post_init__(self) -> None:
        n_in = len(self.feature_names)
        n_obj = len(self.objective_names)
        n_con = len(self.constraint_names)
        n_out = n_obj + n_con
        if n_in <= 0:
            raise ValueError("feature_names cannot be empty")
        if n_out <= 0:
            raise ValueError("objective_names + constraint_names cannot both be empty")
        if int(self.fidelity) < 0:
            raise ValueError("fidelity must be >= 0")

        x_mean = np.asarray(self.x_mean, dtype=np.float64).reshape(-1)
        x_std = np.asarray(self.x_std, dtype=np.float64).reshape(-1)
        y_mean = np.asarray(self.y_mean, dtype=np.float64).reshape(-1)
        y_std = np.asarray(self.y_std, dtype=np.float64).reshape(-1)
        weight = np.asarray(self.weight, dtype=np.float64)
        bias = np.asarray(self.bias, dtype=np.float64).reshape(-1)

        if x_mean.size != n_in or x_std.size != n_in:
            raise ValueError("x normalization shape mismatch")
        if y_mean.size != n_out or y_std.size != n_out:
            raise ValueError("y normalization shape mismatch")
        if weight.shape != (n_out, n_in):
            raise ValueError(f"weight shape mismatch: expected {(n_out, n_in)}, got {weight.shape}")
        if bias.size != n_out:
            raise ValueError("bias shape mismatch")

        object.__setattr__(self, "x_mean", x_mean)
        object.__setattr__(self, "x_std", x_std)
        object.__setattr__(self, "y_mean", y_mean)
        object.__setattr__(self, "y_std", y_std)
        object.__setattr__(self, "weight", weight)
        object.__setattr__(self, "bias", bias)
        if not self.version_hash:
            object.__setattr__(self, "version_hash", _compute_version_hash(self))


def _compute_version_hash(artifact: ThermoSymbolicArtifact) -> str:
    h = hashlib.sha256()
    meta = {
        "feature_names": list(artifact.feature_names),
        "objective_names": list(artifact.objective_names),
        "constraint_names": list(artifact.constraint_names),
        "fidelity": int(artifact.fidelity),
    }
    h.update(json.dumps(meta, sort_keys=True).encode("utf-8"))
    h.update(np.asarray(artifact.x_mean, dtype=np.float64).tobytes())
    h.update(np.asarray(artifact.x_std, dtype=np.float64).tobytes())
    h.update(np.asarray(artifact.y_mean, dtype=np.float64).tobytes())
    h.update(np.asarray(artifact.y_std, dtype=np.float64).tobytes())
    h.update(np.asarray(artifact.weight, dtype=np.float64).tobytes())
    h.update(np.asarray(artifact.bias, dtype=np.float64).tobytes())
    return h.hexdigest()[:16]


def _split_indices(
    n: int,
    *,
    seed: int,
    val_frac: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if n <= 0:
        z = np.zeros(0, dtype=np.int64)
        return z, z, z
    rng = np.random.default_rng(int(seed))
    order = rng.permutation(n)
    n_val = max(1, int(round(float(val_frac) * n)))
    n_val = min(n_val, max(1, n - 2)) if n >= 3 else min(n_val, max(0, n - 1))
    n_test = n_val if n >= 5 else max(1, n - n_val - 1)
    n_test = min(n_test, max(0, n - n_val - 1))
    n_train = max(1, n - n_val - n_test)
    train_idx = order[:n_train]
    val_idx = order[n_train : n_train + n_val]
    test_idx = order[n_train + n_val :]
    return train_idx, val_idx, test_idx


def _predict_affine(
    *,
    weight: np.ndarray,
    bias: np.ndarray,
    x_mean: np.ndarray,
    x_std: np.ndarray,
    y_mean: np.ndarray,
    y_std: np.ndarray,
    X: np.ndarray,
) -> np.ndarray:
    x_scale = np.where(np.abs(x_std) > 0.0, x_std, 1.0)
    y_scale = np.where(np.abs(y_std) > 0.0, y_std, 1.0)
    Xn = (np.asarray(X, dtype=np.float64) - x_mean.reshape(1, -1)) / x_scale.reshape(1, -1)
    Yn = Xn @ weight.T + bias.reshape(1, -1)
    return Yn * y_scale.reshape(1, -1) + y_mean.reshape(1, -1)


def train_thermo_symbolic_affine(
    X: np.ndarray,
    Y: np.ndarray,
    *,
    feature_names: tuple[str, ...],
    objective_names: tuple[str, ...],
    constraint_names: tuple[str, ...],
    fidelity: int,
    seed: int = 42,
    val_frac: float = 0.2,
) -> tuple[ThermoSymbolicArtifact, dict[str, Any]]:
    """Fit a normalized affine surrogate and return artifact + metrics."""
    X = np.asarray(X, dtype=np.float64)
    Y = np.asarray(Y, dtype=np.float64)
    if X.ndim != 2 or Y.ndim != 2:
        raise ValueError("X and Y must be 2D arrays")
    if X.shape[0] != Y.shape[0]:
        raise ValueError("X/Y row mismatch")
    if X.shape[1] != len(feature_names):
        raise ValueError("feature_names length mismatch")
    if Y.shape[1] != len(objective_names) + len(constraint_names):
        raise ValueError("target schema mismatch")
    if X.shape[0] < 5:
        raise ValueError("Need at least 5 samples for train/val/test splits")

    train_idx, val_idx, test_idx = _split_indices(X.shape[0], seed=int(seed), val_frac=float(val_frac))
    X_tr = X[train_idx]
    Y_tr = Y[train_idx]

    x_mean = np.mean(X_tr, axis=0)
    x_std = np.std(X_tr, axis=0)
    y_mean = np.mean(Y_tr, axis=0)
    y_std = np.std(Y_tr, axis=0)
    x_scale = np.where(np.abs(x_std) > 0.0, x_std, 1.0)
    y_scale = np.where(np.abs(y_std) > 0.0, y_std, 1.0)

    Xn = (X_tr - x_mean.reshape(1, -1)) / x_scale.reshape(1, -1)
    Yn = (Y_tr - y_mean.reshape(1, -1)) / y_scale.reshape(1, -1)
    Xn_aug = np.hstack([Xn, np.ones((Xn.shape[0], 1), dtype=np.float64)])
    coef, *_ = np.linalg.lstsq(Xn_aug, Yn, rcond=None)
    weight = np.asarray(coef[:-1, :].T, dtype=np.float64)
    bias = np.asarray(coef[-1, :], dtype=np.float64)

    artifact = ThermoSymbolicArtifact(
        feature_names=tuple(feature_names),
        objective_names=tuple(objective_names),
        constraint_names=tuple(constraint_names),
        fidelity=int(fidelity),
        x_mean=x_mean,
        x_std=x_std,
        y_mean=y_mean,
        y_std=y_std,
        weight=weight,
        bias=bias,
    )

    Y_pred = _predict_affine(
        weight=artifact.weight,
        bias=artifact.bias,
        x_mean=artifact.x_mean,
        x_std=artifact.x_std,
        y_mean=artifact.y_mean,
        y_std=artifact.y_std,
        X=X,
    )

    def _split_metrics(idx: np.ndarray) -> dict[str, float]:
        if idx.size == 0:
            return {"rmse": float("nan"), "mae": float("nan"), "r2": float("nan")}
        return regression_metrics(Y[idx], Y_pred[idx])

    train_m = _split_metrics(train_idx)
    val_m = _split_metrics(val_idx)
    test_m = _split_metrics(test_idx)
    metrics = {
        "n_samples": int(X.shape[0]),
        "n_features": int(X.shape[1]),
        "n_targets": int(Y.shape[1]),
        "train": train_m,
        "val": val_m,
        "test": test_m,
        "train_idx": train_idx.tolist(),
        "val_idx": val_idx.tolist(),
        "test_idx": test_idx.tolist(),
    }
    return artifact, metrics


def save_thermo_symbolic_artifact(
    artifact: ThermoSymbolicArtifact,
    path: str | Path,
    *,
    quality_report: dict[str, Any] | None = None,
) -> Path:
    """Persist thermo symbolic artifact and optional quality report."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    meta = {
        "feature_names": list(artifact.feature_names),
        "objective_names": list(artifact.objective_names),
        "constraint_names": list(artifact.constraint_names),
        "fidelity": int(artifact.fidelity),
        "version_hash": str(artifact.version_hash),
        "model_family": "affine_v1",
    }
    np.savez_compressed(
        target,
        __meta_json__=np.array(json.dumps(meta), dtype=object),
        x_mean=np.asarray(artifact.x_mean, dtype=np.float64),
        x_std=np.asarray(artifact.x_std, dtype=np.float64),
        y_mean=np.asarray(artifact.y_mean, dtype=np.float64),
        y_std=np.asarray(artifact.y_std, dtype=np.float64),
        weight=np.asarray(artifact.weight, dtype=np.float64),
        bias=np.asarray(artifact.bias, dtype=np.float64),
    )

    report = quality_report or {
        "schema_version": "surrogate_quality_report_v1",
        "surrogate_kind": "thermo_symbolic",
        "artifact_file": target.name,
        "artifact_sha256": sha256_file(target),
        "dataset_manifest": {
            "source_path": "",
            "num_samples": 0,
            "num_features": int(len(artifact.feature_names)),
            "num_targets": int(len(artifact.objective_names) + len(artifact.constraint_names)),
            "dataset_sha256": "",
        },
        "metrics": {
            "train": {"rmse": float("nan"), "mae": float("nan"), "r2": float("nan")},
            "val": {"rmse": float("nan"), "mae": float("nan"), "r2": float("nan")},
            "test": {"rmse": float("nan"), "mae": float("nan"), "r2": float("nan")},
            "slice_metrics": [],
        },
        "ood_thresholds": {},
        "uncertainty_calibration": {"method": "deterministic_affine", "status": "not_applicable"},
        "required_artifacts": [target.name],
        "pass": True,
        "fail_reasons": [],
    }
    write_quality_report(target.parent / "quality_report.json", report)
    return target


def load_thermo_symbolic_artifact(
    path: str | Path,
    *,
    validation_mode: str = "strict",
) -> ThermoSymbolicArtifact:
    """Load thermo symbolic artifact from NPZ and validate quality contract."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Thermo symbolic artifact not found: {p}")
    validate_artifact_quality(
        p,
        surrogate_kind="thermo_symbolic",
        validation_mode=str(validation_mode),
        required_artifacts=[p.name],
    )
    with np.load(p, allow_pickle=True) as data:
        if "__meta_json__" not in data:
            raise ValueError(f"Artifact missing __meta_json__: {p}")
        meta = json.loads(str(data["__meta_json__"].item()))
        return ThermoSymbolicArtifact(
            feature_names=tuple(meta["feature_names"]),
            objective_names=tuple(meta["objective_names"]),
            constraint_names=tuple(meta["constraint_names"]),
            fidelity=int(meta.get("fidelity", 1)),
            x_mean=np.asarray(data["x_mean"], dtype=np.float64),
            x_std=np.asarray(data["x_std"], dtype=np.float64),
            y_mean=np.asarray(data["y_mean"], dtype=np.float64),
            y_std=np.asarray(data["y_std"], dtype=np.float64),
            weight=np.asarray(data["weight"], dtype=np.float64),
            bias=np.asarray(data["bias"], dtype=np.float64),
            version_hash=str(meta.get("version_hash", "")),
        )

