"""Compatibility shim to extracted CEM engine modules in `larrak-engines`.

`Larrick_multi` is a control-plane shell and does not own engine physics.
The canonical CEM implementation lives in `larrak-engines` as `larrak_engines.cem`.
"""

from __future__ import annotations

from larrak_engines.cem import *  # noqa: F403

