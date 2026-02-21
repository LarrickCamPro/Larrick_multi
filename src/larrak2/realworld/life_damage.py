"""Phase-binned service-life damage accumulation model.

Implements a simplified Miner-rule proxy for 10,000 h gear service life.
Each phase bin accumulates damage based on contact stress, lubricant film
quality (λ), and the pseudo-hunting exposure reduction factor.

Convention:  D_total ≤ 1.0  →  feasible for the target service life.
             D_total > 1.0  →  expected failure before service life.
"""

from __future__ import annotations

import numpy as np


# Wöhler exponent for contact fatigue (typical carburized steel)
_STRESS_EXPONENT = 8.0

# Reference stress for unit damage rate (MPa) — calibrated to AISI 9310 baseline
_SIGMA_REF_MPA = 1500.0

# Lambda influence exponent: lower λ → faster damage accumulation
_LAMBDA_EXPONENT = 2.0

# Pseudo-hunting set cardinality ladder
_HUNTING_LADDER: list[tuple[float, int]] = [
    (0.00, 1),
    (0.15, 2),
    (0.30, 3),
    (0.45, 4),
    (0.65, 6),
    (0.85, 8),
]


def hunting_n_set(level: float) -> int:
    """Map continuous hunting_level (0–1) to discrete tooth-set count N_set."""
    level = float(np.clip(level, 0.0, 1.0))
    best = 1
    for threshold, n in _HUNTING_LADDER:
        if level >= threshold:
            best = n
    return best


def compute_life_damage_10k(
    hertz_stress_profile: np.ndarray,
    lambda_profile: np.ndarray,
    fn_profile: np.ndarray,
    rpm: float,
    hunting_level: float,
    service_hours: float = 10_000.0,
) -> dict:
    """Compute accumulated Miner-style damage for target service life.

    Args:
        hertz_stress_profile: Hertz contact stress per phase bin (MPa).
        lambda_profile: Specific film thickness per phase bin (dimensionless).
        fn_profile: Normal force per phase bin (N), used for force-gating.
        rpm: Operating speed (rev/min).
        hunting_level: Continuous [0,1] pseudo-hunting level.
        service_hours: Target service life (hours), default 10,000.

    Returns:
        Dictionary with:
            D_total: Total accumulated damage (≤1.0 = feasible).
            D_ring: Ring-side accumulated damage (includes hunting reduction).
            D_planet: Planet-side accumulated damage (conservative, no reduction).
            N_set: Decoded hunting set count.
            revs_total: Total revolutions in service life.
    """
    n_bins = len(hertz_stress_profile)
    if n_bins == 0:
        return {"D_total": 0.0, "D_ring": 0.0, "D_planet": 0.0,
                "N_set": 1, "revs_total": 0.0}

    N_set = hunting_n_set(hunting_level)
    revs_total = rpm * 60.0 * service_hours

    # Per-bin damage rate:
    #   dD(θ) = (σ_H / σ_ref)^n / max(λ, 0.1)^m
    # Summed over bins per revolution, then multiplied by total revolutions.

    sigma_ratio = np.maximum(hertz_stress_profile, 0.0) / _SIGMA_REF_MPA
    lambda_clamp = np.maximum(lambda_profile, 0.1)

    dD_per_bin = (sigma_ratio ** _STRESS_EXPONENT) / (lambda_clamp ** _LAMBDA_EXPONENT)

    # Force-gate: only count bins where normal force > 50% of mean
    force_mean = float(np.mean(np.maximum(fn_profile, 0.0)))
    if force_mean > 0:
        active_mask = fn_profile > 0.5 * force_mean
    else:
        active_mask = np.ones(n_bins, dtype=bool)

    D_per_rev_planet = float(np.sum(dD_per_bin[active_mask])) / n_bins
    D_per_rev_ring = D_per_rev_planet / N_set  # hunting reduces ring exposure

    D_planet = D_per_rev_planet * revs_total
    D_ring = D_per_rev_ring * revs_total

    # Total damage is the maximum of ring and planet (whichever fails first)
    D_total = max(D_planet, D_ring)

    return {
        "D_total": float(D_total),
        "D_ring": float(D_ring),
        "D_planet": float(D_planet),
        "N_set": N_set,
        "revs_total": float(revs_total),
    }
