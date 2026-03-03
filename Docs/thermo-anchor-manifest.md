# Thermo Anchor Manifest Contract

This document defines the strict fidelity-2 anchor policy used by the equation-first thermo path.

## Contract

1. Anchor manifest path:
   `data/thermo/anchor_manifest_v1.json` by default, or `EvalContext.thermo_anchor_manifest_path` override.
2. In strict mode (`surrogate_validation_mode="strict"`) with `fidelity >= 2`:
   anchors must be non-empty.
3. Anchor schema:
   each anchor is an object with finite `rpm > 0` and `torque >= 0`.

## Diagnostics Emitted

Thermo diagnostics include:

1. `anchor_manifest_version`
2. `anchor_count`
3. `anchor_path`

## Reproducible Generation

Use the manifest builder:

```bash
PYTHONPATH=src python tools/build_thermo_anchor_manifest.py \
  --input outputs/orchestration/truth_records.jsonl \
  --output data/thermo/anchor_manifest_v1.json \
  --source truth_runs
```

Supported inputs are `.json` or `.jsonl` records containing `rpm`/`torque` fields
either at top-level or under `operating_point`.
