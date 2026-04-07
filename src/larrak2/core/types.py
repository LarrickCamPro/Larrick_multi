"""Compatibility shim to canonical runtime types in `larrak_runtime`.

The canonical evaluation types live in `larrak-core` as `larrak_runtime.core.types`.
This module keeps the legacy import path stable for the control-plane shell.
"""

from __future__ import annotations

from larrak_runtime.core.types import *  # noqa: F403

