"""Compatibility shim to canonical surrogate artifact contract in `larrak_runtime`.

The canonical surrogate quality contract schema and validators live in
`larrak-core` as `larrak_runtime.surrogate.quality_contract`. This module keeps
the legacy import path stable for callers inside the control-plane shell.
"""

from __future__ import annotations

from larrak_runtime.surrogate.quality_contract import *  # noqa: F403

