"""Structural checks for tracked OpenFOAM validation templates."""

from __future__ import annotations

import json
from pathlib import Path


def _assert_full_case_deck(template_dir: Path) -> None:
    assert (template_dir / "0").is_dir()
    assert (template_dir / "system").is_dir()
    assert (template_dir / "constant").is_dir()
    assert (template_dir / "constant" / "polyMesh").is_dir()
    assert (template_dir / "constant" / "triSurface").is_dir()
    assert (template_dir / "system" / "controlDict").is_file()
    assert (template_dir / "constant" / "thermophysicalProperties").is_file()
    assert (template_dir / "0.0003").is_dir()


def test_validation_spray_template_ships_case_deck_and_metrics_sidecar() -> None:
    template_dir = Path("openfoam_templates/validation_spray_g_iso_octane_case")
    _assert_full_case_deck(template_dir)

    metrics = json.loads((template_dir / "openfoam_metrics.json").read_text(encoding="utf-8"))
    assert "liquid_penetration_max_mm_sprayG" in metrics
    assert "droplet_smd_um_sprayG_z15mm" in metrics


def test_validation_reacting_template_ships_case_deck_and_metrics_sidecar() -> None:
    template_dir = Path("openfoam_templates/validation_reacting_iso_octane_case")
    _assert_full_case_deck(template_dir)

    metrics = json.loads((template_dir / "openfoam_metrics.json").read_text(encoding="utf-8"))
    assert "gas_temperature_K_iso_octane_reacting" in metrics
    assert "OH_molefrac_iso_octane_reacting" in metrics
