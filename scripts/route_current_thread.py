#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from larrak2.architecture.github_concierge import (  # noqa: E402
    load_workflow_ownership,
    route_thread,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Route a cloud/current-workspace Codex thread and bootstrap the task branch.",
    )
    parser.add_argument(
        "--config",
        default=str(REPO_ROOT / "workflow_ownership.yml"),
        help="Path to the workflow ownership manifest.",
    )
    parser.add_argument("--prompt", help="Initial thread prompt to classify.")
    parser.add_argument(
        "--prompt-file",
        help="Path to a file containing the initial thread prompt.",
    )
    parser.add_argument(
        "--thread-id",
        default=os.environ.get("CODEX_THREAD_ID"),
        help="Codex thread identifier used for stable topic suffixes.",
    )
    parser.add_argument("--thread-name", help="Codex thread title when available.")
    parser.add_argument(
        "--workspace-mode",
        default="current",
        choices=("current",),
        help="Bootstrap mode for cloud/current-workspace routing.",
    )
    parser.add_argument(
        "--skip-pr-check",
        action="store_true",
        help="Skip local gh duplicate PR checks and rely on GitHub MCP search instead.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the routing decision and bootstrap command without mutating the checkout.",
    )
    return parser.parse_args()


def _load_prompt(args: argparse.Namespace) -> str:
    if args.prompt:
        return args.prompt
    if args.prompt_file:
        return Path(args.prompt_file).read_text(encoding="utf-8")
    raise SystemExit("A prompt is required. Pass --prompt or --prompt-file.")


def _build_bootstrap_command(
    *,
    workflow: str,
    topic_slug: str,
    prompt: str,
    thread_id: str | None,
    thread_name: str | None,
    routing_confidence: float,
    routing_source: str,
    routing_strategy: str,
    workspace_mode: str,
    skip_pr_check: bool,
) -> list[str]:
    command = [
        str(REPO_ROOT / "scripts" / "start_parallel_task.sh"),
        "--mode",
        workspace_mode,
        "--routing-workflow",
        workflow,
        "--routing-confidence",
        f"{routing_confidence:.3f}",
        "--routing-source",
        routing_source,
        "--routing-strategy",
        routing_strategy,
        "--source-prompt",
        prompt,
    ]
    if skip_pr_check:
        command.append("--skip-pr-check")
    if thread_id:
        command.extend(["--thread-id", thread_id])
    if thread_name:
        command.extend(["--thread-name", thread_name])
    command.extend([workflow, topic_slug])
    return command


def _result_payload(
    *,
    decision: dict[str, Any],
    bootstrap_command: list[str] | None = None,
    bootstrap_returncode: int | None = None,
    bootstrap_stdout: str | None = None,
    bootstrap_stderr: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"decision": decision}
    if bootstrap_command is not None:
        payload["bootstrap_command"] = bootstrap_command
    if bootstrap_returncode is not None:
        payload["bootstrap_returncode"] = bootstrap_returncode
    if bootstrap_stdout:
        payload["bootstrap_stdout"] = bootstrap_stdout.strip()
    if bootstrap_stderr:
        payload["bootstrap_stderr"] = bootstrap_stderr.strip()
    task_context_path = REPO_ROOT / ".task-runtime" / "task.json"
    if task_context_path.exists():
        payload["task_context_path"] = str(task_context_path)
    return payload


def main() -> int:
    args = parse_args()
    prompt = _load_prompt(args)
    policy = load_workflow_ownership(args.config)
    decision = route_thread(
        policy,
        prompt=prompt,
        thread_id=args.thread_id,
        thread_name=args.thread_name,
        workspace_mode=args.workspace_mode,
    )
    decision_payload = decision.to_dict()

    if decision.needs_confirmation:
        print(json.dumps(_result_payload(decision=decision_payload), indent=2, sort_keys=True))
        return 10

    bootstrap_command = _build_bootstrap_command(
        workflow=str(decision.workflow),
        topic_slug=str(decision.topic_slug),
        prompt=prompt,
        thread_id=args.thread_id,
        thread_name=args.thread_name,
        routing_confidence=decision.confidence,
        routing_source=decision.routing_source,
        routing_strategy=decision.routing_strategy,
        workspace_mode=args.workspace_mode,
        skip_pr_check=args.skip_pr_check,
    )

    if args.dry_run:
        print(
            json.dumps(
                _result_payload(
                    decision=decision_payload,
                    bootstrap_command=bootstrap_command,
                ),
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    completed = subprocess.run(
        bootstrap_command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    print(
        json.dumps(
            _result_payload(
                decision=decision_payload,
                bootstrap_command=bootstrap_command,
                bootstrap_returncode=completed.returncode,
                bootstrap_stdout=completed.stdout,
                bootstrap_stderr=completed.stderr,
            ),
            indent=2,
            sort_keys=True,
        )
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
