"""Life-damage calibration and strict route-resolution checks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from larrak2.realworld import life_damage


def test_sigma_ref_resolves_from_calibration_file() -> None:
    life_damage.invalidate_limit_stress_cache()
    ref = life_damage.get_sigma_ref_for_route("AISI_9310", strict_data=True)
    assert ref == pytest.approx(life_damage._SIGMA_REF_MPA)


def test_sigma_ref_missing_route_fails_when_strict(monkeypatch) -> None:
    life_damage.invalidate_limit_stress_cache()
    monkeypatch.setattr(
        life_damage,
        "_load_limit_stress_table",
        lambda strict_data=None: {"AISI_9310": 1500.0},
    )
    with pytest.raises(ValueError, match="missing"):
        life_damage.get_sigma_ref_for_route("NON_EXISTENT", strict_data=True)


def test_missing_calibration_file_fails() -> None:
    life_damage.invalidate_limit_stress_cache()
    with pytest.raises(FileNotFoundError):
        life_damage._load_calibration(path=Path("data/cem/does_not_exist_life_damage.json"))


def test_calibration_rejects_nonfinite_or_invalid_bounds(tmp_path: Path) -> None:
    life_damage.invalidate_limit_stress_cache()
    bad_path = tmp_path / "bad_calibration.json"
    bad_path.write_text(
        json.dumps(
            {
                "version": "bad",
                "baseline_route_id": "AISI_9310",
                "sigma_ref_mpa": 1500.0,
                "stress_exponent": 0.0,
                "lambda_exponent": 2.0,
                "cleanliness_scale_min": 1.2,
                "cleanliness_scale_max": 0.8,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        life_damage._load_calibration(path=bad_path)


def test_route_cleanliness_missing_route_strict_fails() -> None:
    life_damage.invalidate_limit_stress_cache()
    with pytest.raises(ValueError, match="missing from route_metadata"):
        life_damage.get_route_cleanliness_proxy("NON_EXISTENT", strict_data=True)


def test_route_cleanliness_missing_route_off_degrades() -> None:
    life_damage.invalidate_limit_stress_cache()
    clean, status, messages = life_damage.get_route_cleanliness_proxy(
        "NON_EXISTENT",
        strict_data=False,
        validation_mode="off",
    )
    assert clean == pytest.approx(0.5)
    assert status == "degraded_off"
    assert len(messages) >= 1


def test_scalar_proxy_damage_is_deterministic_and_nonzero_when_loaded() -> None:
    life_damage.invalidate_limit_stress_cache()
    out1 = life_damage.compute_life_damage_scalar_proxy_10k(
        hertz_stress_MPa=1300.0,
        lambda_min=0.9,
        rpm=3000.0,
        hunting_level=0.6,
        sigma_ref_MPa=1500.0,
    )
    out2 = life_damage.compute_life_damage_scalar_proxy_10k(
        hertz_stress_MPa=1300.0,
        lambda_min=0.9,
        rpm=3000.0,
        hunting_level=0.6,
        sigma_ref_MPa=1500.0,
    )
    assert out1 == out2
    assert float(out1["D_total"]) > 0.0
    assert int(out1["N_set"]) >= 1
