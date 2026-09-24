---
description: Run scoped CI contract tests (pytest ci_contract) from Larrick_multi.
---

# CI contract tests

Fast lane matches [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml): `pytest -q` with `testpaths` = `tests/ci_contract`.

**Working directory:** `Larrick_multi/`.

```bash
uv sync --extra dev
export LARRICK_MULTI_ROOT="$(pwd)"
export PYTHONPATH=src
pytest -q tests/ci_contract
```
