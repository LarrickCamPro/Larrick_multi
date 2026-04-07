"""Compatibility shim to canonical workflow contracts in `larrak_runtime`.

The canonical contract schema and tracer live in `larrak-core` as
`larrak_runtime.architecture.contracts`.

This module exists to keep the legacy `larrak2.architecture.contracts` import
path stable for the control-plane shell and downstream callers.
"""

from __future__ import annotations

from larrak_runtime.architecture.contracts import *  # noqa: F403

