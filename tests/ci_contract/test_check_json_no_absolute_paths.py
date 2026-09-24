"""Tests for ``scripts/check_json_no_absolute_paths.py``."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "check_json_no_absolute_paths",
    _REPO / "scripts" / "check_json_no_absolute_paths.py",
)
assert _SPEC and _SPEC.loader
mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mod)


def test_skip_path_docs_sources_prefix() -> None:
    globs = ("Docs/sources/**",)
    assert mod._skip_path("Docs/sources/foo.json", globs) is True
    assert mod._skip_path("Docs/sources/a/b.json", globs) is True
    assert mod._skip_path("Docs/other.json", globs) is False


def test_violations_for_text_detects_users() -> None:
    hits = mod.violations_for_text('{"p": "/Users/alice/out.json"}')
    assert "/Users/" in hits


def test_scan_tracked_json_flags_violation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"root": "/home/bob/data"}), encoding="utf-8")
    monkeypatch.setattr(mod, "_tracked_json_paths", lambda _root: ["bad.json"])

    hits = mod.scan_tracked_json(tmp_path, ())
    assert hits == [("bad.json", "/home/")]


def test_scan_respects_default_exclude(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    nested = tmp_path / "Docs" / "sources"
    nested.mkdir(parents=True)
    f = nested / "legacy.json"
    f.write_text(json.dumps({"p": "/Users/x"}), encoding="utf-8")
    monkeypatch.setattr(mod, "_tracked_json_paths", lambda _root: ["Docs/sources/legacy.json"])

    hits_default = mod.scan_tracked_json(tmp_path, mod._DEFAULT_EXCLUDE_GLOBS)
    assert hits_default == []

    hits_strict = mod.scan_tracked_json(tmp_path, ())
    assert hits_strict


def test_fnmatch_exclude(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    p = tmp_path / "vendor.json"
    p.write_text('"/Users/x"', encoding="utf-8")
    monkeypatch.setattr(mod, "_tracked_json_paths", lambda _root: ["vendor.json"])

    assert mod.scan_tracked_json(tmp_path, ("vendor.json",)) == []
