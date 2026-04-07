"""Compatibility shim to engine evaluator in `larrak-engines`.

The canonical evaluation entrypoint for engine implementations lives in
`larrak-engines` as `larrak_engines.evaluator.evaluate_candidate`.
"""

from __future__ import annotations

from larrak_engines.evaluator import *  # noqa: F403

