"""Compatibility shim to `larrak_simulation.training.overnight_campaign`.

This shim is implemented as a module alias so that test monkeypatching of
attributes (for example `build_truth_anchor_bundle`) affects the real
implementation module.
"""

from __future__ import annotations

import sys

import larrak_simulation.training.overnight_campaign as _impl

sys.modules[__name__] = _impl

