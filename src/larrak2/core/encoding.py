"""Compatibility shim to canonical encoding in `larrak_runtime`.

The canonical candidate encoding/decoding lives in `larrak-core` as
`larrak_runtime.core.encoding`. This module keeps the legacy import path stable
for callers that still use `larrak2.core.encoding`.
"""

from __future__ import annotations

from larrak_runtime.core.encoding import *  # noqa: F403

# Legacy constant alias kept for compatibility with older training utilities.
ENCODING_VERSION_V0_4 = LEGACY_ENCODING_VERSION
N_TOTAL_V0_4 = LEGACY_N_TOTAL

