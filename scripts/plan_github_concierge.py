#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from larrak2.architecture.github_concierge import (  # noqa: E402
    actions_to_json,
    build_task_context,
    load_task_context,
    load_workflow_ownership,
    plan_drift_audit,
    plan_merge_checker,
    plan_promotion_actions,
    plan_release_audit,
    plan_security_audit,
    plan_task_actions,
    render_promotion_issue_payload,
    render_task_issue_payload,
    route_thread,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render task context and pure-planner actions for the GitHub concierge flow.",
    )
    parser.add_argument(
        "--config",
        default=str(REPO_ROOT / "workflow_ownership.yml"),
        help="Path to the workflow ownership manifest.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    task_context = subparsers.add_parser("task-context", help="Emit task context JSON.")
    task_context.add_argument("--workflow", required=True)
    task_context.add_argument("--topic", required=True)
    task_context.add_argument("--worktree", required=True)
    task_context.add_argument("--branch")
    task_context.add_argument("--docker-namespace")
    task_context.add_argument("--thread-id")
    task_context.add_argument("--thread-name")
    task_context.add_argument("--routing-workflow")
    task_context.add_argument("--routing-confidence", type=float)
    task_context.add_argument("--routing-source")
    task_context.add_argument("--routing-strategy")
    task_context.add_argument("--source-prompt")
    task_context.add_argument("--workspace-mode", default="worktree")
    task_context.add_argument("--conversation-state", default="active")
    task_context.add_argument("--archive-eligible", action="store_true")
    task_context.add_argument("--last-thread-seen-at")
    task_context.add_argument("--issue-number", type=int)

    route = subparsers.add_parser("route-thread", help="Route a thread prompt to a workflow branch.")
    route.add_argument("--prompt")
    route.add_argument("--prompt-file")
    route.add_argument("--thread-id")
    route.add_argument("--thread-name")
    route.add_argument("--workspace-mode", default="current")

    task = subparsers.add_parser("task", help="Plan task PR actions.")
    task.add_argument("--task-json", required=True)
    task.add_argument("--snapshot-json", required=True)

    task_issue = subparsers.add_parser(
        "task-issue-payload",
        help="Render task issue title/body payload.",
    )
    task_issue.add_argument("--task-json", required=True)

    promote = subparsers.add_parser("promote", help="Plan promotion PR actions.")
    promote.add_argument("--workflow", required=True)
    promote.add_argument("--snapshot-json", required=True)

    promotion_issue = subparsers.add_parser(
        "promotion-issue-payload",
        help="Render promotion issue title/body payload.",
    )
    promotion_issue.add_argument("--workflow", required=True)
    promotion_issue.add_argument("--snapshot-json", required=True)

    audit_drift = subparsers.add_parser("audit-drift", help="Plan drift/staleness audit actions.")
    audit_drift.add_argument("--snapshot-json", required=True)

    audit_security = subparsers.add_parser(
        "audit-security", help="Plan security scan audit actions."
    )
    audit_security.add_argument("--snapshot-json", required=True)

    audit_release = subparsers.add_parser(
        "audit-release", help="Plan release readiness audit actions."
    )
    audit_release.add_argument("--snapshot-json", required=True)

    merge_check = subparsers.add_parser(
        "merge-check", help="Plan daily quiet-branch merge checker actions."
    )
    merge_check.add_argument("--snapshot-json", required=True)

    return parser.parse_args()


def load_json(path: str) -> dict[str, Any]:
    json_path = Path(path)
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(json_path.read_text(encoding="utf-8"))


def main() -> int:
    args = parse_args()
    policy = load_workflow_ownership(args.config)

    if args.command == "route-thread":
        prompt = ""
        if args.prompt:
            prompt = args.prompt
        elif args.prompt_file:
            prompt = Path(args.prompt_file).read_text(encoding="utf-8")
        decision = route_thread(
            policy,
            prompt=prompt,
            thread_id=args.thread_id,
            thread_name=args.thread_name,
            workspace_mode=args.workspace_mode,
        )
        print(json.dumps(decision.to_dict(), indent=2, sort_keys=True))
        return 0

    if args.command == "task-context":
        payload = build_task_context(
            policy=policy,
            workflow=args.workflow,
            topic_slug=args.topic,
            worktree_path=args.worktree,
            branch=args.branch,
            docker_namespace=args.docker_namespace,
            thread_id=args.thread_id,
            thread_name=args.thread_name,
            routing_workflow=args.routing_workflow,
            routing_confidence=args.routing_confidence,
            routing_source=args.routing_source,
            routing_strategy=args.routing_strategy,
            source_prompt_excerpt=args.source_prompt,
            workspace_mode=args.workspace_mode,
            conversation_state=args.conversation_state,
            archive_eligible=args.archive_eligible,
            last_thread_seen_at=args.last_thread_seen_at,
            issue_number=args.issue_number,
        ).to_dict()
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    if args.command == "task":
        task = load_task_context(args.task_json)
        snapshot = load_json(args.snapshot_json)
        print(actions_to_json(plan_task_actions(policy, task, snapshot)))
        return 0

    if args.command == "task-issue-payload":
        task = load_task_context(args.task_json)
        print(json.dumps(render_task_issue_payload(policy, task), indent=2, sort_keys=True))
        return 0

    snapshot = load_json(args.snapshot_json)
    if args.command == "promote":
        print(actions_to_json(plan_promotion_actions(policy, args.workflow, snapshot)))
        return 0
    if args.command == "promotion-issue-payload":
        print(
            json.dumps(
                render_promotion_issue_payload(policy, args.workflow, snapshot),
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "audit-drift":
        print(actions_to_json(plan_drift_audit(policy, snapshot)))
        return 0
    if args.command == "audit-security":
        print(actions_to_json(plan_security_audit(policy, snapshot)))
        return 0
    if args.command == "audit-release":
        print(actions_to_json(plan_release_audit(policy, snapshot)))
        return 0
    if args.command == "merge-check":
        print(actions_to_json(plan_merge_checker(policy, snapshot)))
        return 0

    raise ValueError(f"Unsupported command '{args.command}'")


if __name__ == "__main__":
    raise SystemExit(main())
