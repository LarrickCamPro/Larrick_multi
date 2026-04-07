"""Compatibility shim to `larrak_simulation.training.workflows`."""

from __future__ import annotations

from larrak_simulation.training.workflows import *  # noqa: F403

# Explicit re-exports for legacy internal helpers that start with underscore.
# These are imported directly by `larrak2.training.overnight_campaign`.
from larrak_simulation.training.workflows import _infer_objective_names as _infer_objective_names

