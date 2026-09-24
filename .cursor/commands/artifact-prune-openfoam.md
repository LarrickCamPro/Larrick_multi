---
description: List or dry-run prune failed OpenFOAM authority staging bundles.
---

# Artifact prune (OpenFOAM authority)

Governed lifecycle for `outputs/openfoam_authority/` — see [artifact lifecycle for agents](../../../docs/project_status/artifact_lifecycle_for_agents.md).

**Working directory:** `Larrick_multi/` (or pass `--root`).

List bundles and `promotion_manifest.json` status:

```bash
python scripts/artifact_prune.py list
```

Dry-run removal of **staged** bundles with `promotable: false` (failed staging only):

```bash
python scripts/artifact_prune.py prune-staged-failures
```

Actually delete (requires explicit confirmation):

```bash
python scripts/artifact_prune.py prune-staged-failures --apply --confirm-delete
```

Never use arbitrary `rm -rf` on artifact trees; use this tool or the manual procedure in the lifecycle doc.
