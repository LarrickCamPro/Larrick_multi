from __future__ import annotations

import json
import textwrap
from pathlib import Path

import numpy as np

from larrak2.simulation_validation.runtime_chemistry_table import (
    _local_rbf_interpolate,
    build_runtime_chemistry_table_from_spec,
)


class _FakeGas:
    def __init__(self):
        self.species_names = ["IC8H18", "O2", "N2", "CO2", "H2O"]
        self.molecular_weights = np.array([114.23, 31.998, 28.0134, 44.01, 18.01528], dtype=float)
        self._tp = (300.0, 101325.0)
        self._y = {name: 0.0 for name in self.species_names}

    @property
    def TPY(self):  # pragma: no cover - convenience only
        return self._tp[0], self._tp[1], self._y

    @TPY.setter
    def TPY(self, value):
        temperature, pressure, mass_fractions = value
        self._tp = (float(temperature), float(pressure))
        self._y = {name: float(mass_fractions.get(name, 0.0)) for name in self.species_names}

    @property
    def X(self):
        return np.array([self._y[name] for name in self.species_names], dtype=float)

    @property
    def net_production_rates(self):
        temperature, pressure = self._tp
        fuel = self._y["IC8H18"]
        oxidizer = self._y["O2"]
        products = self._y["CO2"] + self._y["H2O"]
        state_factor = (temperature / 1000.0) * (pressure / 1.0e6)
        return np.array(
            [
                -0.5 * fuel * state_factor,
                -1.0 * oxidizer * state_factor,
                0.0,
                0.35 * (fuel + products + 0.01) * state_factor,
                0.15 * (fuel + products + 0.01) * state_factor,
            ],
            dtype=float,
        )

    @property
    def net_production_rates_ddT(self):
        temperature, pressure = self._tp
        factor = pressure / 1.0e9
        fuel = self._y["IC8H18"]
        oxidizer = self._y["O2"]
        products = self._y["CO2"] + self._y["H2O"]
        return np.array(
            [
                -0.5 * fuel * factor,
                -1.0 * oxidizer * factor,
                0.0,
                0.35 * (fuel + products + 0.01) * factor,
                0.15 * (fuel + products + 0.01) * factor,
            ],
            dtype=float,
        )

    @property
    def net_production_rates_ddX(self):
        temperature, pressure = self._tp
        factor = (temperature / 1000.0) * (pressure / 1.0e6)
        mat = np.zeros((5, 5), dtype=float)
        mat[0, 0] = -0.5 * factor
        mat[1, 1] = -1.0 * factor
        mat[3, 0] = 0.35 * factor
        mat[3, 3] = 0.35 * factor
        mat[3, 4] = 0.35 * factor
        mat[4, 0] = 0.15 * factor
        mat[4, 3] = 0.15 * factor
        mat[4, 4] = 0.15 * factor
        return mat

    @property
    def partial_molar_enthalpies(self):
        return np.array([-2.0e8, -1.0e8, 0.0, -3.5e8, -2.5e8], dtype=float)


def _write_scalar_field(path: Path, values: list[float]) -> None:
    body = "\n".join(str(value) for value in values)
    path.write_text(
        textwrap.dedent(
            f"""\
            FoamFile
            {{
                version 2.0;
                format ascii;
                class volScalarField;
                location "{path.parent.name}";
                object {path.name};
            }}

            dimensions [0 0 0 0 0 0 0];
            internalField nonuniform List<scalar>
            {len(values)}
            (
            {body}
            )
            ;

            boundaryField
            {{
            }}
            """
        ),
        encoding="utf-8",
    )


def test_local_rbf_interpolation_reproduces_anchor_points() -> None:
    sample_states = np.array(
        [
            [900.0, 8.0e5, 0.01],
            [950.0, 9.0e5, 0.02],
            [1000.0, 1.0e6, 0.03],
        ],
        dtype=float,
    )
    sample_values = np.array([[1.0, 2.0], [2.0, 4.0], [3.0, 6.0]], dtype=float)
    scales = np.array([100.0, 1.0e5, 0.01], dtype=float)

    value = _local_rbf_interpolate(
        sample_states=sample_states,
        sample_values=sample_values,
        query_state=np.array([950.0, 9.0e5, 0.02], dtype=float),
        state_scales=scales,
        neighbor_count=3,
        epsilon=1.0,
    )

    assert np.allclose(value, sample_values[1])


def test_build_runtime_chemistry_table_from_spec_writes_binary_and_manifest(
    tmp_path: Path,
    monkeypatch,
) -> None:
    package_dir = tmp_path / "chem323_reduced"
    package_dir.mkdir(parents=True)
    yaml_path = tmp_path / "chem323_reduced.yaml"
    yaml_path.write_text("phases:\n- name: gas\n", encoding="utf-8")
    (package_dir / "package_manifest.json").write_text(
        json.dumps(
            {
                "package_id": "chem323_reduced_v2512",
                "package_hash": "chem323-hash",
                "generated_yaml_path": str(yaml_path),
            }
        ),
        encoding="utf-8",
    )

    class _FakeCanteraModule:
        def Solution(self, path: str, transport_model=None):
            assert path.endswith(".yaml")
            assert transport_model is None
            return _FakeGas()

    monkeypatch.setattr(
        "larrak2.simulation_validation.runtime_chemistry_table._load_cantera",
        lambda: _FakeCanteraModule(),
    )

    output_dir = tmp_path / "runtime_table"
    manifest = build_runtime_chemistry_table_from_spec(
        {
            "table_id": "chem323_engine_ignition_v2",
            "package_dir": str(package_dir),
            "output_dir": str(output_dir),
            "state_species": ["IC8H18", "O2", "CO2", "H2O"],
            "state_axes": {
                "Temperature": [900.0, 1100.0],
                "Pressure": [8.5e5, 9.5e5],
                "IC8H18": [0.005, 0.015],
                "O2": [0.03, 0.06],
                "CO2": [0.0, 0.03],
                "H2O": [0.0, 0.03],
            },
            "adaptive_sampling": {
                "sparse_level": 1,
                "candidate_sparse_level": 2,
                "refinement_rounds": 1,
                "batch_size": 4,
                "max_samples": 24,
                "source_tolerance": 0.0,
                "jacobian_tolerance": 0.0,
                "rbf_neighbor_count": 4,
                "rbf_epsilon": 1.0,
                "lookup_cache_quantization": 0.01,
            },
            "interpolation_method": "local_rbf",
            "fallback_policy": "fullReducedKinetics",
            "jacobian_mode": "full_species",
            "jacobian_storage": "csr",
            "max_untracked_mass_fraction": 0.015,
        },
        refresh=True,
        repo_root=tmp_path,
    )

    assert manifest["table_id"] == "chem323_engine_ignition_v2"
    assert manifest["package_id"] == "chem323_reduced_v2512"
    assert manifest["species_count"] == 5
    assert manifest["interpolation_method"] == "local_rbf"
    assert manifest["fallback_policy"] == "fullReducedKinetics"
    assert manifest["jacobian_mode"] == "full_species"
    assert manifest["jacobian_storage"] == "csr"
    assert manifest["transformed_state_variables"] == ["Pressure"]
    assert manifest["state_transform_floors"]["Pressure"] == 1.0
    assert Path(manifest["files"]["runtimeChemistryTable"]).is_file()
    assert Path(manifest["files"]["runtime_chemistry_table_data"]).is_file()
    assert Path(manifest["files"]["runtime_chemistry_jacobian_csr"]).is_file()
    assert manifest["jacobian"]["row_count"] == 5
    assert manifest["jacobian"]["column_count"] == 6
    assert manifest["jacobian"]["column_variables"] == [
        "Temperature",
        "IC8H18",
        "O2",
        "N2",
        "CO2",
        "H2O",
    ]
    assert manifest["jacobian"]["species_basis"] == "mass_fraction"
    assert manifest["adaptive_sampling"]["seed_point_count"] > 0

    dictionary_text = (output_dir / "runtimeChemistryTable").read_text(encoding="utf-8")
    assert "interpolation            local_rbf;" in dictionary_text
    assert "jacobianMode            full_species;" in dictionary_text
    assert "jacobianStorage         csr;" in dictionary_text
    assert "transformedStateVariables" in dictionary_text
    assert "stateTransformFloors" in dictionary_text
    assert "sampleStates" in dictionary_text
    assert "diagSourceJacobian" in dictionary_text
    assert "temperatureSourceSensitivity" in dictionary_text

    data = np.load(output_dir / "runtime_chemistry_table_data.npz")
    assert data["sample_states"].shape[0] == manifest["table_point_count"]
    assert data["source_terms"].shape[1] == manifest["species_count"]
    assert data["diag_source_jacobian"].shape == data["source_terms"].shape

    jacobian = np.load(output_dir / "runtime_chemistry_jacobian_csr.npz")
    assert jacobian["jacobian_shape"].tolist() == [5, 6]
    assert jacobian["csr_row_ptr"].shape[0] == manifest["table_point_count"]
    assert jacobian["sample_csr_offsets"].shape[0] == manifest["table_point_count"] + 1

    manifest_on_disk = json.loads(
        (output_dir / "runtime_chemistry_table_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest_on_disk["generated_file_hashes"] == manifest["generated_file_hashes"]


def test_seed_corridor_axes_infer_mass_fraction_envelope_from_handoff_and_fields(
    tmp_path: Path,
    monkeypatch,
) -> None:
    package_dir = tmp_path / "chem323_reduced"
    package_dir.mkdir(parents=True)
    yaml_path = tmp_path / "chem323_reduced.yaml"
    yaml_path.write_text("phases:\n- name: gas\n", encoding="utf-8")
    (package_dir / "package_manifest.json").write_text(
        json.dumps(
            {
                "package_id": "chem323_reduced_v2512",
                "package_hash": "chem323-hash",
                "generated_yaml_path": str(yaml_path),
            }
        ),
        encoding="utf-8",
    )

    handoff_path = tmp_path / "handoff.json"
    handoff_path.write_text(
        json.dumps(
            {
                "handoff_bundle": {
                    "temperature_K": 1115.0,
                    "pressure_Pa": 9.1e5,
                    "species_mole_fractions": {
                        "IC8H18": 0.011,
                        "O2": 0.205,
                        "N2": 0.77,
                        "CO2": 0.009,
                        "H2O": 0.005,
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    case_dir = tmp_path / "engine_case"
    time_dir = case_dir / "0.0001"
    time_dir.mkdir(parents=True)
    (case_dir / "logSummary.0.0001.dat").write_text(
        "\n".join(
            [
                "# crankAngleDeg meanPressurePa meanTemperatureK meanVelocityMagnitude",
                "-6.99 1.1e6 1110.0 35.0",
            ]
        ),
        encoding="utf-8",
    )
    _write_scalar_field(time_dir / "T", [980.0, 1110.0, 1285.0, 300.0])
    _write_scalar_field(time_dir / "p", [8.5e5, 1.1e6, 2.4e6, 3.0e4])
    _write_scalar_field(time_dir / "IC8H18", [0.0415, 0.0422, 0.0428, 0.0420])
    _write_scalar_field(time_dir / "O2", [0.218, 0.219, 0.221, 0.2195])
    _write_scalar_field(time_dir / "CO2", [0.012, 0.013, 0.014, 0.0132])
    _write_scalar_field(time_dir / "H2O", [0.0024, 0.0028, 0.0031, 0.0029])
    _write_scalar_field(time_dir / "OH", [1.0e-12, 1.0e-8, 2.0e-8, 1.0e-14])
    _write_scalar_field(time_dir / "CO", [1.0e-14, 2.0e-10, 3.0e-10, 1.0e-13])
    _write_scalar_field(time_dir / "HO2", [1.0e-13, 2.0e-7, 8.0e-7, 1.0e-12])
    _write_scalar_field(time_dir / "H2", [1.0e-14, 2.0e-8, 4.0e-8, 1.0e-13])
    _write_scalar_field(time_dir / "CH2O", [1.0e-14, 4.0e-9, 1.2e-8, 1.0e-13])

    class _FakeCanteraModule:
        def Solution(self, path: str, transport_model=None):
            assert path.endswith(".yaml")
            assert transport_model is None
            return _FakeGas()

    monkeypatch.setattr(
        "larrak2.simulation_validation.runtime_chemistry_table._load_cantera",
        lambda: _FakeCanteraModule(),
    )

    output_dir = tmp_path / "runtime_table_seed_corridor"
    manifest = build_runtime_chemistry_table_from_spec(
        {
            "table_id": "chem323_engine_ignition_seed_corridor",
            "package_dir": str(package_dir),
            "output_dir": str(output_dir),
            "state_axis_strategy": "seed_corridor",
            "state_species": ["IC8H18", "O2", "CO2", "H2O"],
            "balance_species": "N2",
            "seed_handoff_artifacts": [str(handoff_path)],
            "seed_field_case_dirs": [str(case_dir)],
            "seed_field_max_time_dirs": 1,
            "seed_field_max_cells_per_time_dir": 4,
            "authority_windows": [
                {
                    "case_dir": str(case_dir),
                    "angle_min_deg": -7.1,
                    "angle_max_deg": -6.9,
                    "max_time_dirs": 1,
                    "max_cells_per_time_dir": 4,
                }
            ],
            "adaptive_sampling": {
                "sparse_level": 1,
                "candidate_sparse_level": 2,
                "refinement_rounds": 1,
                "batch_size": 4,
                "max_samples": 24,
                "source_tolerance": 0.0,
                "jacobian_tolerance": 0.0,
                "rbf_neighbor_count": 4,
                "rbf_epsilon": 1.0,
                "lookup_cache_quantization": 0.01,
            },
            "interpolation_method": "local_rbf",
            "fallback_policy": "fullReducedKinetics",
            "jacobian_mode": "full_species",
            "jacobian_storage": "csr",
        },
        refresh=True,
        repo_root=tmp_path,
    )

    assert manifest["state_axes"]["Temperature"][0] <= 300.0
    assert manifest["state_axes"]["Pressure"][-1] >= 2.4e6
    assert manifest["state_axes"]["IC8H18"][-1] > 0.04
    assert manifest["state_axes"]["O2"][-1] > 0.2
    assert manifest["adaptive_sampling"]["seed_point_count"] >= 4
    assert manifest["authority_pass"] is True
    assert manifest["strict_runtime_certified"] is True
    assert manifest["authority_windows"][0]["sampled_time_dir_count"] == 1
