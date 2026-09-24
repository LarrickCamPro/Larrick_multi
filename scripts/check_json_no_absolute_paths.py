#!/usr/bin/env python3
"""Fail if tracked JSON contains obvious machine-local absolute path strings."""

from __future__ import annotations

import argparse
import fnmatch
import logging
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)

# Substrings that indicate host-specific paths (POSIX + common Windows JSON escapes).
_MACHINE_MARKERS: tuple[str, ...] = (
    "/Users/",
    "/home/",
    "C:\\\\Users\\\\",
    "C:/Users/",
)

# Grandfathered paths: legacy manifests, local shim files, and generated .NET obj JSON.
# New committed JSON elsewhere must stay portable. Override with --no-default-excludes.
_DEFAULT_EXCLUDE_GLOBS: tuple[str, ...] = (
    "Docs/sources/**",
    "data/simulation_validation/**",
    "tools/picogk_manufact/obj/**",
    "tools/shim_manifest_larrak2.json",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan git-tracked *.json for machine-local absolute path markers.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root (default: parent of scripts/).",
    )
    parser.add_argument(
        "--no-default-excludes",
        action="store_true",
        help=f"Do not skip paths matching {list(_DEFAULT_EXCLUDE_GLOBS)}.",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="Additional path glob(s) relative to repo root to skip (fnmatch). Repeatable.",
    )
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="Print violations but exit 0 (for gradual rollout).",
    )
    return parser.parse_args()


def _repo_root(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    return Path(__file__).resolve().parents[1]


def _tracked_json_paths(root: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--", "*.json"],
        check=False,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "git ls-files failed; run from a git checkout at --root.",
        )
    raw = proc.stdout.split(b"\0")
    return [p.decode("utf-8") for p in raw if p]


def _skip_path(rel: str, globs: tuple[str, ...]) -> bool:
    """Return True if ``rel`` should be skipped (POSIX-style, ``/`` separators)."""
    rel_posix = rel.replace("\\", "/")
    for g in globs:
        g_posix = g.replace("\\", "/")
        if g_posix.endswith("/**"):
            prefix = g_posix[:-3]  # strip trailing /**
            if rel_posix == prefix.rstrip("/") or rel_posix.startswith(
                prefix.rstrip("/") + "/",
            ):
                return True
        elif fnmatch.fnmatch(rel_posix, g_posix):
            return True
    return False


def violations_for_text(text: str) -> list[str]:
    """Return human-readable violation lines for markers present in ``text``."""
    hits: list[str] = []
    for marker in _MACHINE_MARKERS:
        if marker in text:
            hits.append(marker)
    return hits


def scan_tracked_json(
    root: Path,
    exclude_globs: tuple[str, ...],
) -> list[tuple[str, str]]:
    """Return list of (relative_path, marker) for each violation."""
    out: list[tuple[str, str]] = []
    for rel in _tracked_json_paths(root):
        if _skip_path(rel, exclude_globs):
            continue
        path = root / rel
        try:
            body = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for marker in violations_for_text(body):
            out.append((rel, marker))
            break
    return out


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    args = parse_args()
    root = _repo_root(args.root)
    globs: list[str] = list(args.exclude)
    if not args.no_default_excludes:
        globs.extend(_DEFAULT_EXCLUDE_GLOBS)
    exclude_tuple = tuple(globs)

    try:
        bad = scan_tracked_json(root, exclude_tuple)
    except RuntimeError as exc:
        log.error("%s", exc)
        return 2

    if not bad:
        return 0

    for rel, marker in sorted(bad):
        log.error("%s: contains machine-local marker %r", rel, marker)

    if args.warn_only:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
