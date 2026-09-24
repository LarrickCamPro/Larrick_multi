---
description: Scan tracked JSON for machine-local absolute paths (CI contract).
---

# JSON path audit (Phase C / C3)

Runs [`scripts/check_json_no_absolute_paths.py`](../../scripts/check_json_no_absolute_paths.py). See [CLI contract — committed JSON path rules](../../../docs/project_status/cli_contract_for_agents.md#committed-json-path-rules).

**Working directory:** `Larrick_multi/` (repository root for this package).

```bash
python scripts/check_json_no_absolute_paths.py
```

Strict scan (includes grandfathered paths; may fail until legacy JSON is cleaned):

```bash
python scripts/check_json_no_absolute_paths.py --no-default-excludes
```

Warning-only (non-blocking):

```bash
python scripts/check_json_no_absolute_paths.py --warn-only
```
