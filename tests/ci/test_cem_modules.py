"""Tests for CEM (Computational Engineering Model) domain modules."""

import numpy as np
import pytest

from larrak2.cem.evaluator import CEMEvalParams, CEMResult, evaluate_cem
from larrak2.cem.lubrication import (
    LubricationMode,
    LubricationParams,
    cooling_effectiveness,
    effective_viscosity,
    mode_from_level,
)
from larrak2.cem.material_db import (
    MATERIAL_DB,
    MaterialClass,
    MaterialProperties,
    get_material,
    list_materials,
)
from larrak2.cem.post_processing import (
    CoatingType,
    HeatTreatment,
    apply_heat_treat_modifiers,
    coating_from_level,
    get_coating,
)
from larrak2.cem.registry import get_registry
from larrak2.cem.surface_finish import (
    FINISH_PROPERTIES,
    SurfaceFinishTier,
    effective_composite_roughness,
    tier_from_level,
)
from larrak2.cem.tribology import (
    LubeRegime,
    TribologyParams,
    classify_regime,
    compute_lambda,
    compute_micropitting_safety,
    compute_scuff_margin,
    compute_scuff_margins,
    evaluate_tribology,
)


class TestMaterialDB:
    """Test material database lookups."""

    def test_all_materials_present(self):
        """All enum values should have DB entries."""
        for mc in MaterialClass:
            props = get_material(mc)
            assert isinstance(props, MaterialProperties)
            assert props.max_service_temp_C > 0

    def test_list_materials(self):
        """list_materials should return all classes."""
        mats = list_materials()
        assert len(mats) == len(MaterialClass)

    def test_temp_ordering(self):
        """Hot-hard alloys should have higher service temp than 9310."""
        base = get_material(MaterialClass.AISI_9310)
        hot = get_material(MaterialClass.M50_NIL)
        assert hot.max_service_temp_C > base.max_service_temp_C

    def test_invalid_lookup_raises(self):
        """Invalid key should raise KeyError."""
        with pytest.raises(KeyError):
            MATERIAL_DB["nonexistent"]  # type: ignore


class TestTribology:
    """Test tribology calculations."""

    def test_lambda_positive(self):
        """λ should be positive for reasonable inputs."""
        params = TribologyParams()
        lam = compute_lambda(params)
        assert lam > 0

    def test_lambda_finite(self):
        """λ should be finite for all reasonable inputs."""
        params = TribologyParams(
            hertz_stress_MPa=2000.0,
            sliding_velocity_m_s=10.0,
            entrainment_velocity_m_s=30.0,
            oil_viscosity_cSt=5.0,
            composite_roughness_um=0.6,
            bulk_temp_C=250.0,
        )
        lam = compute_lambda(params)
        assert np.isfinite(lam)
        assert lam >= 0

    def test_lambda_decreases_with_roughness_and_stress(self):
        """Lambda should worsen with roughness/stress increases."""
        base = TribologyParams(
            hertz_stress_MPa=1000.0,
            composite_roughness_um=0.20,
            oil_viscosity_cSt=15.0,
            entrainment_velocity_m_s=15.0,
        )
        rougher = TribologyParams(
            hertz_stress_MPa=1000.0,
            composite_roughness_um=0.60,
            oil_viscosity_cSt=15.0,
            entrainment_velocity_m_s=15.0,
        )
        higher_stress = TribologyParams(
            hertz_stress_MPa=1800.0,
            composite_roughness_um=0.20,
            oil_viscosity_cSt=15.0,
            entrainment_velocity_m_s=15.0,
        )
        lam_base = compute_lambda(base, validation_mode="strict")
        lam_rougher = compute_lambda(rougher, validation_mode="strict")
        lam_stress = compute_lambda(higher_stress, validation_mode="strict")
        assert lam_rougher < lam_base
        assert lam_stress < lam_base

    def test_lambda_zero_roughness(self):
        """Zero roughness should give maximum λ (capped)."""
        params = TribologyParams(composite_roughness_um=0.0)
        lam = compute_lambda(params)
        assert lam == 10.0  # Cap value

    def test_scuff_margin_finite(self):
        """Scuff margin should be finite."""
        params = TribologyParams()
        margin = compute_scuff_margin(params)
        assert np.isfinite(margin)

    def test_micropitting_safety(self):
        """S_λ should be positive for positive λ."""
        sf = compute_micropitting_safety(1.5)
        assert sf > 0
        # λ = 1.5 and default λ_perm = 0.3 → S_λ = 5.0
        assert sf == pytest.approx(5.0)

    def test_micropitting_crosses_unity(self):
        """Micropitting factor should cross at S_lambda = 1."""
        assert compute_micropitting_safety(0.29, lambda_perm=0.30) < 1.0
        assert compute_micropitting_safety(0.30, lambda_perm=0.30) == pytest.approx(1.0)
        assert compute_micropitting_safety(0.31, lambda_perm=0.30) > 1.0

    def test_scuff_margin_worsens_with_load_and_sliding(self):
        """Scuff margin should decrease when load/sliding rise."""
        mild = TribologyParams(hertz_stress_MPa=900.0, sliding_velocity_m_s=2.0)
        severe = TribologyParams(hertz_stress_MPa=1700.0, sliding_velocity_m_s=9.0)
        m_mild = compute_scuff_margin(mild, scuff_method="auto", validation_mode="strict")
        m_severe = compute_scuff_margin(severe, scuff_method="auto", validation_mode="strict")
        assert m_severe < m_mild

    def test_scuff_auto_matches_worst_case_method(self):
        """Auto scuff policy should equal min(flash, integral)."""
        metrics = compute_scuff_margins(
            TribologyParams(),
            scuff_method="auto",
            validation_mode="strict",
        )
        assert metrics["scuff_margin_C"] == pytest.approx(
            min(metrics["scuff_margin_flash_C"], metrics["scuff_margin_integral_C"])
        )

    def test_strict_lookup_missing_row_raises(self):
        """Strict mode should fail on unresolved lookup keys."""
        with pytest.raises(ValueError):
            evaluate_tribology(
                TribologyParams(oil_type="unknown_oil"),
                scuff_method="auto",
                validation_mode="strict",
            )

    @pytest.mark.parametrize("mode", ["warn", "off"])
    def test_warn_off_lookup_degrades_with_status(self, mode: str):
        """Warn/off modes should continue with explicit degraded status."""
        result = evaluate_tribology(
            TribologyParams(oil_type="unknown_oil"),
            scuff_method="auto",
            validation_mode=mode,
        )
        assert np.isfinite(result.lambda_min)
        assert np.isfinite(result.scuff_margin_C)
        assert result.tribology_data_status.startswith("degraded")
        assert len(result.tribology_data_messages) > 0

    def test_regime_classification(self):
        """Regime classification boundaries."""
        assert classify_regime(0.2) == LubeRegime.BOUNDARY
        assert classify_regime(0.7) == LubeRegime.MIXED
        assert classify_regime(1.5) == LubeRegime.FULL_EHL


class TestSurfaceFinish:
    """Test surface finish tiers."""

    def test_all_tiers_have_properties(self):
        """All tiers should have entries in the property table."""
        for tier in SurfaceFinishTier:
            assert tier in FINISH_PROPERTIES

    def test_roughness_ordering(self):
        """Superfinished should have lower roughness than as-ground."""
        r_rough = effective_composite_roughness(SurfaceFinishTier.AS_GROUND)
        r_smooth = effective_composite_roughness(SurfaceFinishTier.SUPERFINISHED)
        assert r_smooth < r_rough

    def test_tier_from_level(self):
        """Level mapping should produce correct tiers."""
        assert tier_from_level(0.0) == SurfaceFinishTier.AS_GROUND
        assert tier_from_level(0.5) == SurfaceFinishTier.FINE_GROUND
        assert tier_from_level(1.0) == SurfaceFinishTier.SUPERFINISHED


class TestLubrication:
    """Test lubrication models."""

    def test_viscosity_positive(self):
        """Viscosity should be positive at reasonable temperatures."""
        params = LubricationParams()
        visc = effective_viscosity(params, 150.0)
        assert visc > 0

    def test_cooling_bounds(self):
        """Cooling effectiveness should be in [0, 1]."""
        for mode in LubricationMode:
            params = LubricationParams(mode=mode)
            cool = cooling_effectiveness(params, 20.0)
            assert 0.0 <= cool <= 1.0

    def test_jet_better_than_bath(self):
        """Jet should cool better than splash at high speed."""
        p_bath = LubricationParams(mode=LubricationMode.SPLASH_BATH)
        p_jet = LubricationParams(mode=LubricationMode.PRESSURIZED_JET)
        c_bath = cooling_effectiveness(p_bath, 30.0)
        c_jet = cooling_effectiveness(p_jet, 30.0)
        assert c_jet > c_bath

    def test_mode_from_level(self):
        """Level mapping should produce correct modes."""
        assert mode_from_level(0.0) == LubricationMode.DRY
        assert mode_from_level(1.0) == LubricationMode.PHASE_GATED_JET


class TestPostProcessing:
    """Test coating and heat treatment modifiers."""

    def test_all_coatings_present(self):
        """All coating types should have DB entries."""
        for ct in CoatingType:
            props = get_coating(ct)
            assert props.name

    def test_coating_reduces_friction(self):
        """Coatings should reduce friction (except NONE)."""
        for ct in CoatingType:
            props = get_coating(ct)
            if ct != CoatingType.NONE:
                assert props.friction_coeff_reduction > 0

    def test_heat_treat_modifiers(self):
        """Heat treatment should modify fatigue life."""
        base = 1.0
        hot_hard = apply_heat_treat_modifiers(base, HeatTreatment.CARBURIZED_HOT_HARD)
        assert hot_hard > base  # Hot-hard should improve life

    def test_coating_from_level(self):
        """Level mapping should produce correct coating types."""
        assert coating_from_level(0.0) == CoatingType.NONE
        assert coating_from_level(1.0) == CoatingType.W_DLC_CRN


class TestRegistry:
    """Test dataset registry."""

    def test_singleton(self):
        """get_registry should return a singleton."""
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2

    def test_registered_datasets_exist(self):
        """Expected CEM datasets should be registered."""
        reg = get_registry()
        available = reg.list_available()
        assert "tribology_ehl_coefficients" in available
        assert "scuffing_critical_temperatures" in available
        assert "micropitting_lambda_perm" in available
        assert "fzg_step_load_map" in available

    def test_lookup_by_domain(self):
        """Should be able to filter by domain."""
        reg = get_registry()
        trib = reg.list_by_domain("tribology")
        assert len(trib) >= 4

    def test_load_empty_table(self):
        """Loading placeholder (no file) should return empty column dict."""
        reg = get_registry()
        table = reg.load_table("material_properties")
        assert isinstance(table, dict)
        assert "alloy" in table

    def test_tribology_tables_required_in_strict_mode(self):
        """Required tribology tables should be non-empty in strict mode."""
        reg = get_registry()
        table_names = [
            "tribology_ehl_coefficients",
            "scuffing_critical_temperatures",
            "micropitting_lambda_perm",
            "fzg_step_load_map",
        ]
        key_columns = {
            "tribology_ehl_coefficients": ("oil_type", "finish_tier", "ehl_constant"),
            "scuffing_critical_temperatures": ("oil_type", "additive_package", "method", "T_crit_C"),
            "micropitting_lambda_perm": ("oil_type", "finish_tier", "lambda_perm"),
            "fzg_step_load_map": ("test_standard", "test_method", "load_stage", "T_crit_C"),
        }
        for name in table_names:
            table, messages = reg.load_required_table(
                name,
                validation_mode="strict",
                key_columns=key_columns[name],
            )
            assert not messages
            assert table
            n_rows = max((len(v) for v in table.values()), default=0)
            assert n_rows > 0

    def test_tribology_schema_has_units_provenance_version(self):
        """Tribology dataset descriptors should require traceability columns."""
        reg = get_registry()
        datasets = [
            "tribology_ehl_coefficients",
            "scuffing_critical_temperatures",
            "micropitting_lambda_perm",
            "fzg_step_load_map",
        ]
        for name in datasets:
            desc = reg.get(name)
            assert "provenance" in desc.columns
            assert "version" in desc.columns
            assert any(col.startswith("unit") for col in desc.columns)


class TestCEMEvaluator:
    """Test full CEM evaluation."""

    def test_evaluate_cem_default(self):
        """Default params should produce a complete CEMResult."""
        result = evaluate_cem(CEMEvalParams())
        assert isinstance(result, CEMResult)
        assert np.isfinite(result.lambda_min)
        assert np.isfinite(result.scuff_margin_C)
        assert np.isfinite(result.micropitting_safety)
        assert np.isfinite(result.total_cost_index)
        assert result.lube_regime in {"boundary", "mixed", "full_ehl"}

    def test_evaluate_cem_ranking(self):
        """Feature importance ranking should be present."""
        result = evaluate_cem(CEMEvalParams())
        assert len(result.recommendation_ranking) > 0

    def test_evaluate_cem_details(self):
        """Details dict should contain all domain sections."""
        result = evaluate_cem(CEMEvalParams())
        for key in ["material", "surface", "lubrication", "coating", "heat_treatment", "tribology"]:
            assert key in result.details, f"Missing detail section: {key}"
