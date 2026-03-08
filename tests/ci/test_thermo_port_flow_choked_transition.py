"""Choked/subcritical transition checks for port-flow equations."""

from __future__ import annotations

import numpy as np

from larrak2.thermo.port_flow import (
    compressible_orifice_mass_flow,
    critical_pressure_ratio,
    signed_orifice_mass_flow,
)


def test_choked_transition_continuity() -> None:
    gamma = 1.35
    p_up = 2.0e5
    t_up = 380.0
    area = 3.5e-4
    cd = 0.8
    r = 287.0

    pr_crit = critical_pressure_ratio(gamma)

    mdot_left, _ = compressible_orifice_mass_flow(
        p_up,
        t_up,
        p_up * max(1e-6, pr_crit - 1e-5),
        area,
        cd=cd,
        gamma=gamma,
        r_specific=r,
    )
    mdot_right, _ = compressible_orifice_mass_flow(
        p_up,
        t_up,
        p_up * min(0.999999, pr_crit + 1e-5),
        area,
        cd=cd,
        gamma=gamma,
        r_specific=r,
    )

    rel = abs(mdot_left - mdot_right) / max(abs(mdot_left), abs(mdot_right), 1e-12)
    assert rel <= 2e-2
    assert np.isfinite(mdot_left)
    assert np.isfinite(mdot_right)


def test_signed_orifice_mass_flow_uses_actual_upstream_temperature_forward() -> None:
    mdot_cool, _ = signed_orifice_mass_flow(
        1.2e5,
        300.0,
        9.0e4,
        900.0,
        3.5e-4,
        cd=0.8,
        gamma=1.35,
        r_specific=287.0,
    )
    mdot_hot, _ = signed_orifice_mass_flow(
        1.2e5,
        600.0,
        9.0e4,
        900.0,
        3.5e-4,
        cd=0.8,
        gamma=1.35,
        r_specific=287.0,
    )

    assert mdot_cool > mdot_hot > 0.0


def test_signed_orifice_mass_flow_uses_actual_upstream_temperature_reverse() -> None:
    mdot_cool_back, _ = signed_orifice_mass_flow(
        9.0e4,
        900.0,
        1.2e5,
        320.0,
        3.5e-4,
        cd=0.8,
        gamma=1.35,
        r_specific=287.0,
    )
    mdot_hot_back, _ = signed_orifice_mass_flow(
        9.0e4,
        900.0,
        1.2e5,
        620.0,
        3.5e-4,
        cd=0.8,
        gamma=1.35,
        r_specific=287.0,
    )

    assert abs(mdot_cool_back) > abs(mdot_hot_back)
    assert mdot_cool_back < 0.0
    assert mdot_hot_back < 0.0
