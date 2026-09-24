---
description: Invoke the Kotlin ↔ Python GUI bridge script (allowlisted agent surface).
---

# larrick_gui_bridge

**Script:** [`scripts/larrick_gui_bridge.py`](../../scripts/larrick_gui_bridge.py)

**Contract:** [CLI contract — GUI bridge](../../../docs/project_status/cli_contract_for_agents.md#gui-bridge-subprocess-contract)

**Working directory:** `Larrick_multi/`.

```bash
python scripts/larrick_gui_bridge.py --mode optimize \
  --input path/to/input.json --output path/to/output.json --output-dir path/to/workspace
```

Use `--mode orchestrate|simulate|analyze|engine_eval` as needed. See bridge docstrings and [`tests/ci_contract/test_larrick_gui_bridge.py`](../../tests/ci_contract/test_larrick_gui_bridge.py) for JSON shape and exit-code semantics.
