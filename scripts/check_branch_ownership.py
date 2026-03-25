#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

import yaml

SUPPORTED_MAIN_BRANCH = "main"
EMPTY_TREE_SHA = "0000000000000000000000000000000000000000"


@dataclass(frozen=True)
class WorkflowRule:
    name: str
    base_branch: str
    promotion_target: str
    owned_paths: tuple[str, ...]
    exclude_paths: tuple[str, ...]


@dataclass(frozen=True)
class BranchPolicy:
    branch: str
    kind: str
    workflow: str | None
    expected_base: str | None
    allowed_paths: tuple[str, ...]


@dataclass(frozen=True)
class PolicyFinding:
    code: str
    title: str
    message: str
    path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.path is None:
            payload.pop("path")
        return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate branch naming, PR targets, and changed paths against workflow ownership.",
    )
    parser.add_argument("--branch", required=True, help="Branch or ref name to validate.")
    parser.add_argument("--base", help="Expected PR base branch for the branch under validation.")
    parser.add_argument(
        "--changed-file",
        help="Path to a file containing changed paths (one relative repo path per line).",
    )
    parser.add_argument(
        "--config",
        default="workflow_ownership.yml",
        help="Path to the workflow ownership manifest.",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Repository root directory (defaults to the repo root).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a JSON report instead of human-readable output.",
    )
    return parser.parse_args()


def load_config(config_path: Path) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def normalize_branch_name(branch: str) -> str:
    branch = branch.strip()
    if branch.startswith("refs/heads/"):
        return branch.removeprefix("refs/heads/")
    return branch


def normalize_path(path: str) -> str:
    normalized = path.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.rstrip("/")


def load_workflow_rules(config: dict[str, Any]) -> dict[str, WorkflowRule]:
    workflows = config.get("workflows", {})
    rules: dict[str, WorkflowRule] = {}
    for name, raw_rule in workflows.items():
        rules[name] = WorkflowRule(
            name=name,
            base_branch=str(raw_rule["base_branch"]),
            promotion_target=str(
                raw_rule.get("promotion_target", config.get("promotion_target", "main"))
            ),
            owned_paths=tuple(str(value) for value in raw_rule.get("owned_paths", [])),
            exclude_paths=tuple(str(value) for value in raw_rule.get("exclude_paths", [])),
        )
    return rules


def match_any(path: str, patterns: tuple[str, ...] | list[str]) -> bool:
    return any(fnmatch(path, pattern) for pattern in patterns)


def classify_branch(branch: str, config: dict[str, Any]) -> BranchPolicy:
    branch = normalize_branch_name(branch)
    rules = load_workflow_rules(config)
    main_only_paths = tuple(str(value) for value in config.get("main_only_paths", []))
    shared_contract_paths = tuple(str(value) for value in config.get("shared_contract_paths", []))

    if branch == SUPPORTED_MAIN_BRANCH:
        return BranchPolicy(
            branch=branch,
            kind="main",
            workflow=None,
            expected_base=None,
            allowed_paths=main_only_paths + shared_contract_paths,
        )

    if branch.startswith("codex/main/"):
        return BranchPolicy(
            branch=branch,
            kind="codex-main",
            workflow="main",
            expected_base=SUPPORTED_MAIN_BRANCH,
            allowed_paths=main_only_paths + shared_contract_paths,
        )

    if branch.startswith("codex/"):
        parts = branch.split("/", 2)
        if len(parts) != 3 or not parts[2]:
            raise ValueError(
                "Task branches must use codex/<workflow>/<topic> naming.",
            )
        workflow = parts[1]
        rule = rules.get(workflow)
        if rule is None:
            raise ValueError(f"Unknown workflow '{workflow}' in branch '{branch}'.")
        return BranchPolicy(
            branch=branch,
            kind="codex-workflow",
            workflow=workflow,
            expected_base=rule.base_branch,
            allowed_paths=rule.owned_paths,
        )

    if branch.startswith("dev/"):
        workflow = branch.removeprefix("dev/")
        rule = rules.get(workflow)
        if rule is None or branch != rule.base_branch:
            raise ValueError(f"Unknown workflow branch '{branch}'.")
        return BranchPolicy(
            branch=branch,
            kind="dev-workflow",
            workflow=workflow,
            expected_base=rule.promotion_target,
            allowed_paths=rule.owned_paths,
        )

    raise ValueError(
        f"Unsupported branch '{branch}'. Expected main, dev/<workflow>, codex/main/<topic>, or codex/<workflow>/<topic>.",
    )


def read_changed_paths(root: Path, changed_file: str | None) -> list[str]:
    if changed_file:
        return [
            normalize_path(path)
            for path in Path(changed_file).read_text(encoding="utf-8").splitlines()
            if normalize_path(path)
        ]

    commands = [
        ["git", "diff", "--name-only", "--relative", "HEAD"],
        ["git", "diff", "--name-only", "--cached", "--relative", "HEAD"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ]
    discovered: set[str] = set()
    for command in commands:
        result = subprocess.run(
            command,
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        for line in result.stdout.splitlines():
            normalized = normalize_path(line)
            if normalized:
                discovered.add(normalized)
    return sorted(discovered)


def validate_base(policy: BranchPolicy, base: str | None) -> list[PolicyFinding]:
    if not base or policy.expected_base is None:
        return []

    normalized_base = normalize_branch_name(base)
    if normalized_base == policy.expected_base:
        return []

    return [
        PolicyFinding(
            code="ownership",
            title="Wrong branch target",
            message=(
                f"Branch '{policy.branch}' must target '{policy.expected_base}', "
                f"not '{normalized_base}'."
            ),
        )
    ]


def classify_path_violation(
    path: str,
    config: dict[str, Any],
    workflow_rule: WorkflowRule | None,
) -> str:
    main_only_paths = tuple(str(value) for value in config.get("main_only_paths", []))
    shared_contract_paths = tuple(str(value) for value in config.get("shared_contract_paths", []))
    if match_any(path, main_only_paths) or match_any(path, shared_contract_paths):
        return "reserved for codex/main tasks and main promotion work"
    if (
        workflow_rule
        and workflow_rule.exclude_paths
        and match_any(path, workflow_rule.exclude_paths)
    ):
        return f"explicitly excluded from the '{workflow_rule.name}' workflow"
    return "outside the branch ownership manifest"


def validate_changed_paths(
    policy: BranchPolicy,
    changed_paths: list[str],
    config: dict[str, Any],
) -> list[PolicyFinding]:
    if not changed_paths or policy.kind == "main":
        return []

    rules = load_workflow_rules(config)
    workflow_rule = rules.get(policy.workflow or "")
    violations: list[PolicyFinding] = []
    for path in changed_paths:
        if match_any(path, policy.allowed_paths):
            if (
                workflow_rule
                and workflow_rule.exclude_paths
                and match_any(path, workflow_rule.exclude_paths)
            ):
                violations.append(
                    PolicyFinding(
                        code="layout",
                        title="Excluded workflow path",
                        message=f"'{path}' is excluded from the '{workflow_rule.name}' workflow.",
                        path=path,
                    )
                )
            continue
        reason = classify_path_violation(path, config, workflow_rule)
        violations.append(
            PolicyFinding(
                code="ownership",
                title="Out-of-scope path touched",
                message=f"'{path}' is not allowed on '{policy.branch}' ({reason}).",
                path=path,
            )
        )
    return violations


def findings_to_lines(findings: list[PolicyFinding]) -> list[str]:
    return [finding.message for finding in findings]


def main() -> int:
    args = parse_args()
    script_root = Path(__file__).resolve().parents[1]
    root = Path(args.root).resolve() if args.root else script_root
    config_path = (root / args.config).resolve()
    config = load_config(config_path)

    try:
        policy = classify_branch(args.branch, config)
    except ValueError as exc:
        if args.json:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "branch": normalize_branch_name(args.branch),
                        "findings": [
                            PolicyFinding(
                                code="ownership",
                                title="Invalid branch naming",
                                message=str(exc),
                            ).to_dict()
                        ],
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            print(f"Branch ownership check failed: {exc}")
        return 1

    changed_paths = read_changed_paths(root, args.changed_file)
    findings = validate_base(policy, args.base)
    findings.extend(validate_changed_paths(policy, changed_paths, config))

    if args.json:
        print(
            json.dumps(
                {
                    "ok": not findings,
                    "branch": policy.branch,
                    "policy": asdict(policy),
                    "changed_paths": changed_paths,
                    "findings": [finding.to_dict() for finding in findings],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if not findings else 1

    if findings:
        print("Branch ownership violations detected:")
        for violation in findings_to_lines(findings):
            print(f"- {violation}")
        return 1

    print(
        f"Branch ownership check passed for '{policy.branch}'.",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
