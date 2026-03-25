"""Pure planning and rendering helpers for the GitHub MCP concierge flow."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from string import Template
from typing import Any

import yaml

FINGERPRINT_PATTERN = re.compile(r"<!--\s*concierge:fingerprint=([^\s>]+)\s*-->")
BLOCKED_PATTERN = re.compile(r"<!--\s*concierge:blocked=([^\s>]+)\s*-->")
TASK_METADATA_PATTERN = re.compile(
    r"<!--\s*concierge:task-metadata\s*(\{.*?\})\s*-->",
    re.DOTALL,
)
SEMVER_PATTERN = re.compile(r"^v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$")


@dataclass(frozen=True)
class RepoIdentity:
    owner: str
    name: str


@dataclass(frozen=True)
class PullRequestPolicy:
    auto_merge_to_dev: bool
    manual_merge_to_main: bool


@dataclass(frozen=True)
class AuditThresholds:
    stale_branch_without_pr_hours: int
    stale_open_task_pr_hours: int
    stale_failing_task_pr_hours: int
    orphaned_no_pr_archive_hours: int


@dataclass(frozen=True)
class RoutingPolicy:
    confidence_threshold: float
    confidence_gap_threshold: float
    prompt_excerpt_chars: int
    main_keywords: tuple[str, ...]
    explicit_token_prefix: str
    explicit_phrase_templates: tuple[str, ...]


@dataclass(frozen=True)
class MergeCheckerPolicy:
    inactivity_hours: int
    blocked_archive_hours: int


@dataclass(frozen=True)
class ReleasePolicy:
    strategy: str
    tag_prefix: str
    current_version_source: str


@dataclass(frozen=True)
class WorkflowPolicy:
    name: str
    base_branch: str
    promotion_target: str
    routing_keywords: tuple[str, ...]
    owned_paths: tuple[str, ...]
    exclude_paths: tuple[str, ...]


@dataclass(frozen=True)
class WorkflowOwnershipPolicy:
    repo: RepoIdentity
    promotion_target: str
    pr_policy: PullRequestPolicy
    issue_policy: str
    routing_policy: RoutingPolicy
    merge_checker_policy: MergeCheckerPolicy
    audit_thresholds: AuditThresholds
    release_policy: ReleasePolicy
    shared_contract_paths: tuple[str, ...]
    main_only_paths: tuple[str, ...]
    workflows: dict[str, WorkflowPolicy]


@dataclass(frozen=True)
class TaskContext:
    workflow: str
    branch: str
    base_branch: str
    promotion_branch: str
    topic_slug: str
    worktree_path: str
    repo_owner: str
    repo_name: str
    docker_namespace: str
    thread_id: str | None = None
    thread_name: str | None = None
    routing_workflow: str | None = None
    routing_confidence: float | None = None
    routing_source: str | None = None
    routing_strategy: str | None = None
    source_prompt_excerpt: str | None = None
    workspace_mode: str = "worktree"
    conversation_state: str = "active"
    archive_eligible: bool = False
    last_thread_seen_at: str | None = None
    issue_number: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlannedAction:
    action_id: str
    summary: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ThreadRouteDecision:
    workflow: str | None
    base_branch: str | None
    topic_slug: str | None
    branch: str | None
    confidence: float
    confidence_gap: float
    routing_source: str
    routing_strategy: str
    needs_confirmation: bool
    recommended_workflow: str | None
    candidate_scores: tuple[tuple[str, float], ...]
    matched_keywords: tuple[str, ...]
    source_prompt_excerpt: str
    workspace_mode: str
    thread_id: str | None = None
    thread_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow": self.workflow,
            "base_branch": self.base_branch,
            "topic_slug": self.topic_slug,
            "branch": self.branch,
            "confidence": self.confidence,
            "confidence_gap": self.confidence_gap,
            "routing_source": self.routing_source,
            "routing_strategy": self.routing_strategy,
            "needs_confirmation": self.needs_confirmation,
            "recommended_workflow": self.recommended_workflow,
            "candidate_scores": [
                {"workflow": workflow, "score": score}
                for workflow, score in self.candidate_scores
            ],
            "matched_keywords": list(self.matched_keywords),
            "source_prompt_excerpt": self.source_prompt_excerpt,
            "workspace_mode": self.workspace_mode,
            "thread_id": self.thread_id,
            "thread_name": self.thread_name,
        }


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def template_root() -> Path:
    return repo_root() / ".github" / "concierge_templates"


def load_workflow_ownership(path: str | Path | None = None) -> WorkflowOwnershipPolicy:
    config_path = Path(path) if path is not None else repo_root() / "workflow_ownership.yml"
    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    repo = raw.get("repo", {})
    pr_policy = raw.get("pr_policy", {})
    routing_policy = raw.get("routing_policy", {})
    merge_checker = raw.get("merge_checker_policy", {})
    thresholds = raw.get("audit_thresholds", {})
    release_policy = raw.get("release_policy", {})
    workflows: dict[str, WorkflowPolicy] = {}
    for workflow_name, workflow_data in (raw.get("workflows", {}) or {}).items():
        workflows[workflow_name] = WorkflowPolicy(
            name=workflow_name,
            base_branch=str(workflow_data["base_branch"]),
            promotion_target=str(
                workflow_data.get("promotion_target", raw.get("promotion_target", "main"))
            ),
            routing_keywords=tuple(
                str(item) for item in workflow_data.get("routing_keywords", [])
            ),
            owned_paths=tuple(str(item) for item in workflow_data.get("owned_paths", [])),
            exclude_paths=tuple(str(item) for item in workflow_data.get("exclude_paths", [])),
        )

    return WorkflowOwnershipPolicy(
        repo=RepoIdentity(owner=str(repo["owner"]), name=str(repo["name"])),
        promotion_target=str(raw.get("promotion_target", "main")),
        pr_policy=PullRequestPolicy(
            auto_merge_to_dev=bool(pr_policy.get("auto_merge_to_dev", True)),
            manual_merge_to_main=bool(pr_policy.get("manual_merge_to_main", True)),
        ),
        issue_policy=str(raw.get("issue_policy", "optional")),
        routing_policy=RoutingPolicy(
            confidence_threshold=float(routing_policy.get("confidence_threshold", 0.70)),
            confidence_gap_threshold=float(
                routing_policy.get("confidence_gap_threshold", 0.15)
            ),
            prompt_excerpt_chars=int(routing_policy.get("prompt_excerpt_chars", 240)),
            main_keywords=tuple(str(item) for item in routing_policy.get("main_keywords", [])),
            explicit_token_prefix=str(routing_policy.get("explicit_token_prefix", "workflow:")),
            explicit_phrase_templates=tuple(
                str(item) for item in routing_policy.get("explicit_phrase_templates", [])
            ),
        ),
        merge_checker_policy=MergeCheckerPolicy(
            inactivity_hours=int(merge_checker.get("inactivity_hours", 72)),
            blocked_archive_hours=int(merge_checker.get("blocked_archive_hours", 14 * 24)),
        ),
        audit_thresholds=AuditThresholds(
            stale_branch_without_pr_hours=int(
                thresholds.get("stale_branch_without_pr_hours", 24)
            ),
            stale_open_task_pr_hours=int(thresholds.get("stale_open_task_pr_hours", 48)),
            stale_failing_task_pr_hours=int(
                thresholds.get("stale_failing_task_pr_hours", 24)
            ),
            orphaned_no_pr_archive_hours=int(
                thresholds.get("orphaned_no_pr_archive_hours", 14 * 24)
            ),
        ),
        release_policy=ReleasePolicy(
            strategy=str(release_policy.get("strategy", "semver")),
            tag_prefix=str(release_policy.get("tag_prefix", "v")),
            current_version_source=str(
                release_policy.get("current_version_source", "pyproject.toml")
            ),
        ),
        shared_contract_paths=tuple(str(item) for item in raw.get("shared_contract_paths", [])),
        main_only_paths=tuple(str(item) for item in raw.get("main_only_paths", [])),
        workflows=workflows,
    )


def load_task_context(path: str | Path) -> TaskContext:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return task_context_from_dict(payload)


def task_context_from_dict(payload: Mapping[str, Any]) -> TaskContext:
    issue_number = payload.get("issue_number")
    routing_confidence = payload.get("routing_confidence")
    return TaskContext(
        workflow=str(payload["workflow"]),
        branch=str(payload["branch"]),
        base_branch=str(payload["base_branch"]),
        promotion_branch=str(payload["promotion_branch"]),
        topic_slug=str(payload["topic_slug"]),
        worktree_path=str(payload["worktree_path"]),
        repo_owner=str(payload["repo_owner"]),
        repo_name=str(payload["repo_name"]),
        docker_namespace=str(payload["docker_namespace"]),
        thread_id=str(payload["thread_id"]) if payload.get("thread_id") is not None else None,
        thread_name=(
            str(payload["thread_name"]) if payload.get("thread_name") is not None else None
        ),
        routing_workflow=(
            str(payload["routing_workflow"])
            if payload.get("routing_workflow") is not None
            else None
        ),
        routing_confidence=(
            float(routing_confidence) if routing_confidence is not None else None
        ),
        routing_source=(
            str(payload["routing_source"])
            if payload.get("routing_source") is not None
            else None
        ),
        routing_strategy=(
            str(payload["routing_strategy"])
            if payload.get("routing_strategy") is not None
            else None
        ),
        source_prompt_excerpt=(
            str(payload["source_prompt_excerpt"])
            if payload.get("source_prompt_excerpt") is not None
            else None
        ),
        workspace_mode=str(payload.get("workspace_mode", "worktree")),
        conversation_state=str(payload.get("conversation_state", "active")),
        archive_eligible=bool(payload.get("archive_eligible", False)),
        last_thread_seen_at=(
            str(payload["last_thread_seen_at"])
            if payload.get("last_thread_seen_at") is not None
            else None
        ),
        issue_number=int(issue_number) if issue_number is not None else None,
    )


def build_task_context(
    *,
    policy: WorkflowOwnershipPolicy,
    workflow: str,
    topic_slug: str,
    worktree_path: str | Path,
    branch: str | None = None,
    docker_namespace: str | None = None,
    thread_id: str | None = None,
    thread_name: str | None = None,
    routing_workflow: str | None = None,
    routing_confidence: float | None = None,
    routing_source: str | None = None,
    routing_strategy: str | None = None,
    source_prompt_excerpt: str | None = None,
    workspace_mode: str = "worktree",
    conversation_state: str = "active",
    archive_eligible: bool = False,
    last_thread_seen_at: str | None = None,
    issue_number: int | None = None,
) -> TaskContext:
    workflow_policy = (
        policy.workflows[workflow]
        if workflow != "main"
        else WorkflowPolicy(
            name="main",
            base_branch="main",
            promotion_target="main",
            routing_keywords=policy.routing_policy.main_keywords,
            owned_paths=policy.main_only_paths + policy.shared_contract_paths,
            exclude_paths=(),
        )
    )
    branch_name = branch or f"codex/{workflow}/{topic_slug}"
    docker_ns = docker_namespace or branch_name.replace("/", "-")
    return TaskContext(
        workflow=workflow,
        branch=branch_name,
        base_branch=workflow_policy.base_branch,
        promotion_branch=workflow_policy.promotion_target,
        topic_slug=topic_slug,
        worktree_path=str(Path(worktree_path)),
        repo_owner=policy.repo.owner,
        repo_name=policy.repo.name,
        docker_namespace=docker_ns,
        thread_id=thread_id,
        thread_name=thread_name,
        routing_workflow=routing_workflow or workflow,
        routing_confidence=routing_confidence,
        routing_source=routing_source or routing_strategy,
        routing_strategy=routing_strategy,
        source_prompt_excerpt=trim_excerpt(
            source_prompt_excerpt,
            limit=policy.routing_policy.prompt_excerpt_chars,
        )
        if source_prompt_excerpt
        else None,
        workspace_mode=workspace_mode,
        conversation_state=conversation_state,
        archive_eligible=archive_eligible,
        last_thread_seen_at=last_thread_seen_at,
        issue_number=issue_number,
    )


def route_thread(
    policy: WorkflowOwnershipPolicy,
    *,
    prompt: str,
    thread_id: str | None = None,
    thread_name: str | None = None,
    workspace_mode: str = "current",
) -> ThreadRouteDecision:
    excerpt = trim_excerpt(prompt, limit=policy.routing_policy.prompt_excerpt_chars)
    combined_text = "\n".join(part for part in (thread_name, prompt) if part).strip()
    explicit_marker = _detect_explicit_workflow_marker(policy, combined_text)
    if explicit_marker["needs_confirmation"]:
        recommended_workflow = explicit_marker.get("recommended_workflow")
        return ThreadRouteDecision(
            workflow=None,
            base_branch=None,
            topic_slug=None,
            branch=None,
            confidence=0.0,
            confidence_gap=0.0,
            routing_source="ask-user",
            routing_strategy="ask-user",
            needs_confirmation=True,
            recommended_workflow=recommended_workflow,
            candidate_scores=(),
            matched_keywords=tuple(_string_list(explicit_marker.get("matched_markers", []))),
            source_prompt_excerpt=excerpt,
            workspace_mode=workspace_mode,
            thread_id=thread_id,
            thread_name=thread_name,
        )
    explicit_workflow = explicit_marker.get("workflow")
    if explicit_workflow:
        topic_slug = build_thread_topic_slug(
            thread_name=thread_name,
            prompt=prompt,
            thread_id=thread_id,
        )
        base_branch = (
            "main" if explicit_workflow == "main" else policy.workflows[explicit_workflow].base_branch
        )
        routing_source = str(explicit_marker.get("routing_source", "explicit_phrase"))
        return ThreadRouteDecision(
            workflow=explicit_workflow,
            base_branch=base_branch,
            topic_slug=topic_slug,
            branch=f"codex/{explicit_workflow}/{topic_slug}",
            confidence=1.0,
            confidence_gap=1.0,
            routing_source=routing_source,
            routing_strategy=routing_source,
            needs_confirmation=False,
            recommended_workflow=explicit_workflow,
            candidate_scores=((explicit_workflow, 1.0),),
            matched_keywords=tuple(_string_list(explicit_marker.get("matched_markers", []))),
            source_prompt_excerpt=excerpt,
            workspace_mode=workspace_mode,
            thread_id=thread_id,
            thread_name=thread_name,
        )

    candidate_scores: list[tuple[str, float]] = []
    workflow_keywords: dict[str, tuple[str, ...]] = {
        "main": policy.routing_policy.main_keywords,
        **{
            workflow_name: _workflow_keywords(workflow_name, workflow_policy)
            for workflow_name, workflow_policy in policy.workflows.items()
        },
    }

    for workflow_name, keywords in workflow_keywords.items():
        hits = _matched_keywords(combined_text, keywords)
        score = float(len(hits))
        candidate_scores.append((workflow_name, score))

    ranked = sorted(candidate_scores, key=lambda item: (-item[1], item[0]))
    top_workflow, top_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0
    total_score = sum(score for _, score in ranked)
    confidence = top_score / total_score if total_score > 0 else 0.0
    confidence_gap = (top_score - second_score) / total_score if total_score > 0 else 0.0
    matched_workflows = [name for name, score in ranked if name != "main" and score > 0]
    cross_workflow = len(matched_workflows) >= 2

    if total_score <= 0:
        return ThreadRouteDecision(
            workflow=None,
            base_branch=None,
            topic_slug=None,
            branch=None,
            confidence=0.0,
            confidence_gap=0.0,
            routing_source="ask-user",
            routing_strategy="ask-user",
            needs_confirmation=True,
            recommended_workflow=None,
            candidate_scores=tuple((name, score) for name, score in ranked[:3]),
            matched_keywords=(),
            source_prompt_excerpt=excerpt,
            workspace_mode=workspace_mode,
            thread_id=thread_id,
            thread_name=thread_name,
        )

    top_hits = _matched_keywords(combined_text, workflow_keywords[top_workflow])
    auto_route = (
        confidence >= policy.routing_policy.confidence_threshold
        and confidence_gap >= policy.routing_policy.confidence_gap_threshold
        and not cross_workflow
    )
    if not auto_route:
        return ThreadRouteDecision(
            workflow=None,
            base_branch=None,
            topic_slug=None,
            branch=None,
            confidence=round(confidence, 3),
            confidence_gap=round(confidence_gap, 3),
            routing_source="ask-user",
            routing_strategy="ask-user",
            needs_confirmation=True,
            recommended_workflow=top_workflow,
            candidate_scores=tuple((name, score) for name, score in ranked[:3]),
            matched_keywords=tuple(top_hits),
            source_prompt_excerpt=excerpt,
            workspace_mode=workspace_mode,
            thread_id=thread_id,
            thread_name=thread_name,
        )

    resolved_workflow = top_workflow
    base_branch = "main" if resolved_workflow == "main" else policy.workflows[resolved_workflow].base_branch
    topic_slug = build_thread_topic_slug(
        thread_name=thread_name,
        prompt=prompt,
        thread_id=thread_id,
    )
    branch = f"codex/{resolved_workflow}/{topic_slug}"
    return ThreadRouteDecision(
        workflow=resolved_workflow,
        base_branch=base_branch,
        topic_slug=topic_slug,
        branch=branch,
        confidence=round(confidence, 3),
        confidence_gap=round(confidence_gap, 3),
        routing_source="classifier",
        routing_strategy="classifier",
        needs_confirmation=False,
        recommended_workflow=resolved_workflow,
        candidate_scores=tuple((name, score) for name, score in ranked[:3]),
        matched_keywords=tuple(top_hits),
        source_prompt_excerpt=excerpt,
        workspace_mode=workspace_mode,
        thread_id=thread_id,
        thread_name=thread_name,
    )


def render_task_pr_title(task: TaskContext) -> str:
    return f"{task.workflow}: {humanize_slug(task.topic_slug)}"


def render_task_issue_title(task: TaskContext) -> str:
    return f"Track {task.workflow} task: {humanize_slug(task.topic_slug)}"


def render_promotion_pr_title(workflow: str) -> str:
    return f"Promote {workflow} to main"


def render_promotion_issue_title(workflow: str) -> str:
    return f"Promote {workflow} branch to main"


def render_task_issue_payload(policy: WorkflowOwnershipPolicy, task: TaskContext) -> dict[str, Any]:
    return {
        "owner": task.repo_owner,
        "repo": task.repo_name,
        "title": render_task_issue_title(task),
        "body": render_task_issue_body(policy, task),
    }


def render_promotion_issue_payload(
    policy: WorkflowOwnershipPolicy,
    workflow: str,
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "owner": policy.repo.owner,
        "repo": policy.repo.name,
        "title": render_promotion_issue_title(workflow),
        "body": render_promotion_issue_body(workflow, snapshot),
    }


def build_task_pr_metadata(
    policy: WorkflowOwnershipPolicy,
    task: TaskContext,
    *,
    pr_snapshot: Mapping[str, Any] | None = None,
    thread_updated_at: Any = None,
    branch_updated_at: Any = None,
    pr_activity_at: Any = None,
    check_run_at: Any = None,
    conversation_state: str | None = None,
    archive_eligible: bool | None = None,
    blocked_reasons: Sequence[Any] | None = None,
) -> dict[str, Any]:
    pr_data = _mapping(pr_snapshot)
    existing = parse_task_pr_metadata(pr_data.get("body", ""))
    state = (
        conversation_state
        or str(pr_data.get("conversation_state") or existing.get("conversation_state") or task.conversation_state)
    )
    resolved_blocked_reasons = _string_list(
        blocked_reasons
        if blocked_reasons is not None
        else pr_data.get("blocked_reasons") or existing.get("blocked_reasons", [])
    )
    return {
        "workflow": task.workflow,
        "branch": task.branch,
        "base_branch": task.base_branch,
        "promotion_branch": task.promotion_branch,
        "thread_id": task.thread_id,
        "thread_name": task.thread_name,
        "routing_source": task.routing_source or task.routing_strategy or "manual",
        "routing_strategy": task.routing_strategy or task.routing_source or "manual",
        "routing_confidence": task.routing_confidence,
        "workspace_mode": task.workspace_mode,
        "conversation_state": state,
        "archive_eligible": bool(
            archive_eligible
            if archive_eligible is not None
            else pr_data.get("archive_eligible", existing.get("archive_eligible", task.archive_eligible))
        ),
        "last_thread_seen_at": _iso_timestamp(
            thread_updated_at
            or pr_data.get("thread_updated_at")
            or existing.get("last_thread_seen_at")
            or task.last_thread_seen_at
        ),
        "last_branch_seen_at": _iso_timestamp(
            branch_updated_at
            or pr_data.get("branch_updated_at")
            or pr_data.get("latest_commit_at")
            or existing.get("last_branch_seen_at")
        ),
        "last_pr_activity_at": _iso_timestamp(
            pr_activity_at or pr_data.get("updated_at") or existing.get("last_pr_activity_at")
        ),
        "last_check_run_at": _iso_timestamp(
            check_run_at or pr_data.get("latest_check_run_at") or existing.get("last_check_run_at")
        ),
        "blocked_reasons": resolved_blocked_reasons if state == "blocked" else [],
    }


def render_task_pr_metadata_block(metadata: Mapping[str, Any]) -> str:
    return (
        "<!-- concierge:task-metadata\n"
        f"{json.dumps(dict(metadata), indent=2, sort_keys=True)}\n"
        "-->"
    )


def parse_task_pr_metadata(body: Any) -> dict[str, Any]:
    match = TASK_METADATA_PATTERN.search(str(body or ""))
    if match is None:
        return {}
    try:
        parsed = json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return parsed


def strip_task_pr_metadata(body: Any) -> str:
    stripped = TASK_METADATA_PATTERN.sub("", str(body or ""))
    return stripped.strip()


def render_task_pr_body(
    policy: WorkflowOwnershipPolicy,
    task: TaskContext,
    metadata: Mapping[str, Any] | None = None,
) -> str:
    workflow = _resolve_workflow_policy(policy, task.workflow)
    context = {
        "workflow": task.workflow,
        "branch": task.branch,
        "base_branch": task.base_branch,
        "promotion_branch": task.promotion_branch,
        "topic_slug": task.topic_slug,
        "owned_paths_bullets": bullet_list(workflow.owned_paths),
        "issue_line": format_issue_line(task.issue_number),
        "task_metadata_block": render_task_pr_metadata_block(
            metadata or build_task_pr_metadata(policy, task)
        ),
    }
    return render_template("task_pr.md.tmpl", context)


def render_task_issue_body(policy: WorkflowOwnershipPolicy, task: TaskContext) -> str:
    workflow = _resolve_workflow_policy(policy, task.workflow)
    context = {
        "workflow": task.workflow,
        "branch": task.branch,
        "base_branch": task.base_branch,
        "promotion_branch": task.promotion_branch,
        "topic_slug": task.topic_slug,
        "owned_paths_bullets": bullet_list(workflow.owned_paths),
    }
    return render_template("task_issue.md.tmpl", context)


def render_promotion_pr_body(
    workflow: str,
    snapshot: Mapping[str, Any],
) -> str:
    linked_prs = snapshot.get("linked_task_prs", [])
    commits = snapshot.get("commit_summaries", [])
    context = {
        "workflow": workflow,
        "base_branch": str(snapshot.get("base_branch", f"dev/{workflow}")),
        "promotion_branch": str(snapshot.get("promotion_branch", "main")),
        "linked_task_prs_bullets": bullet_list(_format_linked_prs(linked_prs)),
        "commit_delta_bullets": bullet_list(_string_list(commits), fallback="- No commit summaries provided."),
        "release_notes_bullets": bullet_list(
            build_release_note_lines(linked_prs=linked_prs, commit_summaries=commits),
            fallback="- No release notes were derived from the snapshot.",
        ),
    }
    return render_template("promotion_pr.md.tmpl", context)


def render_promotion_issue_body(
    workflow: str,
    snapshot: Mapping[str, Any],
) -> str:
    context = {
        "workflow": workflow,
        "base_branch": str(snapshot.get("base_branch", f"dev/{workflow}")),
        "promotion_branch": str(snapshot.get("promotion_branch", "main")),
        "linked_task_prs_bullets": bullet_list(_format_linked_prs(snapshot.get("linked_task_prs", []))),
    }
    return render_template("promotion_issue.md.tmpl", context)


def render_template(template_name: str, values: Mapping[str, Any]) -> str:
    template_path = template_root() / template_name
    template = Template(template_path.read_text(encoding="utf-8"))
    rendered = template.safe_substitute({key: str(value) for key, value in values.items()})
    return rendered.strip() + "\n"


def plan_task_actions(
    policy: WorkflowOwnershipPolicy,
    task: TaskContext,
    snapshot: Mapping[str, Any],
) -> list[PlannedAction]:
    actions: list[PlannedAction] = []
    branch_pushed = bool(snapshot.get("branch_pushed", False))
    task_pr = _mapping(snapshot.get("task_pr"))
    policy_findings = list(snapshot.get("policy_findings", []))
    desired_metadata = build_task_pr_metadata(
        policy,
        task,
        pr_snapshot=task_pr,
        thread_updated_at=snapshot.get("thread_updated_at"),
        branch_updated_at=snapshot.get("branch_updated_at"),
        pr_activity_at=snapshot.get("pr_activity_at"),
        check_run_at=snapshot.get("latest_check_run_at"),
    )

    if not task_pr:
        if branch_pushed:
            actions.append(
                PlannedAction(
                    action_id="create_task_pr",
                    summary=f"Open the task PR for '{task.branch}' into '{task.base_branch}'.",
                    payload={
                        "owner": task.repo_owner,
                        "repo": task.repo_name,
                        "head": task.branch,
                        "base": task.base_branch,
                        "title": render_task_pr_title(task),
                        "body": render_task_pr_body(policy, task, metadata=desired_metadata),
                        "draft": False,
                    },
                )
            )
        return actions

    desired_title = render_task_pr_title(task)
    desired_body = render_task_pr_body(policy, task, metadata=desired_metadata)
    changed_fields: dict[str, Any] = {}
    if str(task_pr.get("title", "")) != desired_title:
        changed_fields["title"] = desired_title
    if str(task_pr.get("base_ref", task.base_branch)) != task.base_branch:
        changed_fields["base"] = task.base_branch
    if changed_fields and str(task_pr.get("state", "OPEN")).upper() == "OPEN":
        actions.append(
            PlannedAction(
                action_id="update_task_pr",
                summary=f"Sync the task PR metadata for '{task.branch}'.",
                payload={
                    "pull_number": int(task_pr["number"]),
                    "owner": task.repo_owner,
                    "repo": task.repo_name,
                    **changed_fields,
                },
            )
        )

    existing_metadata = parse_task_pr_metadata(task_pr.get("body", ""))
    if (
        strip_task_pr_metadata(task_pr.get("body", "")) != strip_task_pr_metadata(desired_body)
        or existing_metadata != desired_metadata
    ) and str(task_pr.get("state", "OPEN")).upper() == "OPEN":
        actions.append(
            PlannedAction(
                action_id="upsert_task_pr_metadata",
                summary=f"Upsert task PR metadata for '{task.branch}'.",
                payload={
                    "pull_number": int(task_pr["number"]),
                    "owner": task.repo_owner,
                    "repo": task.repo_name,
                    "body": desired_body,
                    "metadata": desired_metadata,
                },
            )
        )

    actions.extend(_plan_policy_comment_actions(task, task_pr, policy_findings))

    if (
        str(task_pr.get("state", "OPEN")).upper() == "OPEN"
        and not bool(task_pr.get("copilot_review_requested", False))
    ):
        actions.append(
            PlannedAction(
                action_id="request_copilot_review",
                summary=f"Request Copilot review for PR #{int(task_pr['number'])}.",
                payload={
                    "pull_number": int(task_pr["number"]),
                    "owner": task.repo_owner,
                    "repo": task.repo_name,
                },
            )
        )

    behind_base_by = int(task_pr.get("behind_base_by", 0) or 0)
    if behind_base_by > 0 and str(task_pr.get("state", "OPEN")).upper() == "OPEN":
        actions.append(
            PlannedAction(
                action_id="refresh_task_pr_branch",
                summary=f"Refresh task PR #{int(task_pr['number'])} with the latest '{task.base_branch}'.",
                payload={
                    "pull_number": int(task_pr["number"]),
                    "owner": task.repo_owner,
                    "repo": task.repo_name,
                    "behind_base_by": behind_base_by,
                },
            )
        )

    if _task_pr_ready_for_merge(policy=policy, pr_snapshot=task_pr, policy_findings=policy_findings):
        actions.append(
            PlannedAction(
                action_id="merge_task_pr",
                summary=f"Merge task PR #{int(task_pr['number'])} into '{task.base_branch}'.",
                payload={
                    "pull_number": int(task_pr["number"]),
                    "owner": task.repo_owner,
                    "repo": task.repo_name,
                },
            )
        )
        actions.extend(
            _post_merge_housekeeping_actions(
                policy=policy,
                task=task,
                pr_snapshot=task_pr,
            )
        )

    return actions


def plan_promotion_actions(
    policy: WorkflowOwnershipPolicy,
    workflow: str,
    snapshot: Mapping[str, Any],
) -> list[PlannedAction]:
    workflow_policy = policy.workflows[workflow]
    dev_branch = _mapping(snapshot.get("dev_branch"))
    ahead_by = int(dev_branch.get("ahead_by", snapshot.get("ahead_by", 0)) or 0)
    if ahead_by <= 0:
        return []

    promotion_pr = _mapping(snapshot.get("promotion_pr"))
    desired_title = render_promotion_pr_title(workflow)
    desired_body = render_promotion_pr_body(
        workflow,
        {
            **dict(snapshot),
            "base_branch": workflow_policy.base_branch,
            "promotion_branch": workflow_policy.promotion_target,
        },
    )

    if not promotion_pr:
        return [
            PlannedAction(
                action_id="open_promotion_pr",
                summary=f"Open the promotion PR for '{workflow_policy.base_branch}' into '{workflow_policy.promotion_target}'.",
                payload={
                    "owner": policy.repo.owner,
                    "repo": policy.repo.name,
                    "head": workflow_policy.base_branch,
                    "base": workflow_policy.promotion_target,
                    "title": desired_title,
                    "body": desired_body,
                    "draft": False,
                },
            )
        ]

    actions: list[PlannedAction] = []
    changed_fields: dict[str, Any] = {}
    if str(promotion_pr.get("title", "")) != desired_title:
        changed_fields["title"] = desired_title
    if str(promotion_pr.get("body", "")) != desired_body:
        changed_fields["body"] = desired_body
    if str(promotion_pr.get("base_ref", workflow_policy.promotion_target)) != workflow_policy.promotion_target:
        changed_fields["base"] = workflow_policy.promotion_target
    if changed_fields and str(promotion_pr.get("state", "OPEN")).upper() == "OPEN":
        actions.append(
            PlannedAction(
                action_id="update_promotion_pr",
                summary=f"Sync the promotion PR metadata for '{workflow}'.",
                payload={
                    "pull_number": int(promotion_pr["number"]),
                    "owner": policy.repo.owner,
                    "repo": policy.repo.name,
                    **changed_fields,
                },
            )
        )

    behind_base_by = int(promotion_pr.get("behind_base_by", 0) or 0)
    if behind_base_by > 0 and str(promotion_pr.get("state", "OPEN")).upper() == "OPEN":
        actions.append(
            PlannedAction(
                action_id="refresh_promotion_pr_branch",
                summary=f"Refresh promotion PR #{int(promotion_pr['number'])} with the latest '{workflow_policy.promotion_target}'.",
                payload={
                    "pull_number": int(promotion_pr["number"]),
                    "owner": policy.repo.owner,
                    "repo": policy.repo.name,
                    "behind_base_by": behind_base_by,
                },
            )
        )

    if _promotion_pr_ready_for_main(policy=policy, pr_snapshot=promotion_pr):
        actions.append(
            PlannedAction(
                action_id="prepare_main_merge",
                summary=f"Promotion PR #{int(promotion_pr['number'])} is ready for explicit main-branch approval.",
                payload={
                    "pull_number": int(promotion_pr["number"]),
                    "owner": policy.repo.owner,
                    "repo": policy.repo.name,
                    "base": workflow_policy.promotion_target,
                    "head": workflow_policy.base_branch,
                },
            )
        )

    return actions


def plan_drift_audit(
    policy: WorkflowOwnershipPolicy,
    snapshot: Mapping[str, Any],
) -> list[PlannedAction]:
    now = _parse_timestamp(snapshot.get("now")) or datetime.now(UTC)
    actions: list[PlannedAction] = []

    for branch in snapshot.get("open_task_branches", []):
        branch_data = _mapping(branch)
        if branch_data.get("has_pr", False):
            continue
        age_hours = hours_since(branch_data.get("updated_at"), now)
        workflow = workflow_from_branch(str(branch_data.get("branch", "")))
        if age_hours >= policy.audit_thresholds.orphaned_no_pr_archive_hours:
            actions.append(
                PlannedAction(
                    action_id="audit_orphaned_no_pr_task",
                    summary=f"Task branch '{branch_data['branch']}' is orphaned without a PR.",
                    payload={
                        "kind": "orphaned_no_pr",
                        "branch": str(branch_data["branch"]),
                        "workflow": workflow,
                        "age_hours": age_hours,
                        "archive_eligible": True,
                        "threshold_hours": policy.audit_thresholds.orphaned_no_pr_archive_hours,
                    },
                )
            )
            continue
        if age_hours >= policy.audit_thresholds.stale_branch_without_pr_hours:
            actions.append(
                PlannedAction(
                    action_id="audit_stale_task",
                    summary=f"Task branch '{branch_data['branch']}' has no PR and is stale.",
                    payload={
                        "kind": "branch_without_pr",
                        "branch": str(branch_data["branch"]),
                        "workflow": workflow,
                        "age_hours": age_hours,
                        "threshold_hours": policy.audit_thresholds.stale_branch_without_pr_hours,
                    },
                )
            )

    task_prs = list(snapshot.get("task_pull_requests", [])) or list(snapshot.get("open_task_prs", []))
    for pr in task_prs:
        pr_data = _mapping(pr)
        metadata = parse_task_pr_metadata(pr_data.get("body", ""))
        workflow = workflow_from_branch(str(pr_data.get("head_ref", ""))) or str(
            metadata.get("workflow", "")
        )
        conversation_state = str(
            pr_data.get("conversation_state")
            or metadata.get("conversation_state")
            or ("merged" if pr_data.get("merged_at") else "active")
        )
        archive_eligible = bool(
            pr_data.get("archive_eligible", metadata.get("archive_eligible", False))
        )
        blocked_summary = str(
            pr_data.get("blocked_summary")
            or metadata.get("blocked_summary")
            or ""
        ).strip()
        blocked_reasons = _string_list(
            pr_data.get("blocked_reasons") or metadata.get("blocked_reasons", [])
        )
        if conversation_state == "merged" and archive_eligible:
            actions.append(
                PlannedAction(
                    action_id="audit_archive_eligible_task",
                    summary=f"Merged task PR #{int(pr_data['number'])} is ready for archive handling.",
                    payload={
                        "kind": "merged_task_pr",
                        "pull_number": int(pr_data["number"]),
                        "branch": str(pr_data.get("head_ref", "")),
                        "workflow": workflow,
                        "archive_eligible": True,
                    },
                )
            )
            continue
        if conversation_state == "blocked" and archive_eligible:
            actions.append(
                PlannedAction(
                    action_id="audit_archive_eligible_task",
                    summary=f"Blocked task PR #{int(pr_data['number'])} is archive-eligible.",
                    payload={
                        "kind": "blocked_task_pr",
                        "pull_number": int(pr_data["number"]),
                        "branch": str(pr_data.get("head_ref", "")),
                        "workflow": workflow,
                        "blocked_summary": blocked_summary,
                        "blocked_reasons": blocked_reasons,
                        "archive_eligible": True,
                    },
                )
            )
            continue
        if bool(pr_data.get("draft", False)) and blocked_summary:
            actions.append(
                PlannedAction(
                    action_id="audit_blocked_task_pr",
                    summary=f"Task PR #{int(pr_data['number'])} remains blocked.",
                    payload={
                        "pull_number": int(pr_data["number"]),
                        "branch": str(pr_data.get("head_ref", "")),
                        "workflow": workflow,
                        "blocked_summary": blocked_summary,
                        "blocked_reasons": blocked_reasons,
                    },
                )
            )
            continue
        if str(pr_data.get("state", "OPEN")).upper() != "OPEN":
            continue
        age_hours = hours_since(pr_data.get("updated_at"), now)
        failing = bool(pr_data.get("failing_checks", False))
        threshold = (
            policy.audit_thresholds.stale_failing_task_pr_hours
            if failing
            else policy.audit_thresholds.stale_open_task_pr_hours
        )
        if age_hours >= threshold:
            actions.append(
                PlannedAction(
                    action_id="audit_stale_task",
                    summary=f"Task PR #{int(pr_data['number'])} requires attention.",
                    payload={
                        "kind": "failing_task_pr" if failing else "stale_task_pr",
                        "pull_number": int(pr_data["number"]),
                        "branch": str(pr_data.get("head_ref", "")),
                        "workflow": workflow,
                        "age_hours": age_hours,
                        "threshold_hours": threshold,
                    },
                )
            )

    promotion_prs = {
        str(_mapping(pr).get("head_ref", "")): _mapping(pr)
        for pr in snapshot.get("promotion_prs", [])
        if str(_mapping(pr).get("state", "OPEN")).upper() == "OPEN"
    }
    for workflow_name, workflow_policy in policy.workflows.items():
        branch_state = _mapping(_mapping(snapshot.get("workflow_branches", {})).get(workflow_name))
        ahead_by = int(branch_state.get("ahead_by", 0) or 0)
        if ahead_by > 0 and workflow_policy.base_branch not in promotion_prs:
            actions.append(
                PlannedAction(
                    action_id="audit_missing_promotion_pr",
                    summary=f"'{workflow_policy.base_branch}' is ahead of main without an open promotion PR.",
                    payload={
                        "workflow": workflow_name,
                        "branch": workflow_policy.base_branch,
                        "ahead_by": ahead_by,
                    },
                )
            )

    for pr in promotion_prs.values():
        behind_base_by = int(pr.get("behind_base_by", 0) or 0)
        if behind_base_by > 0:
            actions.append(
                PlannedAction(
                    action_id="audit_promotion_out_of_date",
                    summary=f"Promotion PR #{int(pr['number'])} is behind base and should be refreshed.",
                    payload={
                        "pull_number": int(pr["number"]),
                        "branch": str(pr.get("head_ref", "")),
                        "behind_base_by": behind_base_by,
                    },
                )
            )

    return actions


def plan_merge_checker(
    policy: WorkflowOwnershipPolicy,
    snapshot: Mapping[str, Any],
) -> list[PlannedAction]:
    now = _parse_timestamp(snapshot.get("now")) or datetime.now(UTC)
    actions: list[PlannedAction] = []

    for raw_branch in snapshot.get("task_branches_without_pr", []):
        branch = _mapping(raw_branch)
        age_hours = hours_since(branch.get("updated_at"), now)
        if age_hours < policy.audit_thresholds.stale_branch_without_pr_hours:
            continue
        archive_eligible = age_hours >= policy.audit_thresholds.orphaned_no_pr_archive_hours
        actions.append(
            PlannedAction(
                action_id="report_orphaned_no_pr_task",
                summary=f"Task branch '{branch.get('branch', '')}' is stale without a PR.",
                payload={
                    "branch": str(branch.get("branch", "")),
                    "workflow": workflow_from_branch(str(branch.get("branch", ""))),
                    "age_hours": age_hours,
                    "archive_eligible": archive_eligible,
                    "threshold_hours": policy.audit_thresholds.stale_branch_without_pr_hours,
                },
            )
        )

    for raw_pr in snapshot.get("task_pull_requests", []):
        pr = _mapping(raw_pr)
        if str(pr.get("state", "OPEN")).upper() != "OPEN":
            continue
        head_ref = str(pr.get("head_ref", ""))
        base_ref = str(pr.get("base_ref", ""))
        if not head_ref.startswith("codex/") or not base_ref.startswith("dev/"):
            continue

        latest_activity = latest_activity_at(pr)
        inactivity_hours = hours_since(latest_activity, now)
        if inactivity_hours < policy.merge_checker_policy.inactivity_hours:
            continue

        if _task_pr_passes_merge_checker(policy, pr):
            behind_base_by = int(pr.get("behind_base_by", 0) or 0)
            if behind_base_by > 0:
                actions.append(
                    PlannedAction(
                        action_id="refresh_task_pr_branch",
                        summary=f"Refresh quiet task PR #{int(pr['number'])} before merge.",
                        payload={
                            "pull_number": int(pr["number"]),
                            "owner": policy.repo.owner,
                            "repo": policy.repo.name,
                            "behind_base_by": behind_base_by,
                            "inactivity_hours": inactivity_hours,
                        },
                    )
                )
                continue

            actions.append(
                PlannedAction(
                    action_id="merge_task_pr",
                    summary=f"Auto-merge quiet task PR #{int(pr['number'])} into '{base_ref}'.",
                    payload={
                        "pull_number": int(pr["number"]),
                        "owner": policy.repo.owner,
                        "repo": policy.repo.name,
                        "inactivity_hours": inactivity_hours,
                    },
                )
            )
            actions.extend(
                _post_merge_housekeeping_actions_for_pr(
                    policy=policy,
                    pr_snapshot=pr,
                    inactivity_hours=inactivity_hours,
                )
            )
            continue

        actions.extend(
            _plan_blocked_task_actions(
                policy=policy,
                pr_snapshot=pr,
                inactivity_hours=inactivity_hours,
                latest_activity=latest_activity,
            )
        )

    return actions


def plan_security_audit(
    policy: WorkflowOwnershipPolicy,
    snapshot: Mapping[str, Any],
) -> list[PlannedAction]:
    actions: list[PlannedAction] = []
    for pr in snapshot.get("pull_requests", []):
        pr_data = _mapping(pr)
        if str(pr_data.get("state", "OPEN")).upper() != "OPEN":
            continue
        kind = (
            "promotion"
            if str(pr_data.get("base_ref", "")) == policy.promotion_target
            else "task"
        )
        actions.append(
            PlannedAction(
                action_id="audit_security_scan",
                summary=f"Run secret scanning for {kind} PR #{int(pr_data['number'])}.",
                payload={
                    "pull_number": int(pr_data["number"]),
                    "owner": policy.repo.owner,
                    "repo": policy.repo.name,
                    "kind": kind,
                    "head_ref": str(pr_data.get("head_ref", "")),
                    "base_ref": str(pr_data.get("base_ref", "")),
                },
            )
        )
    return actions


def plan_release_audit(
    policy: WorkflowOwnershipPolicy,
    snapshot: Mapping[str, Any],
) -> list[PlannedAction]:
    current_version = str(snapshot.get("current_version") or read_project_version())
    tags = [str(tag) for tag in snapshot.get("tags", [])]
    commit_summaries = _string_list(snapshot.get("commits_since_latest_tag", []))
    main_branch = _mapping(snapshot.get("main_branch"))
    ahead_by = int(main_branch.get("ahead_by", 0) or 0)
    latest_tag = latest_semver_tag(tags, tag_prefix=policy.release_policy.tag_prefix)

    if ahead_by <= 0 and not commit_summaries and latest_tag is not None:
        return []

    next_tag = compute_next_semver_tag(
        existing_tags=tags,
        current_version=current_version,
        tag_prefix=policy.release_policy.tag_prefix,
    )
    release_notes = build_release_note_lines(
        linked_prs=snapshot.get("merged_promotions", []),
        commit_summaries=commit_summaries,
    )
    return [
        PlannedAction(
            action_id="audit_release_ready",
            summary=f"Main is ahead of the latest release tag; the next candidate tag is '{next_tag}'.",
            payload={
                "owner": policy.repo.owner,
                "repo": policy.repo.name,
                "current_version": current_version,
                "latest_tag": latest_tag,
                "next_tag": next_tag,
                "release_notes": release_notes,
            },
        )
    ]


def compute_next_semver_tag(
    *,
    existing_tags: Sequence[str],
    current_version: str,
    tag_prefix: str = "v",
) -> str:
    current = parse_semver(current_version)
    versions = [version for tag in existing_tags if (version := parse_semver(tag)) is not None]
    if not versions:
        return f"{tag_prefix}{current_version}"

    highest = max(versions)
    if highest < current:
        return f"{tag_prefix}{current_version}"

    bumped = (highest[0], highest[1], highest[2] + 1)
    return f"{tag_prefix}{bumped[0]}.{bumped[1]}.{bumped[2]}"


def latest_semver_tag(existing_tags: Sequence[str], *, tag_prefix: str = "v") -> str | None:
    tagged_versions: list[tuple[tuple[int, int, int], str]] = []
    for tag in existing_tags:
        parsed = parse_semver(tag)
        if parsed is None:
            continue
        tagged_versions.append((parsed, tag if tag.startswith(tag_prefix) else f"{tag_prefix}{tag}"))
    if not tagged_versions:
        return None
    return max(tagged_versions, key=lambda item: item[0])[1]


def parse_semver(value: str) -> tuple[int, int, int] | None:
    match = SEMVER_PATTERN.match(value.strip())
    if not match:
        return None
    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
    )


def read_project_version(path: str | Path | None = None) -> str:
    pyproject_path = Path(path) if path is not None else repo_root() / "pyproject.toml"
    pattern = re.compile(r'^version\s*=\s*"([^"]+)"$', re.MULTILINE)
    match = pattern.search(pyproject_path.read_text(encoding="utf-8"))
    if match is None:
        raise ValueError(f"Could not find project version in '{pyproject_path}'.")
    return match.group(1)


def actions_to_json(actions: Sequence[PlannedAction]) -> str:
    return json.dumps([action.to_dict() for action in actions], indent=2, sort_keys=True)


def humanize_slug(value: str) -> str:
    words = [segment for segment in value.replace("_", "-").split("-") if segment]
    return " ".join(word.capitalize() for word in words) or value


def bullet_list(items: Sequence[str], *, fallback: str = "- None declared.") -> str:
    if not items:
        return fallback
    return "\n".join(f"- {item}" for item in items)


def format_issue_line(issue_number: int | None) -> str:
    if issue_number is None:
        return "- Linked issue: none"
    return f"- Linked issue: #{issue_number}"


def build_release_note_lines(
    *,
    linked_prs: Sequence[Any],
    commit_summaries: Sequence[str],
) -> list[str]:
    lines = _format_linked_prs(linked_prs)
    if lines:
        return lines
    return _string_list(commit_summaries)


def build_fingerprint(code: str, path: str | None, message: str) -> str:
    sanitized_message = re.sub(r"[^a-z0-9._-]+", "-", message.lower()).strip("-")[:48]
    sanitized_path = re.sub(r"[^a-z0-9._/-]+", "-", (path or "general").lower()).strip("-")
    return f"{code}:{sanitized_path}:{sanitized_message}"


def build_blocked_marker(*, head_ref: str, reasons: Sequence[str]) -> str:
    sanitized_branch = re.sub(r"[^a-z0-9._/-]+", "-", head_ref.lower()).strip("-")
    reason_slug = "-".join(
        re.sub(r"[^a-z0-9._-]+", "-", reason.lower()).strip("-") for reason in reasons
    )[:80]
    return f"blocked:{sanitized_branch}:{reason_slug}"


def fingerprint_marker(fingerprint: str) -> str:
    return f"<!-- concierge:fingerprint={fingerprint} -->"


def blocked_marker_comment(marker: str) -> str:
    return f"<!-- concierge:blocked={marker} -->"


def extract_comment_fingerprints(comments: Sequence[Any]) -> set[str]:
    fingerprints: set[str] = set()
    for comment in comments:
        body = str(_mapping(comment).get("body", ""))
        for match in FINGERPRINT_PATTERN.finditer(body):
            fingerprints.add(match.group(1))
    return fingerprints


def extract_blocked_markers(comments: Sequence[Any]) -> set[str]:
    markers: set[str] = set()
    for comment in comments:
        body = str(_mapping(comment).get("body", ""))
        for match in BLOCKED_PATTERN.finditer(body):
            markers.add(match.group(1))
    return markers


def hours_since(value: Any, now: datetime) -> int:
    timestamp = _parse_timestamp(value)
    if timestamp is None:
        return 0
    delta = now - timestamp
    return max(int(delta.total_seconds() // 3600), 0)


def latest_activity_at(pr_snapshot: Mapping[str, Any]) -> str | None:
    metadata = parse_task_pr_metadata(pr_snapshot.get("body", ""))
    timestamps = [
        _parse_timestamp(pr_snapshot.get("thread_updated_at") or metadata.get("last_thread_seen_at")),
        _parse_timestamp(pr_snapshot.get("branch_updated_at") or metadata.get("last_branch_seen_at")),
        _parse_timestamp(pr_snapshot.get("updated_at") or metadata.get("last_pr_activity_at")),
        _parse_timestamp(pr_snapshot.get("latest_comment_at")),
        _parse_timestamp(pr_snapshot.get("latest_review_at")),
        _parse_timestamp(pr_snapshot.get("latest_check_run_at") or metadata.get("last_check_run_at")),
    ]
    timestamps = [timestamp for timestamp in timestamps if timestamp is not None]
    if not timestamps:
        return None
    return max(timestamps).isoformat()


def _parse_timestamp(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _plan_policy_comment_actions(
    task: TaskContext,
    pr_snapshot: Mapping[str, Any],
    findings: Sequence[Any],
) -> list[PlannedAction]:
    changed_paths = {
        str(item)
        for item in pr_snapshot.get("changed_paths", [])
        if str(item)
    }
    for file_info in pr_snapshot.get("files", []):
        file_data = _mapping(file_info)
        path = str(file_data.get("path", ""))
        if path:
            changed_paths.add(path)

    existing_fingerprints = extract_comment_fingerprints(
        list(pr_snapshot.get("comments", [])) + list(pr_snapshot.get("review_comments", []))
    )
    actions: list[PlannedAction] = []
    for raw_finding in findings:
        finding = _mapping(raw_finding)
        message = str(finding.get("message", "")).strip()
        if not message:
            continue
        path = str(finding.get("path", "") or "") or None
        code = str(finding.get("code", "policy"))
        title = str(finding.get("title", "Policy finding"))
        fingerprint = str(finding.get("fingerprint") or build_fingerprint(code, path, message))
        if fingerprint in existing_fingerprints:
            continue

        body = f"**{title}**\n\n{message}\n\n{fingerprint_marker(fingerprint)}"
        payload: dict[str, Any] = {
            "pull_number": int(pr_snapshot["number"]),
            "owner": task.repo_owner,
            "repo": task.repo_name,
            "fingerprint": fingerprint,
            "body": body,
        }
        if path and path in changed_paths:
            payload.update(
                {
                    "comment_kind": "inline_review",
                    "path": path,
                    "subject_type": "file",
                }
            )
        else:
            payload["comment_kind"] = "general"
        actions.append(
            PlannedAction(
                action_id="comment_policy_failure",
                summary=f"Comment on unresolved policy finding '{title}'.",
                payload=payload,
            )
        )
    return actions


def _plan_blocked_task_actions(
    *,
    policy: WorkflowOwnershipPolicy,
    pr_snapshot: Mapping[str, Any],
    inactivity_hours: int,
    latest_activity: str | None,
) -> list[PlannedAction]:
    reasons = _blocked_reasons(policy, pr_snapshot)
    if not reasons:
        return []

    metadata = parse_task_pr_metadata(pr_snapshot.get("body", ""))
    blocked_marker = build_blocked_marker(
        head_ref=str(pr_snapshot.get("head_ref", "")),
        reasons=reasons,
    )
    archive_eligible = (
        inactivity_hours >= policy.merge_checker_policy.blocked_archive_hours
    )
    blocked_summary = (
        "**Blocked by merge checker**\n\n"
        f"- Inactivity window: {inactivity_hours} hours\n"
        f"- Latest activity: {latest_activity or 'unknown'}\n"
        f"- Reasons: {', '.join(reasons)}\n\n"
        f"{blocked_marker_comment(blocked_marker)}"
    )
    desired_metadata = {
        **metadata,
        "workflow": workflow_from_branch(str(pr_snapshot.get("head_ref", ""))) or metadata.get("workflow"),
        "branch": str(pr_snapshot.get("head_ref", "")),
        "base_branch": str(pr_snapshot.get("base_ref", "")),
        "thread_id": metadata.get("thread_id"),
        "thread_name": metadata.get("thread_name"),
        "routing_source": metadata.get("routing_source"),
        "routing_strategy": metadata.get("routing_strategy"),
        "routing_confidence": metadata.get("routing_confidence"),
        "workspace_mode": metadata.get("workspace_mode", "current"),
        "conversation_state": "blocked",
        "archive_eligible": archive_eligible,
        "last_thread_seen_at": metadata.get("last_thread_seen_at"),
        "last_branch_seen_at": _iso_timestamp(
            pr_snapshot.get("branch_updated_at")
            or pr_snapshot.get("latest_commit_at")
            or metadata.get("last_branch_seen_at")
        ),
        "last_pr_activity_at": _iso_timestamp(
            pr_snapshot.get("updated_at") or metadata.get("last_pr_activity_at")
        ),
        "last_check_run_at": _iso_timestamp(
            pr_snapshot.get("latest_check_run_at") or metadata.get("last_check_run_at")
        ),
        "blocked_reasons": reasons,
    }
    desired_body = upsert_task_pr_metadata(pr_snapshot.get("body", ""), desired_metadata)

    actions: list[PlannedAction] = []
    if desired_metadata != metadata:
        actions.append(
            PlannedAction(
                action_id="upsert_task_pr_metadata",
                summary=f"Update task PR #{int(pr_snapshot['number'])} lifecycle metadata.",
                payload={
                    "pull_number": int(pr_snapshot["number"]),
                    "owner": policy.repo.owner,
                    "repo": policy.repo.name,
                    "body": desired_body,
                    "metadata": desired_metadata,
                },
            )
        )
    if not bool(pr_snapshot.get("draft", False)):
        actions.append(
            PlannedAction(
                action_id="mark_task_pr_blocked",
                summary=f"Mark quiet task PR #{int(pr_snapshot['number'])} as blocked/draft.",
                payload={
                    "pull_number": int(pr_snapshot["number"]),
                    "owner": policy.repo.owner,
                    "repo": policy.repo.name,
                    "draft": True,
                    "blocked_reasons": reasons,
                },
            )
        )

    existing_markers = extract_blocked_markers(pr_snapshot.get("comments", []))
    if blocked_marker not in existing_markers:
        actions.append(
            PlannedAction(
                action_id="comment_blocked_task_pr",
                summary=f"Summarize why quiet task PR #{int(pr_snapshot['number'])} is blocked.",
                payload={
                    "pull_number": int(pr_snapshot["number"]),
                    "owner": policy.repo.owner,
                    "repo": policy.repo.name,
                    "body": blocked_summary,
                    "blocked_marker": blocked_marker,
                    "blocked_reasons": reasons,
                    "inactivity_hours": inactivity_hours,
                },
            )
        )
    if archive_eligible:
        actions.append(
            PlannedAction(
                action_id="report_archive_eligible_task",
                summary=f"Blocked task PR #{int(pr_snapshot['number'])} is archive-eligible.",
                payload={
                    "kind": "blocked_task_pr",
                    "pull_number": int(pr_snapshot["number"]),
                    "branch": str(pr_snapshot.get("head_ref", "")),
                    "workflow": workflow_from_branch(str(pr_snapshot.get("head_ref", ""))),
                    "archive_eligible": True,
                    "blocked_reasons": reasons,
                    "inactivity_hours": inactivity_hours,
                },
            )
        )
    return actions


def _post_merge_housekeeping_actions(
    *,
    policy: WorkflowOwnershipPolicy,
    task: TaskContext,
    pr_snapshot: Mapping[str, Any],
) -> list[PlannedAction]:
    metadata = build_task_pr_metadata(
        policy,
        task,
        pr_snapshot=pr_snapshot,
        conversation_state="merged",
        archive_eligible=True,
    )
    return [
        PlannedAction(
            action_id="finalize_merged_task_pr",
            summary=f"Finalize merged task PR #{int(pr_snapshot['number'])} metadata.",
            payload={
                "pull_number": int(pr_snapshot["number"]),
                "owner": task.repo_owner,
                "repo": task.repo_name,
                "body": render_task_pr_body(policy, task, metadata=metadata),
                "metadata": metadata,
            },
        ),
        PlannedAction(
            action_id="delete_task_branch",
            summary=f"Delete merged task branch '{task.branch}'.",
            payload={
                "branch": task.branch,
                "owner": task.repo_owner,
                "repo": task.repo_name,
            },
        ),
        PlannedAction(
            action_id="report_archive_eligible_task",
            summary=f"Merged task PR #{int(pr_snapshot['number'])} is ready for archive handling.",
            payload={
                "kind": "merged_task_pr",
                "pull_number": int(pr_snapshot["number"]),
                "branch": task.branch,
                "workflow": task.workflow,
                "archive_eligible": True,
            },
        ),
    ]


def _post_merge_housekeeping_actions_for_pr(
    *,
    policy: WorkflowOwnershipPolicy,
    pr_snapshot: Mapping[str, Any],
    inactivity_hours: int,
) -> list[PlannedAction]:
    metadata = parse_task_pr_metadata(pr_snapshot.get("body", ""))
    metadata.update(
        {
            "workflow": workflow_from_branch(str(pr_snapshot.get("head_ref", ""))) or metadata.get("workflow"),
            "branch": str(pr_snapshot.get("head_ref", "")),
            "base_branch": str(pr_snapshot.get("base_ref", "")),
            "conversation_state": "merged",
            "archive_eligible": True,
            "last_pr_activity_at": _iso_timestamp(pr_snapshot.get("updated_at") or metadata.get("last_pr_activity_at")),
            "last_check_run_at": _iso_timestamp(pr_snapshot.get("latest_check_run_at") or metadata.get("last_check_run_at")),
        }
    )
    return [
        PlannedAction(
            action_id="finalize_merged_task_pr",
            summary=f"Finalize merged task PR #{int(pr_snapshot['number'])} metadata.",
            payload={
                "pull_number": int(pr_snapshot["number"]),
                "owner": policy.repo.owner,
                "repo": policy.repo.name,
                "body": upsert_task_pr_metadata(pr_snapshot.get("body", ""), metadata),
                "metadata": metadata,
                "inactivity_hours": inactivity_hours,
            },
        ),
        PlannedAction(
            action_id="delete_task_branch",
            summary=f"Delete merged task branch '{str(pr_snapshot.get('head_ref', ''))}'.",
            payload={
                "branch": str(pr_snapshot.get("head_ref", "")),
                "owner": policy.repo.owner,
                "repo": policy.repo.name,
            },
        ),
        PlannedAction(
            action_id="report_archive_eligible_task",
            summary=f"Merged task PR #{int(pr_snapshot['number'])} is ready for archive handling.",
            payload={
                "kind": "merged_task_pr",
                "pull_number": int(pr_snapshot["number"]),
                "branch": str(pr_snapshot.get("head_ref", "")),
                "workflow": workflow_from_branch(str(pr_snapshot.get("head_ref", ""))),
                "archive_eligible": True,
                "inactivity_hours": inactivity_hours,
            },
        ),
    ]


def _task_pr_ready_for_merge(
    *,
    policy: WorkflowOwnershipPolicy,
    pr_snapshot: Mapping[str, Any],
    policy_findings: Sequence[Any],
) -> bool:
    if str(pr_snapshot.get("state", "OPEN")).upper() != "OPEN":
        return False
    if bool(pr_snapshot.get("draft", False)):
        return False
    if policy_findings:
        return False
    if str(pr_snapshot.get("base_ref", "")).startswith("dev/") is False:
        return False
    if not policy.pr_policy.auto_merge_to_dev:
        return False
    if int(pr_snapshot.get("behind_base_by", 0) or 0) > 0:
        return False
    if bool(pr_snapshot.get("copilot_review_requested", False)) and not bool(
        pr_snapshot.get("copilot_review_completed", False)
    ):
        return False
    if str(pr_snapshot.get("review_decision", "")).upper() == "CHANGES_REQUESTED":
        return False
    return _checks_green(pr_snapshot.get("check_runs", []))


def _task_pr_passes_merge_checker(
    policy: WorkflowOwnershipPolicy,
    pr_snapshot: Mapping[str, Any],
) -> bool:
    metadata = parse_task_pr_metadata(pr_snapshot.get("body", ""))
    if str(pr_snapshot.get("state", "OPEN")).upper() != "OPEN":
        return False
    if bool(pr_snapshot.get("draft", False)):
        return False
    if bool(pr_snapshot.get("archive_eligible", metadata.get("archive_eligible", False))):
        return False
    if not policy.pr_policy.auto_merge_to_dev:
        return False
    if str(pr_snapshot.get("review_decision", "")).upper() == "CHANGES_REQUESTED":
        return False
    if not _named_check_green(pr_snapshot.get("check_runs", []), "Branch Ownership"):
        return False

    workflow = str(pr_snapshot.get("base_ref", "")).removeprefix("dev/")
    if not workflow or not _named_check_green(
        pr_snapshot.get("check_runs", []), f"Fast Checks ({workflow})"
    ):
        return False

    contract_checks_passed = pr_snapshot.get("contract_checks_passed")
    if contract_checks_passed is False:
        return False

    return True


def _promotion_pr_ready_for_main(
    *,
    policy: WorkflowOwnershipPolicy,
    pr_snapshot: Mapping[str, Any],
) -> bool:
    if str(pr_snapshot.get("state", "OPEN")).upper() != "OPEN":
        return False
    if bool(pr_snapshot.get("draft", False)):
        return False
    if not policy.pr_policy.manual_merge_to_main:
        return False
    if int(pr_snapshot.get("behind_base_by", 0) or 0) > 0:
        return False
    if str(pr_snapshot.get("review_decision", "")).upper() == "CHANGES_REQUESTED":
        return False
    return _checks_green(pr_snapshot.get("check_runs", []))


def _checks_green(check_runs: Sequence[Any]) -> bool:
    if not check_runs:
        return False
    for raw_check in check_runs:
        check = _mapping(raw_check)
        if str(check.get("status", "")).lower() != "completed":
            return False
        conclusion = str(check.get("conclusion", "")).lower()
        if conclusion not in {"success", "neutral", "skipped"}:
            return False
    return True


def _named_check_green(check_runs: Sequence[Any], name: str) -> bool:
    for raw_check in check_runs:
        check = _mapping(raw_check)
        if str(check.get("name", "")).strip() != name:
            continue
        if str(check.get("status", "")).lower() != "completed":
            return False
        return str(check.get("conclusion", "")).lower() in {"success", "neutral", "skipped"}
    return False


def _blocked_reasons(
    policy: WorkflowOwnershipPolicy,
    pr_snapshot: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []
    if not _named_check_green(pr_snapshot.get("check_runs", []), "Branch Ownership"):
        reasons.append("branch-ownership")
    workflow = str(pr_snapshot.get("base_ref", "")).removeprefix("dev/")
    if workflow and not _named_check_green(
        pr_snapshot.get("check_runs", []), f"Fast Checks ({workflow})"
    ):
        reasons.append("workflow-fast-checks")
    if pr_snapshot.get("contract_checks_passed") is False:
        reasons.append("contract-readiness")
    if int(pr_snapshot.get("behind_base_by", 0) or 0) > 0:
        reasons.append("behind-base")
    if str(pr_snapshot.get("review_decision", "")).upper() == "CHANGES_REQUESTED":
        reasons.append("changes-requested")
    if not reasons and not _task_pr_passes_merge_checker(policy, pr_snapshot):
        reasons.append("merge-gate")
    return reasons


def _format_linked_prs(items: Sequence[Any]) -> list[str]:
    lines: list[str] = []
    for raw_item in items:
        item = _mapping(raw_item)
        number = item.get("number")
        title = str(item.get("title", "")).strip()
        if number is not None and title:
            lines.append(f"PR #{int(number)} - {title}")
        elif number is not None:
            lines.append(f"PR #{int(number)}")
        elif title:
            lines.append(title)
    return lines


def _string_list(items: Sequence[Any]) -> list[str]:
    lines: list[str] = []
    for item in items:
        if isinstance(item, Mapping):
            message = str(item.get("message") or item.get("title") or "").strip()
            if message:
                lines.append(message)
            continue
        text = str(item).strip()
        if text:
            lines.append(text)
    return lines


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def workflow_from_branch(branch: str) -> str:
    parts = str(branch).split("/")
    if len(parts) >= 2 and parts[0] in {"codex", "dev"}:
        return parts[1]
    if branch == "main":
        return "main"
    return ""


def _resolve_workflow_policy(
    policy: WorkflowOwnershipPolicy,
    workflow: str,
) -> WorkflowPolicy:
    if workflow == "main":
        return WorkflowPolicy(
            name="main",
            base_branch="main",
            promotion_target="main",
            routing_keywords=policy.routing_policy.main_keywords,
            owned_paths=policy.main_only_paths + policy.shared_contract_paths,
            exclude_paths=(),
        )
    return policy.workflows[workflow]


def _workflow_keywords(workflow_name: str, workflow_policy: WorkflowPolicy) -> tuple[str, ...]:
    aliases = {
        workflow_name,
        workflow_name.replace("-", " "),
        workflow_name.replace("-", ""),
    }
    return tuple(dict.fromkeys([*aliases, *workflow_policy.routing_keywords]))


def _matched_keywords(text: str, keywords: Sequence[str]) -> list[str]:
    normalized_text = normalize_text(text)
    hits: list[str] = []
    for keyword in keywords:
        normalized_keyword = normalize_text(keyword)
        if not normalized_keyword:
            continue
        if normalized_keyword in normalized_text:
            hits.append(keyword)
    return list(dict.fromkeys(hits))


def _detect_explicit_workflow_marker(
    policy: WorkflowOwnershipPolicy,
    text: str,
) -> dict[str, Any]:
    valid_workflows = {"main", *policy.workflows.keys()}
    token_prefix = policy.routing_policy.explicit_token_prefix
    token_prefix_normalized = normalize_text(token_prefix)
    normalized_text = normalize_text(text)
    matched_markers: list[str] = []
    matched_workflows: list[str] = []

    token_pattern = re.compile(
        rf"{re.escape(token_prefix)}\s*([a-z0-9][a-z0-9-]*)",
        re.IGNORECASE,
    )
    for match in token_pattern.finditer(str(text or "")):
        raw_value = match.group(1).strip()
        workflow = _normalize_workflow_name(raw_value, valid_workflows)
        matched_markers.append(f"{policy.routing_policy.explicit_token_prefix}{raw_value}")
        if workflow:
            matched_workflows.append(workflow)
        else:
            return {
                "needs_confirmation": True,
                "matched_markers": matched_markers,
                "recommended_workflow": None,
            }

    phrase_matches: list[tuple[str, str]] = []
    for workflow in valid_workflows:
        for alias in _workflow_aliases(workflow):
            for template in policy.routing_policy.explicit_phrase_templates:
                phrase = normalize_text(template.format(workflow=alias))
                if phrase and phrase in normalized_text:
                    phrase_matches.append((workflow, template.format(workflow=alias)))
    if phrase_matches:
        matched_markers.extend(marker for _, marker in phrase_matches)
        matched_workflows.extend(workflow for workflow, _ in phrase_matches)

    normalized_workflows = list(dict.fromkeys(matched_workflows))
    if len(normalized_workflows) > 1:
        return {
            "needs_confirmation": True,
            "matched_markers": matched_markers,
            "recommended_workflow": normalized_workflows[0],
        }
    if len(normalized_workflows) == 1:
        routing_source = "explicit_token" if any(
            normalize_text(marker).startswith(token_prefix_normalized) for marker in matched_markers
        ) else "explicit_phrase"
        return {
            "needs_confirmation": False,
            "workflow": normalized_workflows[0],
            "routing_source": routing_source,
            "matched_markers": matched_markers,
        }
    return {"needs_confirmation": False, "workflow": None}


def _workflow_aliases(workflow: str) -> tuple[str, ...]:
    aliases = {
        workflow,
        workflow.replace("-", " "),
        workflow.replace("-", ""),
    }
    return tuple(dict.fromkeys(alias for alias in aliases if alias))


def _normalize_workflow_name(value: str, valid_workflows: set[str]) -> str | None:
    for workflow in valid_workflows:
        if normalize_text(value) in {normalize_text(alias) for alias in _workflow_aliases(workflow)}:
            return workflow
    return None


def normalize_text(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def _iso_timestamp(value: Any) -> str | None:
    parsed = _parse_timestamp(value)
    if parsed is None:
        return None
    return parsed.isoformat()


def slugify_topic(value: str) -> str:
    slug = re.sub(r"[^a-z0-9._-]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug or "task"


def trim_excerpt(value: str, *, limit: int) -> str:
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return text[: max(limit - 3, 1)].rstrip() + "..."


def build_thread_topic_slug(
    *,
    thread_name: str | None,
    prompt: str,
    thread_id: str | None = None,
) -> str:
    basis = thread_name or prompt
    words = normalize_text(basis).split()
    topic_root = "-".join(words[:8]) if words else "task"
    topic_root = slugify_topic(topic_root)
    if thread_id:
        return f"{topic_root}-{thread_id[:8].lower()}"
    return topic_root


def upsert_task_pr_metadata(body: Any, metadata: Mapping[str, Any]) -> str:
    core = strip_task_pr_metadata(body)
    if core:
        return f"{core}\n\n{render_task_pr_metadata_block(metadata)}\n"
    return f"{render_task_pr_metadata_block(metadata)}\n"
