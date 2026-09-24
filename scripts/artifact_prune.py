#!/usr/bin/env python3
"""Governed lifecycle helpers for local surrogate / OpenFOAM authority outputs.

Default is read-only or dry-run. Destructive removal requires explicit flags.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_REL_OPENFOAM_AUTHORITY = Path("outputs") / "openfoam_authority"


def _repo_root(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    env = os.environ.get("LARRICK_MULTI_ROOT", "").strip()
    if env:
        return Path(env).resolve()
    return Path.cwd().resolve()


def _authority_root(repo_root: Path) -> Path:
    return (repo_root / _REL_OPENFOAM_AUTHORITY).resolve()


def _load_promotion_manifest(bundle_dir: Path) -> dict[str, Any] | None:
    path = bundle_dir / "promotion_manifest.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("skip %s: invalid promotion_manifest.json (%s)", bundle_dir.name, exc)
        return None
    return data if isinstance(data, dict) else None


def cmd_list(repo_root: Path) -> int:
    root = _authority_root(repo_root)
    if not root.is_dir():
        log.info("no OpenFOAM authority directory at %s", root)
        return 0
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        man = _load_promotion_manifest(d)
        if man is None:
            log.info("%s\t(no promotion_manifest.json)", d.name)
            continue
        status = man.get("status", "")
        promo = man.get("promotable", "")
        log.info("%s\tstatus=%r\tpromotable=%r", d.name, status, promo)
    return 0


def _is_prunable_staged_failure(man: dict[str, Any]) -> bool:
    return man.get("status") == "staged" and man.get("promotable") is False


def cmd_prune_staged_failures(
    repo_root: Path,
    *,
    apply: bool,
    confirm_delete: bool,
) -> int:
    root = _authority_root(repo_root)
    if not root.is_dir():
        log.info("nothing to prune: missing %s", root)
        return 0

    if apply and not confirm_delete:
        log.error("refusing --apply without --confirm-delete")
        return 2

    targets: list[Path] = []
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        man = _load_promotion_manifest(d)
        if man is None or not _is_prunable_staged_failure(man):
            continue
        targets.append(d)

    if not targets:
        log.info("no staged non-promotable bundles under %s", root)
        return 0

    for d in targets:
        if apply:
            shutil.rmtree(d)
            log.info("removed %s", d)
        else:
            log.info("dry-run: would remove %s", d)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="List or prune OpenFOAM authority staging bundles under outputs/.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Larrick_multi root (default: LARRICK_MULTI_ROOT or cwd).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List bundle directories and promotion status.")
    p_list.set_defaults(func=lambda a: cmd_list(_repo_root(a.root)))

    p_prune = sub.add_parser(
        "prune-staged-failures",
        help="Remove staged bundles with promotion_manifest promotable=false (failed staging).",
    )
    p_prune.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete directories (default is dry-run only).",
    )
    p_prune.add_argument(
        "--confirm-delete",
        action="store_true",
        help="Required with --apply to acknowledge destructive behavior.",
    )

    def _prune(ns: argparse.Namespace) -> int:
        return cmd_prune_staged_failures(
            _repo_root(ns.root),
            apply=bool(ns.apply),
            confirm_delete=bool(ns.confirm_delete),
        )

    p_prune.set_defaults(func=_prune)
    return parser


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    parser = _build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
