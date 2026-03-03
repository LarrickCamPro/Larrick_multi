# Tribology Gap Closure Plan (ISO-Grounded)

Status: in progress (implementation wave 1 complete)  
Last updated: 2026-03-03

## 1. ISO Mapping

| ISO source | Method scope | Code/data mapping |
| --- | --- | --- |
| ISO/TS 6336-20:2017 | Scuffing, flash temperature method | `scuff_method="flash"` path in `src/larrak2/cem/tribology.py` + `data/cem/scuffing_critical_temperatures.csv` |
| ISO/TS 6336-21:2017 | Scuffing, integral temperature method | `scuff_method="integral"` path in `src/larrak2/cem/tribology.py` + phase-resolved high-load evaluation in `src/larrak2/realworld/surrogates.py` |
| ISO/TS 6336-22:2018 | Micropitting permissible film and lambda safety | `data/cem/micropitting_lambda_perm.csv` + `compute_micropitting_safety` + `evaluate_tribology` |
| ISO 14635-1:2023 | FZG A/8,3/90 relative scuff capacity | `data/cem/fzg_step_load_map.csv` rows keyed to generic EP oil/additive package |
| ISO 14635-2:2023 | FZG A10/16,6R/120 step-load relative scuff capacity (high EP) | `data/cem/fzg_step_load_map.csv` rows keyed to high EP oil/additive package |

## 2. Data Contract

Required strict tables under `data/cem/`:

1. `tribology_ehl_coefficients.csv`
2. `scuffing_critical_temperatures.csv`
3. `micropitting_lambda_perm.csv`
4. `fzg_step_load_map.csv`

Schema contract highlights:

| Table | Required lookup keys | Required traceability columns |
| --- | --- | --- |
| `tribology_ehl_coefficients` | `oil_type`, `finish_tier`, `temp_C_min`, `temp_C_max` | `unit_system`, `provenance`, `version` |
| `scuffing_critical_temperatures` | `oil_type`, `additive_package`, `method`, `load_stage` | `unit_temp`, `provenance`, `version` |
| `micropitting_lambda_perm` | `oil_type`, `finish_tier` | `unit_lambda`, `provenance`, `version` |
| `fzg_step_load_map` | `test_standard`, `test_method`, `load_stage`, `oil_type`, `additive_package` | `unit_temp`, `provenance`, `version` |

## 3. Fail-Hard Policy

Validation modes in runtime:

1. `strict`: missing table, empty table, missing key column, unresolved key row, or non-numeric required values raise `ValueError`.
2. `warn`: continue execution with explicit degraded diagnostics (`tribology_data_status=degraded_warn`) and messages.
3. `off`: continue execution with explicit degraded diagnostics (`tribology_data_status=degraded_off`) and messages.

Strict resolution is controlled by:

1. `EvalContext.strict_data` (default strict)
2. `EvalContext.strict_tribology_data` (override)
3. CLI flags `--strict-tribology-data|--no-strict-tribology-data`

Scuff method policy is controlled by:

1. `EvalContext.tribology_scuff_method` (`auto|flash|integral`)
2. CLI flag `--tribology-scuff-method`

## 4. Acceptance Criteria

1. Strict mode fails when any required tribology table is missing, empty, or unresolved for requested lookup keys.
2. Warn/off mode proceeds with explicit degraded status and messages.
3. `auto` scuff policy equals `min(flash, integral)`.
4. Phase-resolved path computes high-load-bin flash and integral margins and selects method-aware worst case.
5. Diagnostics include method, data status, and table provenance/version metadata.
6. Downselect/release strict paths block approval when strict tribology data resolution fails.

## 5. CI Commands

Use these for tribology contract + behavior gating:

```bash
PYTHONPATH=src pytest -q tests/ci/test_cem_modules.py
PYTHONPATH=src pytest -q tests/ci/test_realworld_surrogates.py tests/ci/test_phase_resolved.py
PYTHONPATH=src pytest -q tests/ci/test_smoke_eval.py tests/ci/test_constraints_sign.py
```
