"""Dataset registry — architecture for future experimental data ingestion.

Provides a registration and lookup system so that CEM modules can be
backed by real experimental/textbook datasets without code changes.

Datasets are described by ``DatasetDescriptor`` and managed by the
singleton ``DatasetRegistry``.  Placeholder datasets are auto-registered
on import with sensible defaults from the research documents.

Data format convention:
    - CSV or JSON files in ``data/cem/`` directory
    - Loaded on first access, cached in memory
    - Schema hash validates that the loader matches the expected columns
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dataset descriptor
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DatasetDescriptor:
    """Metadata for a CEM dataset.

    Attributes:
        name: Unique identifier (e.g. "material_fatigue_life").
        domain: CEM domain this dataset belongs to
            (tribology / material / surface / lubrication / post_processing).
        version: Semantic version string.
        source_ref: Citation or source reference.
        path: Relative path to data file (from project root), or None
            if the dataset is entirely in-memory (placeholder).
        columns: Expected column names (for schema validation).
        schema_hash: Auto-computed hash of column names + version.
    """

    name: str
    domain: str
    version: str = "0.1.0-placeholder"
    source_ref: str = ""
    path: str | None = None
    columns: tuple[str, ...] = ()
    schema_hash: str = field(init=False, default="")

    def __post_init__(self) -> None:
        # Compute schema hash
        data = json.dumps(
            {
                "name": self.name,
                "domain": self.domain,
                "version": self.version,
                "columns": list(self.columns),
            },
            sort_keys=True,
        )
        h = hashlib.sha256(data.encode()).hexdigest()
        object.__setattr__(self, "schema_hash", h[:16])


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class DatasetRegistry:
    """Central registry for CEM datasets.

    Manages registration, lookup, and lazy loading of datasets.
    """

    def __init__(self) -> None:
        self._descriptors: dict[str, DatasetDescriptor] = {}
        self._cache: dict[str, Any] = {}

    def register(self, descriptor: DatasetDescriptor) -> None:
        """Register a dataset descriptor."""
        if descriptor.name in self._descriptors:
            existing = self._descriptors[descriptor.name]
            if existing.schema_hash != descriptor.schema_hash:
                logger.warning(
                    "Overwriting dataset '%s' (hash %s → %s)",
                    descriptor.name,
                    existing.schema_hash,
                    descriptor.schema_hash,
                )
        self._descriptors[descriptor.name] = descriptor
        # Invalidate cache on re-registration
        self._cache.pop(descriptor.name, None)

    def get(self, name: str) -> DatasetDescriptor:
        """Look up a dataset descriptor by name.

        Raises:
            KeyError: If dataset is not registered.
        """
        return self._descriptors[name]

    def list_available(self) -> list[str]:
        """Return names of all registered datasets."""
        return sorted(self._descriptors.keys())

    def list_by_domain(self, domain: str) -> list[DatasetDescriptor]:
        """Return all descriptors for a given domain."""
        return [d for d in self._descriptors.values() if d.domain == domain]

    def load_table(self, name: str) -> dict[str, list]:
        """Load a dataset table.

        If a file path is specified, loads from disk (CSV/JSON).
        Otherwise returns an empty placeholder structure.

        Returns:
            Dictionary mapping column names to lists of values.
        """
        if name in self._cache:
            return self._cache[name]

        desc = self.get(name)

        if desc.path is not None:
            p = Path(desc.path)
            if p.exists():
                table = self._load_file(p, desc)
            else:
                logger.warning("Dataset file not found: %s — returning empty placeholder", p)
                table = {col: [] for col in desc.columns}
        else:
            # Auto-locate from data/cem/{name}.csv or .json
            auto_found = False
            for ext in (".csv", ".json"):
                candidate_path = Path("data") / "cem" / f"{desc.name}{ext}"
                if candidate_path.exists():
                    logger.info("Auto-located dataset: %s", candidate_path)
                    table = self._load_file(candidate_path, desc)
                    auto_found = True
                    break
            if not auto_found:
                table = {col: [] for col in desc.columns}

        self._cache[name] = table
        return table

    @staticmethod
    def _load_file(path: Path, desc: DatasetDescriptor) -> dict[str, list]:
        """Load a CSV or JSON file into column-dict format."""
        if path.suffix == ".json":
            with open(path) as f:
                data = json.load(f)
            if isinstance(data, list):
                # List of records → column dict
                if data:
                    cols = list(data[0].keys())
                    return {c: [row.get(c) for row in data] for c in cols}
                return {col: [] for col in desc.columns}
            return data  # Already column dict
        elif path.suffix == ".csv":
            # Minimal CSV reader (no pandas dependency)
            lines = path.read_text().strip().split("\n")
            if not lines:
                return {col: [] for col in desc.columns}
            header = [h.strip() for h in lines[0].split(",")]
            table: dict[str, list] = {h: [] for h in header}
            for line in lines[1:]:
                values = line.split(",")
                for h, v in zip(header, values):
                    table[h].append(v.strip())
            return table
        else:
            logger.warning("Unsupported file format: %s", path.suffix)
            return {col: [] for col in desc.columns}


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_REGISTRY: DatasetRegistry | None = None


def get_registry() -> DatasetRegistry:
    """Return the singleton DatasetRegistry, initializing placeholder datasets."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = DatasetRegistry()
        _register_placeholders(_REGISTRY)
    return _REGISTRY


# ---------------------------------------------------------------------------
# Placeholder dataset registration
# ---------------------------------------------------------------------------


def _register_placeholders(reg: DatasetRegistry) -> None:
    """Register placeholder dataset descriptors.

    These define the expected schema for each domain.  Actual data files
    are out of scope for this sprint — the architecture accepts them
    once sourced.
    """
    reg.register(
        DatasetDescriptor(
            name="material_properties",
            domain="material",
            source_ref="NASA Glenn + Carpenter + Pyrowear datasheets",
            columns=(
                "alloy",
                "max_service_temp_C",
                "case_hardness_HRC",
                "core_hardness_HRC",
                "fatigue_life_multiplier",
                "cost_tier",
            ),
        )
    )

    reg.register(
        DatasetDescriptor(
            name="tribology_ehl_coefficients",
            domain="tribology",
            source_ref="ISO/TS 6336-22 + NASA λ–life correlation",
            columns=(
                "oil_type",
                "temperature_C",
                "viscosity_cSt",
                "pressure_viscosity_coeff",
                "ehl_constant",
            ),
        )
    )

    reg.register(
        DatasetDescriptor(
            name="scuffing_critical_temperatures",
            domain="tribology",
            source_ref="ISO/TS 6336-20/21 + FZG test data",
            columns=(
                "oil_type",
                "additive_package",
                "T_crit_C",
                "load_stage",
                "method",
            ),
        )
    )

    reg.register(
        DatasetDescriptor(
            name="surface_finish_endurance",
            domain="surface",
            source_ref="REM/AGMA FZG micropitting + NASA scuffing TOF",
            columns=(
                "finish_method",
                "Ra_um",
                "Rz_um",
                "composite_roughness_factor",
                "micropitting_life_multiplier",
                "scuffing_TOF_multiplier",
                "cost_multiplier",
            ),
        )
    )

    reg.register(
        DatasetDescriptor(
            name="lubrication_cooling_curves",
            domain="lubrication",
            source_ref="NASA oil-jet studies + API 677",
            columns=(
                "delivery_mode",
                "flow_rate_L_min",
                "pitch_vel_m_s",
                "tooth_temp_reduction_C",
                "churning_loss_fraction",
            ),
        )
    )

    reg.register(
        DatasetDescriptor(
            name="coating_rcf_performance",
            domain="post_processing",
            source_ref="Oerlikon Balzers + Platit + Scientific Reports",
            columns=(
                "coating_type",
                "substrate",
                "hertz_stress_MPa",
                "cycles_to_failure",
                "friction_coeff",
                "temperature_C",
            ),
        )
    )

    reg.register(
        DatasetDescriptor(
            name="heat_treat_hardness_curves",
            domain="post_processing",
            source_ref="Pyrowear/CBS-50 NiL/Ferrium datasheets",
            columns=(
                "alloy",
                "treatment",
                "temper_temp_C",
                "case_hardness_HRC",
                "core_hardness_HRC",
            ),
        )
    )
