"""Smoke test for evaluation."""

import numpy as np

from larrak2.core.encoding import bounds, random_candidate
from larrak2.core.evaluator import evaluate_candidate
from larrak2.core.types import EvalContext


def test_smoke_eval_shapes():
    """Test that evaluate_candidate returns correct shapes."""
    ctx = EvalContext(rpm=3000.0, torque=200.0, fidelity=0, seed=42)
    xl, xu = bounds()

    rng = np.random.default_rng(42)

    for _ in range(10):
        x = random_candidate(rng)

        # Check bounds
        assert np.all(x >= xl), "x below lower bounds"
        assert np.all(x <= xu), "x above upper bounds"

        # Evaluate
        result = evaluate_candidate(x, ctx)

        # Check shapes
        assert result.F.shape == (3,), f"Expected F shape (3,), got {result.F.shape}"
        assert result.G.shape == (17,), f"Expected G shape (17,), got {result.G.shape}"

        # Loss should be non-negative
        loss_total = result.diag["metrics"]["loss_total"]
        assert loss_total >= 0.0, f"Loss should be non-negative, got {loss_total}"


def test_smoke_eval_finite():
    """Test that evaluate_candidate returns finite values."""
    ctx = EvalContext(rpm=3000.0, torque=200.0, fidelity=0, seed=42)

    rng = np.random.default_rng(123)

    for _ in range(10):
        x = random_candidate(rng)
        result = evaluate_candidate(x, ctx)

        # Check finite
        assert np.all(np.isfinite(result.F)), "F contains non-finite values"
        assert np.all(np.isfinite(result.G)), "G contains non-finite values"


def test_smoke_eval_diag():
    """Test that diagnostics dict is populated."""
    ctx = EvalContext(rpm=3000.0, torque=200.0, fidelity=0, seed=42)

    rng = np.random.default_rng(456)
    x = random_candidate(rng)

    result = evaluate_candidate(x, ctx)

    # Check diag structure
    assert "thermo" in result.diag
    assert "gear" in result.diag
    assert "timings" in result.diag
    assert "metrics" in result.diag
    assert "realworld" in result.diag

    # Check timings
    assert result.diag["timings"]["total_ms"] > 0

    # Check realworld diagnostics structure
    rw = result.diag["realworld"]
    assert "lambda_min" in rw
    assert "scuff_margin_C" in rw
    assert "micropitting_safety" in rw
    assert "feature_importance" in rw

    # Check gear-derived operating conditions
    gear_d = result.diag["gear"]
    assert "hertz_stress_max" in gear_d, "Missing hertz_stress_max in gear diag"
    assert "entrainment_velocity_mean" in gear_d, "Missing entrainment_velocity_mean in gear diag"
