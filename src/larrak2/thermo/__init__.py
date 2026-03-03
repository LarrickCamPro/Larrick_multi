from __future__ import annotations

"""Thermo module — equation-first thermodynamic physics models."""

from .constants import ThermoConstants, load_anchor_manifest, load_thermo_constants
from .motionlaw import ThermoResult, eval_thermo
from .symbolic_artifact import (
    ThermoSymbolicArtifact,
    load_thermo_symbolic_artifact,
    save_thermo_symbolic_artifact,
    train_thermo_symbolic_affine,
)
from .symbolic_bridge import (
    apply_thermo_symbolic_overlay,
    assemble_thermo_symbolic_feature_vector,
    numeric_thermo_forward,
    symbolic_thermo_forward,
)
from .two_zone import TwoZoneThermoResult, evaluate_two_zone_thermo
from .validation import ThermoValidationReport

__all__ = [
    "ThermoConstants",
    "ThermoResult",
    "ThermoSymbolicArtifact",
    "ThermoValidationReport",
    "TwoZoneThermoResult",
    "apply_thermo_symbolic_overlay",
    "assemble_thermo_symbolic_feature_vector",
    "eval_thermo",
    "evaluate_two_zone_thermo",
    "load_anchor_manifest",
    "load_thermo_symbolic_artifact",
    "load_thermo_constants",
    "numeric_thermo_forward",
    "save_thermo_symbolic_artifact",
    "symbolic_thermo_forward",
    "train_thermo_symbolic_affine",
]
