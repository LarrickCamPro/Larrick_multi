"""Candidate encoding and decoding.

This module defines the parameter structure and provides pack/unpack
functions for the flat decision vector x.

Layout (ENCODING_VERSION = "0.4"):
    x[0:5]   - ThermoParams (5 floats)
    x[5:14]  - GearParams (9 floats: base_radius + 7 pitch_coeffs + face_width)
    x[14:22] - RealWorldParams (8 floats: surface_finish, lube, material, coating,
               hunting, oil_flow, oil_supply_temp, evacuation)
    Total: 22 decision variables
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

ENCODING_VERSION = "0.4"

# Decision variable count
N_THERMO = 5
N_GEAR = 9       # base_radius(1) + pitch_coeffs(7) + face_width(1)
N_REALWORLD = 8  # surface_finish, lube_mode, material, coating, hunting, oil_flow, oil_temp, evacuation
N_TOTAL = N_THERMO + N_GEAR + N_REALWORLD  # 22


@dataclass
class ThermoParams:
    """Thermodynamic control parameters.

    Attributes:
        compression_duration: Compression phase duration (degrees), [30, 90].
        expansion_duration: Expansion phase duration (degrees), [60, 120].
        heat_release_center: Center of heat release (degrees), [0, 30].
        heat_release_width: Heat release duration (degrees), [10, 60].
        lambda_af: Air-fuel equivalence ratio λ [-], where λ < 1 is rich and λ > 1 is lean.
    """

    compression_duration: float
    expansion_duration: float
    heat_release_center: float
    heat_release_width: float
    lambda_af: float

    def to_array(self) -> np.ndarray:
        """Convert to flat array."""
        return np.array(
            [
                self.compression_duration,
                self.expansion_duration,
                self.heat_release_center,
                self.heat_release_width,
                self.lambda_af,
            ],
            dtype=np.float64,
        )

    @classmethod
    def from_array(cls, arr: np.ndarray) -> ThermoParams:
        """Create from flat array."""
        return cls(
            compression_duration=float(arr[0]),
            expansion_duration=float(arr[1]),
            heat_release_center=float(arr[2]),
            heat_release_width=float(arr[3]),
            lambda_af=float(arr[4]),
        )


@dataclass
class GearParams:
    """Gear synthesis control parameters.

    Attributes:
        base_radius: Base circle radius (mm), [20, 60].
        pitch_coeffs: Fourier coefficients for pitch curve (7 floats).
        face_width_mm: Gear face width (mm), [4, 14]. Upper bound = gear body z-height.
    """

    base_radius: float
    pitch_coeffs: np.ndarray  # 7 coefficients
    face_width_mm: float      # Constrained by gear body z-height

    def to_array(self) -> np.ndarray:
        """Convert to flat array."""
        return np.concatenate([[self.base_radius], self.pitch_coeffs, [self.face_width_mm]])

    @classmethod
    def from_array(cls, arr: np.ndarray) -> GearParams:
        """Create from flat array."""
        return cls(
            base_radius=float(arr[0]),
            pitch_coeffs=np.array(arr[1:8], dtype=np.float64),
            face_width_mm=float(arr[8]),
        )


@dataclass
class RealWorldParams:
    """Real-world engineering decision parameters.

    Continuous 0–1 levels that map to CEM enum tiers during evaluation.

    Attributes:
        surface_finish_level: 0→as-ground, 0.5→fine-ground, 1→superfinished.
        lube_mode_level: 0→dry, 0.33→splash, 0.67→jet, 1→phase-gated jet.
        material_quality_level: 0→9310, 0.5→CBS-50NiL, 1→Ferrium C64.
        coating_level: 0→none, 0.5→ta-C, 1→W-DLC/CrN duplex.
        hunting_level: 0→1-set, 0.5→4-set, 1→8-set pseudo-hunting.
        oil_flow_level: 0→0.5 L/min, 1→10 L/min.
        oil_supply_temp_level: 0→40°C, 1→120°C.
        evacuation_level: 0→passive drain, 1→active scavenge.
    """

    surface_finish_level: float
    lube_mode_level: float
    material_quality_level: float
    coating_level: float
    hunting_level: float
    oil_flow_level: float
    oil_supply_temp_level: float
    evacuation_level: float

    def to_array(self) -> np.ndarray:
        """Convert to flat array."""
        return np.array(
            [
                self.surface_finish_level,
                self.lube_mode_level,
                self.material_quality_level,
                self.coating_level,
                self.hunting_level,
                self.oil_flow_level,
                self.oil_supply_temp_level,
                self.evacuation_level,
            ],
            dtype=np.float64,
        )

    @classmethod
    def from_array(cls, arr: np.ndarray) -> RealWorldParams:
        """Create from flat array."""
        return cls(
            surface_finish_level=float(arr[0]),
            lube_mode_level=float(arr[1]),
            material_quality_level=float(arr[2]),
            coating_level=float(arr[3]),
            hunting_level=float(arr[4]),
            oil_flow_level=float(arr[5]),
            oil_supply_temp_level=float(arr[6]),
            evacuation_level=float(arr[7]),
        )


@dataclass
class Candidate:
    """Complete candidate solution.

    Combines thermo, gear, and real-world parameters into a single
    structured object decoded from the flat decision vector.
    """

    thermo: ThermoParams
    gear: GearParams
    realworld: RealWorldParams


def decode_candidate(x: np.ndarray) -> Candidate:
    """Decode flat array to structured Candidate.

    Args:
        x: Flat decision vector of length N_TOTAL (22).

    Returns:
        Candidate with ThermoParams, GearParams, and RealWorldParams.
    """
    if len(x) != N_TOTAL:
        raise ValueError(f"Expected {N_TOTAL} (22) variables, got {len(x)}")

    thermo = ThermoParams.from_array(x[:N_THERMO])
    gear = GearParams.from_array(x[N_THERMO : N_THERMO + N_GEAR])
    realworld = RealWorldParams.from_array(x[N_THERMO + N_GEAR : N_THERMO + N_GEAR + N_REALWORLD])

    return Candidate(thermo=thermo, gear=gear, realworld=realworld)


def encode_candidate(candidate: Candidate) -> np.ndarray:
    """Encode structured Candidate to flat array.

    Args:
        candidate: Structured candidate solution.

    Returns:
        Flat decision vector of length N_TOTAL (22).
    """
    return np.concatenate(
        [
            candidate.thermo.to_array(),
            candidate.gear.to_array(),
            candidate.realworld.to_array(),
        ],
        dtype=np.float64,
    )


def bounds() -> tuple[np.ndarray, np.ndarray]:
    """Return lower and upper bounds for decision variables.

    Returns:
        (xl, xu) tuple of bound arrays, each of length N_TOTAL (22).
    """
    # ThermoParams bounds
    # compression, expansion, hr_center, hr_width, lambda_af
    thermo_lb = np.array([30.0, 60.0, 0.0, 10.0, 0.6])
    thermo_ub = np.array([90.0, 120.0, 30.0, 60.0, 1.6])

    # GearParams bounds: base_radius + 7 pitch coefficients + face_width
    gear_lb = np.array([20.0, -0.5, -0.5, -0.5, -0.5, -0.5, -0.5, -0.5, 4.0])
    gear_ub = np.array([60.0,  0.5,  0.5,  0.5,  0.5,  0.5,  0.5,  0.5, 14.0])

    # RealWorldParams bounds: 8 continuous levels [0, 1]
    # [finish, lube_mode, material, coating, hunting, oil_flow, oil_temp, evacuation]
    rw_lb = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    rw_ub = np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0])

    xl = np.concatenate([thermo_lb, gear_lb, rw_lb])
    xu = np.concatenate([thermo_ub, gear_ub, rw_ub])

    return xl, xu


def random_candidate(rng: np.random.Generator | None = None) -> np.ndarray:
    """Generate a random candidate within bounds.

    Args:
        rng: Random number generator (uses default if None).

    Returns:
        Random decision vector within bounds (length 22).
    """
    if rng is None:
        rng = np.random.default_rng()

    xl, xu = bounds()
    return rng.uniform(xl, xu)


def mid_bounds_candidate() -> np.ndarray:
    """Return candidate at midpoint of bounds (likely feasible for toy physics)."""
    xl, xu = bounds()
    return (xl + xu) / 2
