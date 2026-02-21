"""Tests for phase-resolved tribology evaluation."""

import numpy as np
import pytest

from larrak2.realworld.surrogates import (
    DEFAULT_REALWORLD_PARAMS,
    evaluate_realworld_phase_resolved,
    evaluate_realworld_surrogates,
)


class TestPhaseResolvedBasics:
    """Test phase-resolved evaluation produces valid results."""

    def _make_flat_profiles(self, n: int = 360, value: float = 1200.0):
        """Create flat (constant) profiles for testing."""
        return {
            "hertz_stress_profile": np.full(n, value),
            "sliding_velocity_profile": np.full(n, 5.0),
            "entrainment_velocity_profile": np.full(n, 15.0),
            "fn_profile": np.full(n, 100.0),
        }

    def test_flat_profiles_finite(self):
        """Flat profiles should produce finite results."""
        profs = self._make_flat_profiles()
        result = evaluate_realworld_phase_resolved(DEFAULT_REALWORLD_PARAMS, **profs)
        assert np.isfinite(result.lambda_min)
        assert np.isfinite(result.scuff_margin_C)
        assert np.isfinite(result.micropitting_safety)

    def test_worst_phase_in_range(self):
        """Worst phase angle should be in [0, 360)."""
        profs = self._make_flat_profiles()
        result = evaluate_realworld_phase_resolved(DEFAULT_REALWORLD_PARAMS, **profs)
        assert 0.0 <= result.worst_phase_deg < 360.0

    def test_n_bins_analyzed_positive(self):
        """At least some bins should be analyzed."""
        profs = self._make_flat_profiles()
        result = evaluate_realworld_phase_resolved(DEFAULT_REALWORLD_PARAMS, **profs)
        assert result.n_bins_analyzed > 0

    def test_lambda_profile_shape(self):
        """Lambda profile should match input shape."""
        n = 360
        profs = self._make_flat_profiles(n)
        result = evaluate_realworld_phase_resolved(DEFAULT_REALWORLD_PARAMS, **profs)
        assert result.lambda_profile.shape == (n,)


class TestPhaseResolvedForceGating:
    """Test force-gating: only high-load bins should be analyzed."""

    def test_fewer_bins_than_total(self):
        """With varying force, not all bins should be analyzed."""
        n = 360
        # Create a force profile with a clear peak region
        theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
        fn = 50.0 + 150.0 * np.abs(np.sin(theta))  # peak at π/2 and 3π/2

        result = evaluate_realworld_phase_resolved(
            DEFAULT_REALWORLD_PARAMS,
            hertz_stress_profile=np.full(n, 1200.0),
            sliding_velocity_profile=np.full(n, 5.0),
            entrainment_velocity_profile=np.full(n, 15.0),
            fn_profile=fn,
        )

        # Not all 360 bins should be analyzed (force has valleys)
        assert result.n_bins_analyzed < n, (
            f"Expected fewer than {n} bins analyzed, got {result.n_bins_analyzed}"
        )
        assert result.n_bins_analyzed > 0

    def test_non_analyzed_bins_nan(self):
        """Bins not analyzed should have NaN in lambda_profile."""
        n = 360
        theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
        fn = 50.0 + 150.0 * np.abs(np.sin(theta))

        result = evaluate_realworld_phase_resolved(
            DEFAULT_REALWORLD_PARAMS,
            hertz_stress_profile=np.full(n, 1200.0),
            sliding_velocity_profile=np.full(n, 5.0),
            entrainment_velocity_profile=np.full(n, 15.0),
            fn_profile=fn,
        )

        n_nan = int(np.sum(np.isnan(result.lambda_profile)))
        n_valid = int(np.sum(~np.isnan(result.lambda_profile)))
        assert n_valid == result.n_bins_analyzed
        assert n_nan == n - result.n_bins_analyzed


class TestPhaseResolvedVsScalar:
    """Test that phase-resolved gives consistent results vs scalar."""

    def test_flat_matches_scalar(self):
        """Flat profiles should give same λ as scalar evaluation."""
        n = 360
        hertz = 1200.0
        sliding = 5.0
        entrainment = 15.0

        # Scalar evaluation
        scalar_result = evaluate_realworld_surrogates(
            DEFAULT_REALWORLD_PARAMS,
            hertz_stress_MPa=hertz,
            sliding_velocity_m_s=sliding,
            entrainment_velocity_m_s=entrainment,
        )

        # Phase-resolved with flat profiles
        phase_result = evaluate_realworld_phase_resolved(
            DEFAULT_REALWORLD_PARAMS,
            hertz_stress_profile=np.full(n, hertz),
            sliding_velocity_profile=np.full(n, sliding),
            entrainment_velocity_profile=np.full(n, entrainment),
            fn_profile=np.full(n, 100.0),  # Uniform force → all bins analyzed
        )

        assert phase_result.lambda_min == pytest.approx(scalar_result.lambda_min, rel=0.01), (
            f"Flat-profile phase-resolved λ ({phase_result.lambda_min:.4f}) "
            f"should match scalar λ ({scalar_result.lambda_min:.4f})"
        )

    def test_varying_profile_worse_than_mean(self):
        """Varying profiles should give worse (lower) λ than mean values."""
        n = 360
        # Create profiles with variation
        theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
        hertz_prof = 1200.0 + 400.0 * np.sin(theta)  # 800–1600 MPa
        sliding_prof = 5.0 + 3.0 * np.cos(theta)  # 2–8 m/s
        entrainment_prof = np.full(n, 15.0)
        fn_prof = np.full(n, 100.0)  # Uniform force → all bins analyzed

        # Phase-resolved with varying profiles
        phase_result = evaluate_realworld_phase_resolved(
            DEFAULT_REALWORLD_PARAMS,
            hertz_stress_profile=hertz_prof,
            sliding_velocity_profile=sliding_prof,
            entrainment_velocity_profile=entrainment_prof,
            fn_profile=fn_prof,
        )

        # Scalar with mean values
        scalar_result = evaluate_realworld_surrogates(
            DEFAULT_REALWORLD_PARAMS,
            hertz_stress_MPa=float(np.mean(hertz_prof)),
            sliding_velocity_m_s=float(np.mean(sliding_prof)),
            entrainment_velocity_m_s=15.0,
        )

        # Worst-case phase should be worse (lower λ) than mean evaluation
        assert phase_result.lambda_min <= scalar_result.lambda_min, (
            f"Phase-resolved worst-case λ ({phase_result.lambda_min:.4f}) "
            f"should be ≤ mean-value λ ({scalar_result.lambda_min:.4f})"
        )
