"""Thermo symbolic surrogate bridge for CasADi slice NLP overlays."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

from ..core.artifact_paths import DEFAULT_THERMO_SYMBOLIC_ARTIFACT
from ..core.types import EvalContext
from ..surrogate.stack.runtime import parse_feature_index
from .symbolic_artifact import ThermoSymbolicArtifact, load_thermo_symbolic_artifact

LOGGER = logging.getLogger(__name__)


def _import_casadi():
    try:
        import casadi as ca
    except Exception as exc:  # pragma: no cover - handled by caller
        raise ImportError(f"CasADi is required for thermo symbolic bridge: {exc}") from exc
    return ca


def assemble_thermo_symbolic_feature_vector(
    *,
    artifact: ThermoSymbolicArtifact,
    x_full_sym,
    rpm: float,
    torque: float,
):
    """Build symbolic feature vector from full design variable + operating point."""
    ca = _import_casadi()
    feats = []
    for name in artifact.feature_names:
        if name == "rpm":
            feats.append(ca.DM([float(rpm)])[0])
            continue
        if name == "torque":
            feats.append(ca.DM([float(torque)])[0])
            continue
        idx = parse_feature_index(name)
        if idx is None:
            raise ValueError(f"Unsupported thermo symbolic feature '{name}'")
        feats.append(x_full_sym[int(idx)])
    return ca.vertcat(*feats)


def symbolic_thermo_forward(artifact: ThermoSymbolicArtifact, x_features_sym):
    """Evaluate thermo symbolic affine model and return output vector."""
    ca = _import_casadi()
    x_mean = ca.DM(np.asarray(artifact.x_mean, dtype=np.float64))
    x_std = ca.DM(np.where(np.abs(artifact.x_std) > 0.0, artifact.x_std, 1.0))
    y_mean = ca.DM(np.asarray(artifact.y_mean, dtype=np.float64))
    y_std = ca.DM(np.where(np.abs(artifact.y_std) > 0.0, artifact.y_std, 1.0))
    W = ca.DM(np.asarray(artifact.weight, dtype=np.float64))
    b = ca.DM(np.asarray(artifact.bias, dtype=np.float64))

    h = (x_features_sym - x_mean) / x_std
    y_n = W @ h + b
    return y_n * y_std + y_mean


def numeric_thermo_forward(
    artifact: ThermoSymbolicArtifact,
    x_full: np.ndarray,
    *,
    rpm: float,
    torque: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Evaluate thermo symbolic model numerically for one sample."""
    x = np.asarray(x_full, dtype=np.float64).reshape(-1)
    feats = np.zeros(len(artifact.feature_names), dtype=np.float64)
    for i, name in enumerate(artifact.feature_names):
        if name == "rpm":
            feats[i] = float(rpm)
            continue
        if name == "torque":
            feats[i] = float(torque)
            continue
        idx = parse_feature_index(name)
        if idx is None or idx < 0 or idx >= x.size:
            raise ValueError(f"Invalid thermo symbolic feature '{name}' for vector size {x.size}")
        feats[i] = float(x[idx])

    x_scale = np.where(np.abs(artifact.x_std) > 0.0, artifact.x_std, 1.0)
    y_scale = np.where(np.abs(artifact.y_std) > 0.0, artifact.y_std, 1.0)
    y = (
        artifact.weight @ ((feats - artifact.x_mean) / x_scale)
        + artifact.bias
    ) * y_scale + artifact.y_mean
    n_obj = len(artifact.objective_names)
    return np.asarray(y[:n_obj], dtype=np.float64), np.asarray(y[n_obj:], dtype=np.float64)


def _raise_or_warn(mode: str, message: str) -> None:
    if mode == "strict":
        raise RuntimeError(message)
    if mode == "warn":
        LOGGER.warning(message)


def apply_thermo_symbolic_overlay(
    *,
    ctx: EvalContext,
    x_full_sym,
    stack_objective_names: tuple[str, ...],
    stack_constraint_names: tuple[str, ...],
    F_hat,
    G_hat,
) -> tuple[Any, Any, dict[str, Any]]:
    """Overlay stack objective/constraint expressions with thermo symbolic terms."""
    mode = str(getattr(ctx, "thermo_symbolic_mode", "off") or "off").lower()
    diag: dict[str, Any] = {
        "thermo_symbolic_mode": mode,
        "thermo_symbolic_used": False,
        "thermo_symbolic_version": "",
        "thermo_symbolic_path": "",
        "thermo_symbolic_overlay_objectives": [],
        "thermo_symbolic_overlay_constraints": [],
    }
    if mode == "off":
        return F_hat, G_hat, diag

    artifact_path = (
        str(getattr(ctx, "thermo_symbolic_artifact_path", "") or "").strip()
        or str(DEFAULT_THERMO_SYMBOLIC_ARTIFACT)
    )
    diag["thermo_symbolic_path"] = artifact_path
    try:
        artifact = load_thermo_symbolic_artifact(
            artifact_path,
            validation_mode=str(getattr(ctx, "surrogate_validation_mode", "strict")),
        )
    except Exception as exc:  # pragma: no cover - exercised by strict/warn branches
        _raise_or_warn(mode, f"Failed to load thermo symbolic artifact '{artifact_path}': {exc}")
        diag["thermo_symbolic_error"] = str(exc)
        return F_hat, G_hat, diag

    if int(artifact.fidelity) != int(ctx.fidelity):
        msg = (
            "Thermo symbolic artifact fidelity mismatch: "
            f"artifact={artifact.fidelity}, context={ctx.fidelity}"
        )
        _raise_or_warn(mode, msg)
        diag["thermo_symbolic_error"] = msg
        return F_hat, G_hat, diag

    feats_sym = assemble_thermo_symbolic_feature_vector(
        artifact=artifact,
        x_full_sym=x_full_sym,
        rpm=float(ctx.rpm),
        torque=float(ctx.torque),
    )
    y = symbolic_thermo_forward(artifact, feats_sym)
    n_obj = len(artifact.objective_names)
    obj_expr = y[:n_obj]
    con_expr = y[n_obj:]

    obj_idx_map = {name: i for i, name in enumerate(stack_objective_names)}
    con_idx_map = {name: i for i, name in enumerate(stack_constraint_names)}
    obj_overlay: dict[int, Any] = {}
    con_overlay: dict[int, Any] = {}

    for i, name in enumerate(artifact.objective_names):
        if name in obj_idx_map:
            obj_overlay[int(obj_idx_map[name])] = obj_expr[i]
    for i, name in enumerate(artifact.constraint_names):
        if name in con_idx_map:
            con_overlay[int(con_idx_map[name])] = con_expr[i]

    if not obj_overlay and not con_overlay:
        msg = (
            "Thermo symbolic overlay had no name matches against stack outputs. "
            f"artifact_obj={artifact.objective_names}, artifact_con={artifact.constraint_names}"
        )
        _raise_or_warn(mode, msg)
        diag["thermo_symbolic_error"] = msg
        return F_hat, G_hat, diag

    ca = _import_casadi()
    F_terms = [F_hat[i] for i in range(len(stack_objective_names))]
    G_terms = [G_hat[i] for i in range(len(stack_constraint_names))]
    for idx, expr in obj_overlay.items():
        F_terms[int(idx)] = expr
    for idx, expr in con_overlay.items():
        G_terms[int(idx)] = expr

    F_new = ca.vertcat(*F_terms) if F_terms else ca.MX([])
    G_new = ca.vertcat(*G_terms) if G_terms else ca.MX([])
    diag.update(
        {
            "thermo_symbolic_used": True,
            "thermo_symbolic_version": str(artifact.version_hash),
            "thermo_symbolic_path": str(Path(artifact_path)),
            "thermo_symbolic_overlay_objectives": [
                str(stack_objective_names[idx]) for idx in sorted(obj_overlay.keys())
            ],
            "thermo_symbolic_overlay_constraints": [
                str(stack_constraint_names[idx]) for idx in sorted(con_overlay.keys())
            ],
        }
    )
    return F_new, G_new, diag

