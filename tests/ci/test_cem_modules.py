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

    def test_placeholders_registered(self):
        """Placeholder datasets should be auto-registered."""
        reg = get_registry()
        available = reg.list_available()
        assert len(available) >= 7  # We registered 7 placeholder datasets

    def test_lookup_by_domain(self):
        """Should be able to filter by domain."""
        reg = get_registry()
        trib = reg.list_by_domain("tribology")
        assert len(trib) >= 2  # ehl_coefficients + scuffing_critical_temps

    def test_load_empty_table(self):
        """Loading placeholder (no file) should return empty column dict."""
        reg = get_registry()
        table = reg.load_table("material_properties")
        assert isinstance(table, dict)
        assert "alloy" in table


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
