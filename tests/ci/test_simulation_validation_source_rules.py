"""Unit tests — source-type validation rules for measured vs synthetic vs derived."""

from __future__ import annotations

import pytest

from larrak2.simulation_validation.dataset_registry import (
    DatasetRegistry,
    DatasetRegistryError,
)
from larrak2.simulation_validation.models import (
    ComparisonMode,
    SourceType,
    ValidationDatasetManifest,
    ValidationMetricSpec,
)


def _make_metric(metric_id: str = "m1", source_type: SourceType = SourceType.MEASURED):
    return ValidationMetricSpec(
        metric_id=metric_id,
        units="ms",
        comparison_mode=ComparisonMode.ABSOLUTE,
        tolerance_band=0.5,
        source_type=source_type,
    )


def _make_measured_dataset(dataset_id: str = "ds_measured", regime: str = "chemistry"):
    return ValidationDatasetManifest(
        dataset_id=dataset_id,
        regime=regime,
        fuel_family="gasoline",
        source_type=SourceType.MEASURED,
        metrics=[_make_metric()],
    )


def _make_synthetic_dataset(
    dataset_id: str = "ds_synthetic",
    regime: str = "chemistry",
    measured_anchor_ids: list[str] | None = None,
    governing_basis: str = "Arrhenius extrapolation",
):
    return ValidationDatasetManifest(
        dataset_id=dataset_id,
        regime=regime,
        fuel_family="gasoline",
        source_type=SourceType.SYNTHETIC,
        measured_anchor_ids=measured_anchor_ids or ["ds_measured"],
        governing_basis=governing_basis,
        metrics=[_make_metric(source_type=SourceType.SYNTHETIC)],
    )


class TestSourceTypeValidation:
    def test_measured_dataset_registers(self):
        reg = DatasetRegistry()
        ds = _make_measured_dataset()
        reg.register(ds)
        assert reg.get("ds_measured").source_type == SourceType.MEASURED

    def test_synthetic_without_measured_rejected(self):
        """Synthetic extension rejected when no measured dataset exists for regime."""
        reg = DatasetRegistry()
        ds = _make_synthetic_dataset()
        with pytest.raises(DatasetRegistryError, match="no measured dataset"):
            reg.register(ds)

    def test_synthetic_after_measured_accepted(self):
        reg = DatasetRegistry()
        reg.register(_make_measured_dataset())
        ds = _make_synthetic_dataset()
        reg.register(ds)
        assert len(reg.by_regime("chemistry")) == 2

    def test_synthetic_missing_anchor_provenance_rejected(self):
        """Synthetic target missing measured-anchor provenance is rejected."""
        ds = ValidationDatasetManifest(
            dataset_id="bad_synthetic",
            regime="chemistry",
            fuel_family="gasoline",
            source_type=SourceType.SYNTHETIC,
            measured_anchor_ids=[],  # missing!
            governing_basis="",  # missing!
        )
        reg = DatasetRegistry()
        reg.register(_make_measured_dataset())
        with pytest.raises(DatasetRegistryError, match="Provenance validation failed"):
            reg.register(ds)

    def test_synthetic_with_governing_basis_only_rejected(self):
        """Synthetic needs both anchors AND governing basis."""
        ds = ValidationDatasetManifest(
            dataset_id="partial_synthetic",
            regime="chemistry",
            fuel_family="gasoline",
            source_type=SourceType.SYNTHETIC,
            measured_anchor_ids=[],
            governing_basis="Some equation",
        )
        reg = DatasetRegistry()
        reg.register(_make_measured_dataset())
        with pytest.raises(DatasetRegistryError):
            reg.register(ds)

    def test_derived_constraint_registers_without_anchors(self):
        ds = ValidationDatasetManifest(
            dataset_id="derived_conservation",
            regime="full_handoff",
            fuel_family="gasoline",
            source_type=SourceType.DERIVED_CONSTRAINT,
        )
        reg = DatasetRegistry()
        reg.register(ds)
        assert reg.get("derived_conservation").source_type == SourceType.DERIVED_CONSTRAINT


class TestRegistryQueries:
    def test_by_regime(self):
        reg = DatasetRegistry()
        reg.register(_make_measured_dataset("ds1", "chemistry"))
        reg.register(_make_measured_dataset("ds2", "spray"))
        assert len(reg.by_regime("chemistry")) == 1
        assert len(reg.by_regime("spray")) == 1

    def test_by_fuel_family(self):
        reg = DatasetRegistry()
        reg.register(_make_measured_dataset("ds1"))
        assert len(reg.by_fuel_family("gasoline")) == 1
        assert len(reg.by_fuel_family("diesel")) == 0

    def test_has_measured_for_regime(self):
        reg = DatasetRegistry()
        assert reg.has_measured_for_regime("chemistry") is False
        reg.register(_make_measured_dataset())
        assert reg.has_measured_for_regime("chemistry") is True

    def test_get_missing_raises(self):
        reg = DatasetRegistry()
        with pytest.raises(KeyError):
            reg.get("nonexistent")

    def test_to_dict(self):
        reg = DatasetRegistry()
        reg.register(_make_measured_dataset())
        d = reg.to_dict()
        assert "ds_measured" in d["datasets"]
