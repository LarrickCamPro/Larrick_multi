"""ISO 6336-style tribology calculations.

Implements simplified models for:
- Specific film thickness λ (EHL film / composite roughness)
- Scuffing temperature margin (flash temperature method, ISO/TS 6336-20/21)
- Micropitting safety factor S_λ (ISO/TS 6336-22 style)

All coefficient tables are **placeholder** — designed to be replaced by
validated experimental datasets via the DatasetRegistry.

References:
    ISO/TS 6336-20: Scuffing load capacity (flash temperature)
    ISO/TS 6336-21: Scuffing load capacity (integral temperature)
    ISO/TS 6336-22: Micropitting load capacity
    NASA gear tribology: λ–life correlation, AGMA 925-A03 regimes
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np


class LubeRegime(Enum):
    """Lubrication regime classified by specific film thickness λ.

    Thresholds per AGMA 925-A03 / NASA correlation work:
        BOUNDARY:  λ ≤ 0.4
        MIXED:     0.4 < λ ≤ 1.0
        FULL_EHL:  λ > 1.0
    """

    BOUNDARY = "boundary"
    MIXED = "mixed"
    FULL_EHL = "full_ehl"


@dataclass(frozen=True)
class TribologyParams:
    """Operating-point tribology inputs.

    All values are for a single phase bin; the caller is responsible
    for evaluating across the phase grid and finding worst-case.

    Attributes:
        hertz_stress_MPa: Maximum Hertzian contact stress.
        sliding_velocity_m_s: Local sliding velocity at the contact.
        entrainment_velocity_m_s: Mean rolling (entrainment) velocity.
        oil_viscosity_cSt: Dynamic viscosity at contact inlet temperature.
        composite_roughness_um: Combined RMS roughness σ* (µm).
        bulk_temp_C: Bulk gear body temperature.
        oil_inlet_temp_C: Oil temperature at contact inlet.
    """

    hertz_stress_MPa: float = 1200.0
    sliding_velocity_m_s: float = 5.0
    entrainment_velocity_m_s: float = 15.0
    oil_viscosity_cSt: float = 12.0
    composite_roughness_um: float = 0.4
    bulk_temp_C: float = 150.0
    oil_inlet_temp_C: float = 90.0


# ---------------------------------------------------------------------------
# Placeholder EHL coefficients (simplified Dowson-Higginson-style)
# Replace with dataset-backed lookup when data is available.
# ---------------------------------------------------------------------------

# Simplified minimum film thickness (µm):
#   h_min ≈ k_ehl * (η₀ · U)^0.7 * R'^0.43 / (E' · W)^0.13
#
# We collapse dimensional groups into a single empirical scaling constant
# calibrated so that "typical" gear conditions give λ ≈ 1.0–1.5 with
# superfinished surfaces.  This is intentionally a rough proxy.

_K_EHL = 0.045  # Placeholder constant (µm · s^0.7 / cSt^0.7 / (m/s)^0.7)


def _get_ehl_constant() -> float:
    """Retrieve k_ehl from dataset registry if available, else placeholder."""
    try:
        from larrak2.cem.registry import get_registry

        reg = get_registry()
        table = reg.load_table("tribology_ehl_coefficients")
        if "ehl_constant" in table and len(table["ehl_constant"]) > 0:
            return float(table["ehl_constant"][0])
    except Exception:
        pass
    return _K_EHL


def compute_lambda(params: TribologyParams) -> float:
    """Compute specific film thickness λ = h_min / σ_composite.

    Uses a simplified Dowson-Higginson-inspired power-law correlation.
    The result is dimensionless and classifies the lubrication regime.

    Returns:
        λ value (float).  λ > 1 ≈ full EHL, 0.4–1.0 ≈ mixed, <0.4 ≈ boundary.
    """
    if params.composite_roughness_um <= 0:
        return 10.0  # Perfect surface → infinite film ratio (capped)

    # Viscosity-speed product (proxy for EHL film building capacity)
    viscosity_speed = params.oil_viscosity_cSt * params.entrainment_velocity_m_s
    if viscosity_speed <= 0:
        return 0.0

    # Simplified h_min (µm)
    k_ehl = _get_ehl_constant()
    h_min = k_ehl * (viscosity_speed**0.7)

    # Pressure correction (higher Hertz stress thins the film)
    if params.hertz_stress_MPa > 0:
        pressure_factor = (1500.0 / max(params.hertz_stress_MPa, 100.0)) ** 0.13
    else:
        pressure_factor = 1.0

    h_min *= pressure_factor

    # Temperature correction (viscosity drops with temperature)
    # Simplified: assume viscosity already reflects temperature; apply
    # a mild additional penalty for bulk temperature above 120 °C.
    if params.bulk_temp_C > 120.0:
        temp_penalty = max(0.3, 1.0 - 0.003 * (params.bulk_temp_C - 120.0))
        h_min *= temp_penalty

    lambda_val = h_min / params.composite_roughness_um
    return float(np.clip(lambda_val, 0.0, 10.0))


def classify_regime(lambda_val: float) -> LubeRegime:
    """Classify lubrication regime from specific film thickness."""
    if lambda_val <= 0.4:
        return LubeRegime.BOUNDARY
    elif lambda_val <= 1.0:
        return LubeRegime.MIXED
    else:
        return LubeRegime.FULL_EHL


# ---------------------------------------------------------------------------
# Scuffing temperature margin (flash temperature method)
# ---------------------------------------------------------------------------

# Placeholder critical scuff temperature (°C) — from FZG-class test data.
# Real value depends on oil + additive package + material.
_T_SCUFF_CRIT = 400.0  # Placeholder (°C)


def _get_scuff_crit_temp() -> float:
    """Retrieve critical scuffing temperature from dataset registry if available."""
    try:
        from larrak2.cem.registry import get_registry

        reg = get_registry()
        table = reg.load_table("scuffing_critical_temperatures")
        if "T_crit_C" in table and len(table["T_crit_C"]) > 0:
            return float(table["T_crit_C"][0])
    except Exception:
        pass
    return _T_SCUFF_CRIT


# Friction coefficient for flash temperature calculation
_MU_FLASH = 0.06  # Placeholder


def compute_scuff_margin(params: TribologyParams) -> float:
    """Compute scuffing temperature margin (°C).

    Positive margin = safe.  Negative = scuffing risk.

    Uses simplified flash temperature method:
        T_flash ≈ μ · W_load_proxy · |v_s| / (k_thermal · √(v_e))
    where the load proxy is derived from Hertz stress.

    Returns:
        Temperature margin (°C): T_crit − (T_bulk + T_flash).
    """
    # Flash temperature rise (simplified)
    sliding = abs(params.sliding_velocity_m_s)
    entrainment = max(abs(params.entrainment_velocity_m_s), 0.1)

    # Load proxy from Hertz stress (simplified: stress² ∝ force/length)
    load_proxy = (params.hertz_stress_MPa / 1000.0) ** 2

    flash_temp = _MU_FLASH * load_proxy * sliding / (0.01 * np.sqrt(entrainment))

    # Cap at reasonable values
    flash_temp = float(np.clip(flash_temp, 0.0, 500.0))

    contact_temp = params.bulk_temp_C + flash_temp
    T_crit = _get_scuff_crit_temp()
    margin = T_crit - contact_temp
    return float(margin)


# ---------------------------------------------------------------------------
# Micropitting safety factor
# ---------------------------------------------------------------------------

# Permissible minimum specific film thickness (placeholder)
# Typical FZG-derived values are 0.1–0.3 depending on oil + finish.
_LAMBDA_PERM = 0.3  # Placeholder


def compute_micropitting_safety(lambda_val: float, lambda_perm: float = _LAMBDA_PERM) -> float:
    """Compute micropitting safety factor S_λ = λ_min / λ_perm.

    Per ISO/TS 6336-22, micropitting occurs when the minimum local
    specific film thickness falls below the permissible value.

    Args:
        lambda_val: Minimum specific film thickness in the contact zone.
        lambda_perm: Permissible specific film thickness (from test data).

    Returns:
        Safety factor S_λ.  S_λ ≥ 1.0 → acceptable risk.
    """
    if lambda_perm <= 0:
        return 10.0
    return float(lambda_val / lambda_perm)
