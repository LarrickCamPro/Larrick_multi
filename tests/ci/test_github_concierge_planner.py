"""Tests for the GitHub concierge planner and template helpers."""

from __future__ import annotations

from larrak2.architecture.github_concierge import (
    build_task_context,
    compute_next_semver_tag,
    load_workflow_ownership,
    parse_task_pr_metadata,
    plan_drift_audit,
    plan_merge_checker,
    plan_promotion_actions,
    plan_release_audit,
    plan_security_audit,
    plan_task_actions,
    read_project_version,
    render_promotion_issue_body,
    render_promotion_issue_payload,
    render_task_issue_body,
    render_task_issue_payload,
    render_task_pr_body,
    route_thread,
)


def _policy():
    return load_workflow_ownership()


def _task(issue_number: int | None = None):
    return build_task_context(
        policy=_policy(),
        workflow="simulation",
        topic_slug="fix-doe-paths",
        worktree_path="/tmp/wt-simulation-fix-doe-paths",
        thread_id="019d2234-1a71-75f2-abd8-9aec967c7df0",
        thread_name="Fix Doe Paths",
        routing_workflow="simulation",
        routing_confidence=0.91,
        routing_source="classifier",
        routing_strategy="classifier",
        source_prompt_excerpt="We need to refine the simulation suite.",
        workspace_mode="current",
        conversation_state="active",
        archive_eligible=False,
        last_thread_seen_at="2026-03-24T08:00:00+00:00",
        issue_number=issue_number,
    )


def _green_checks(workflow: str) -> list[dict[str, str]]:
    return [
        {
            "name": "Branch Ownership",
            "status": "completed",
            "conclusion": "success",
        },
        {
            "name": f"Fast Checks ({workflow})",
            "status": "completed",
            "conclusion": "success",
        },
    ]


def test_workflow_policy_includes_repo_release_and_cloud_lifecycle_settings() -> None:
    policy = _policy()
    assert policy.repo.owner == "mhold3n"
    assert policy.repo.name == "Larrick_multi"
    assert policy.pr_policy.auto_merge_to_dev is True
    assert policy.pr_policy.manual_merge_to_main is True
    assert policy.issue_policy == "optional"
    assert policy.routing_policy.confidence_threshold == 0.70
    assert policy.routing_policy.explicit_token_prefix == "workflow:"
    assert "working on {workflow} development" in policy.routing_policy.explicit_phrase_templates
    assert policy.merge_checker_policy.inactivity_hours == 72
    assert policy.merge_checker_policy.blocked_archive_hours == 336
    assert policy.audit_thresholds.stale_open_task_pr_hours == 48
    assert policy.audit_thresholds.orphaned_no_pr_archive_hours == 336
    assert policy.release_policy.tag_prefix == "v"


def test_build_task_context_contains_cloud_lifecycle_fields() -> None:
    task = _task(issue_number=17)
    payload = task.to_dict()
    assert payload["workflow"] == "simulation"
    assert payload["branch"] == "codex/simulation/fix-doe-paths"
    assert payload["base_branch"] == "dev/simulation"
    assert payload["promotion_branch"] == "main"
    assert payload["repo_owner"] == "mhold3n"
    assert payload["repo_name"] == "Larrick_multi"
    assert payload["docker_namespace"] == "codex-simulation-fix-doe-paths"
    assert payload["thread_id"] == "019d2234-1a71-75f2-abd8-9aec967c7df0"
    assert payload["thread_name"] == "Fix Doe Paths"
    assert payload["routing_workflow"] == "simulation"
    assert payload["routing_confidence"] == 0.91
    assert payload["routing_source"] == "classifier"
    assert payload["routing_strategy"] == "classifier"
    assert payload["workspace_mode"] == "current"
    assert payload["conversation_state"] == "active"
    assert payload["archive_eligible"] is False
    assert payload["last_thread_seen_at"] == "2026-03-24T08:00:00+00:00"
    assert payload["issue_number"] == 17


def test_route_thread_routes_explicit_token_authoritatively() -> None:
    decision = route_thread(
        _policy(),
        prompt="workflow:optimization We are actually working on simulation tooling, but this thread owns optimization development.",
        thread_id="019d2234-1a71-75f2-abd8-9aec967c7df0",
        thread_name="Optimization Sweep",
    )
    payload = decision.to_dict()
    assert payload["needs_confirmation"] is False
    assert payload["workflow"] == "optimization"
    assert payload["routing_source"] == "explicit_token"
    assert payload["branch"] == "codex/optimization/optimization-sweep-019d2234"


def test_route_thread_routes_explicit_phrase_authoritatively() -> None:
    decision = route_thread(
        _policy(),
        prompt="This conversation is for training development and should tighten the surrogate manifest flow.",
        thread_id="019d2234-1a71-75f2-abd8-9aec967c7df0",
        thread_name="Training Manifest Flow",
    )
    payload = decision.to_dict()
    assert payload["needs_confirmation"] is False
    assert payload["workflow"] == "training"
    assert payload["routing_source"] == "explicit_phrase"


def test_route_thread_requests_confirmation_for_conflicting_markers() -> None:
    decision = route_thread(
        _policy(),
        prompt="workflow:simulation working on training development",
        thread_id="019d2234-1a71-75f2-abd8-9aec967c7df0",
        thread_name="Conflicting markers",
    )
    payload = decision.to_dict()
    assert payload["needs_confirmation"] is True
    assert payload["workflow"] is None


def test_route_thread_routes_simulation_prompt_confidently_with_classifier_fallback() -> None:
    decision = route_thread(
        _policy(),
        prompt="We need to refine the simulation suite and inspect the OpenFOAM solver.",
        thread_id="019d2234-1a71-75f2-abd8-9aec967c7df0",
        thread_name="Refine Simulation Suite",
    )
    payload = decision.to_dict()
    assert payload["needs_confirmation"] is False
    assert payload["workflow"] == "simulation"
    assert payload["base_branch"] == "dev/simulation"
    assert payload["branch"] == "codex/simulation/refine-simulation-suite-019d2234"
    assert payload["routing_source"] == "classifier"
    assert "simulation" in payload["matched_keywords"]


def test_route_thread_requests_confirmation_for_cross_workflow_prompt() -> None:
    decision = route_thread(
        _policy(),
        prompt="We need to connect the simulation dataset bundle to surrogate training.",
        thread_id="019d2234-1a71-75f2-abd8-9aec967c7df0",
        thread_name="Bridge Simulation and Training",
    )
    payload = decision.to_dict()
    assert payload["needs_confirmation"] is True
    assert payload["workflow"] is None
    assert payload["recommended_workflow"] in {"simulation", "training"}


def test_template_rendering_includes_issue_promotion_and_metadata_block() -> None:
    policy = _policy()
    task = _task(issue_number=17)

    task_pr_body = render_task_pr_body(policy, task)
    task_issue_body = render_task_issue_body(policy, task)
    task_issue_payload = render_task_issue_payload(policy, task)
    promotion_issue_body = render_promotion_issue_body(
        "simulation",
        {
            "base_branch": "dev/simulation",
            "promotion_branch": "main",
            "linked_task_prs": [{"number": 22, "title": "simulation: Fix doe paths"}],
        },
    )
    promotion_issue_payload = render_promotion_issue_payload(
        policy,
        "simulation",
        {
            "base_branch": "dev/simulation",
            "promotion_branch": "main",
            "linked_task_prs": [{"number": 22, "title": "simulation: Fix doe paths"}],
        },
    )
    metadata = parse_task_pr_metadata(task_pr_body)

    assert "#17" in task_pr_body
    assert "openfoam_templates/**" in task_pr_body
    assert metadata["workflow"] == "simulation"
    assert metadata["conversation_state"] == "active"
    assert metadata["archive_eligible"] is False
    assert "Track the `simulation` task `fix-doe-paths`" in task_issue_body
    assert "PR #22 - simulation: Fix doe paths" in promotion_issue_body
    assert task_issue_payload["title"] == "Track simulation task: Fix Doe Paths"
    assert promotion_issue_payload["title"] == "Promote simulation branch to main"


def test_plan_task_actions_creates_pr_after_first_push_with_metadata() -> None:
    actions = plan_task_actions(
        _policy(),
        _task(),
        {
            "branch_pushed": True,
            "thread_updated_at": "2026-03-24T08:00:00+00:00",
        },
    )
    assert [action.action_id for action in actions] == ["create_task_pr"]
    assert actions[0].payload["base"] == "dev/simulation"
    assert actions[0].payload["title"] == "simulation: Fix Doe Paths"
    metadata = parse_task_pr_metadata(actions[0].payload["body"])
    assert metadata["conversation_state"] == "active"
    assert metadata["routing_source"] == "classifier"


def test_plan_task_actions_syncs_pending_pr_requests_review_and_upserts_metadata() -> None:
    task = _task()
    actions = plan_task_actions(
        _policy(),
        task,
        {
            "branch_pushed": True,
            "thread_updated_at": "2026-03-25T10:00:00+00:00",
            "task_pr": {
                "number": 10,
                "state": "OPEN",
                "title": "stale title",
                "body": "stale body",
                "base_ref": "dev/analysis",
                "draft": False,
                "copilot_review_requested": False,
                "check_runs": [{"name": "Fast Checks (simulation)", "status": "queued"}],
            },
        },
    )
    assert [action.action_id for action in actions] == [
        "update_task_pr",
        "upsert_task_pr_metadata",
        "request_copilot_review",
    ]
    assert parse_task_pr_metadata(actions[1].payload["body"])["last_thread_seen_at"] == "2026-03-25T10:00:00+00:00"


def test_plan_task_actions_merges_green_dev_pr_with_housekeeping() -> None:
    task = _task()
    body = render_task_pr_body(_policy(), task)
    actions = plan_task_actions(
        _policy(),
        task,
        {
            "branch_pushed": True,
            "task_pr": {
                "number": 11,
                "state": "OPEN",
                "title": "simulation: Fix Doe Paths",
                "body": body,
                "base_ref": "dev/simulation",
                "draft": False,
                "copilot_review_requested": True,
                "copilot_review_completed": True,
                "review_decision": "APPROVED",
                "check_runs": _green_checks("simulation"),
            },
            "policy_findings": [],
        },
    )
    assert [action.action_id for action in actions] == [
        "merge_task_pr",
        "finalize_merged_task_pr",
        "delete_task_branch",
        "report_archive_eligible_task",
    ]


def test_plan_task_actions_refreshes_task_pr_when_base_moves() -> None:
    task = _task()
    body = render_task_pr_body(_policy(), task)
    actions = plan_task_actions(
        _policy(),
        task,
        {
            "branch_pushed": True,
            "task_pr": {
                "number": 15,
                "state": "OPEN",
                "title": "simulation: Fix Doe Paths",
                "body": body,
                "base_ref": "dev/simulation",
                "draft": False,
                "copilot_review_requested": True,
                "copilot_review_completed": True,
                "review_decision": "APPROVED",
                "behind_base_by": 2,
                "check_runs": _green_checks("simulation"),
            },
        },
    )
    action_ids = [action.action_id for action in actions]
    assert "refresh_task_pr_branch" in action_ids
    assert "merge_task_pr" not in action_ids


def test_plan_task_actions_comments_on_policy_findings_without_duplicates() -> None:
    task = _task()
    body = render_task_pr_body(_policy(), task)
    actions = plan_task_actions(
        _policy(),
        task,
        {
            "branch_pushed": True,
            "task_pr": {
                "number": 12,
                "state": "OPEN",
                "title": "simulation: Fix Doe Paths",
                "body": body,
                "base_ref": "dev/simulation",
                "draft": False,
                "copilot_review_requested": True,
                "copilot_review_completed": True,
                "review_decision": "APPROVED",
                "changed_paths": ["src/larrak2/simulation_validation/source_rules.py"],
                "comments": [
                    {
                        "body": "**Already handled**\n\n<!-- concierge:fingerprint=ownership:general:duplicate -->"
                    }
                ],
                "review_comments": [],
                "check_runs": _green_checks("simulation"),
            },
            "policy_findings": [
                {
                    "code": "ownership",
                    "title": "Wrong branch target",
                    "message": "This branch must target dev/simulation.",
                    "fingerprint": "ownership:general:duplicate",
                },
                {
                    "code": "layout",
                    "title": "Template drift",
                    "message": "The touched simulation file is outside the allowed layout policy.",
                    "path": "src/larrak2/simulation_validation/source_rules.py",
                },
            ],
        },
    )
    assert [action.action_id for action in actions] == ["comment_policy_failure"]
    assert actions[0].payload["comment_kind"] == "inline_review"
    assert actions[0].payload["path"] == "src/larrak2/simulation_validation/source_rules.py"


def test_plan_promotion_actions_opens_pr_after_dev_branch_advances() -> None:
    actions = plan_promotion_actions(
        _policy(),
        "simulation",
        {
            "dev_branch": {"ahead_by": 2},
            "linked_task_prs": [{"number": 44, "title": "Simulation: fix doe paths"}],
            "commit_summaries": ["simulation: fix doe paths", "simulation: tighten templates"],
        },
    )
    assert [action.action_id for action in actions] == ["open_promotion_pr"]
    assert actions[0].payload["head"] == "dev/simulation"
    assert actions[0].payload["base"] == "main"


def test_plan_promotion_actions_prepares_but_does_not_merge_main() -> None:
    actions = plan_promotion_actions(
        _policy(),
        "simulation",
        {
            "dev_branch": {"ahead_by": 1},
            "promotion_pr": {
                "number": 45,
                "state": "OPEN",
                "title": "Promote simulation to main",
                "body": "current body",
                "base_ref": "main",
                "draft": False,
                "review_decision": "APPROVED",
                "behind_base_by": 0,
                "check_runs": [
                    {
                        "name": "Fast Checks (main)",
                        "status": "completed",
                        "conclusion": "success",
                    }
                ],
            },
            "linked_task_prs": [{"number": 44, "title": "Simulation: fix doe paths"}],
            "commit_summaries": ["simulation: fix doe paths"],
        },
    )
    action_ids = [action.action_id for action in actions]
    assert "prepare_main_merge" in action_ids
    assert "merge_task_pr" not in action_ids


def test_plan_promotion_actions_refreshes_branch_before_main_merge() -> None:
    actions = plan_promotion_actions(
        _policy(),
        "simulation",
        {
            "dev_branch": {"ahead_by": 1},
            "promotion_pr": {
                "number": 46,
                "state": "OPEN",
                "title": "Promote simulation to main",
                "body": "current body",
                "base_ref": "main",
                "draft": False,
                "review_decision": "APPROVED",
                "behind_base_by": 3,
                "check_runs": [
                    {
                        "name": "Fast Checks (main)",
                        "status": "completed",
                        "conclusion": "success",
                    }
                ],
            },
            "linked_task_prs": [{"number": 44, "title": "Simulation: fix doe paths"}],
            "commit_summaries": ["simulation: fix doe paths"],
        },
    )
    action_ids = [action.action_id for action in actions]
    assert "refresh_promotion_pr_branch" in action_ids
    assert "prepare_main_merge" not in action_ids


def test_plan_drift_audit_flags_merged_blocked_and_orphaned_items() -> None:
    actions = plan_drift_audit(
        _policy(),
        {
            "now": "2026-04-10T12:00:00+00:00",
            "open_task_branches": [
                {
                    "branch": "codex/simulation/fix-doe-paths",
                    "has_pr": False,
                    "updated_at": "2026-03-20T08:00:00+00:00",
                }
            ],
            "task_pull_requests": [
                {
                    "number": 52,
                    "state": "OPEN",
                    "head_ref": "codex/training/add-manifest-schema",
                    "draft": True,
                    "body": render_task_pr_body(
                        _policy(),
                        build_task_context(
                            policy=_policy(),
                            workflow="training",
                            topic_slug="add-manifest-schema",
                            worktree_path="/tmp/wt-training-add-manifest-schema",
                            branch="codex/training/add-manifest-schema",
                            routing_source="classifier",
                            routing_strategy="classifier",
                            workspace_mode="current",
                            conversation_state="blocked",
                            archive_eligible=True,
                        ),
                    ),
                    "blocked_summary": "workflow-fast-checks",
                    "blocked_reasons": ["workflow-fast-checks"],
                },
                {
                    "number": 53,
                    "state": "CLOSED",
                    "merged_at": "2026-04-09T10:00:00+00:00",
                    "head_ref": "codex/simulation/refine-simulation-suite-019d2234",
                    "body": render_task_pr_body(
                        _policy(),
                        build_task_context(
                            policy=_policy(),
                            workflow="simulation",
                            topic_slug="refine-simulation-suite-019d2234",
                            worktree_path="/tmp/wt-simulation-refine",
                            branch="codex/simulation/refine-simulation-suite-019d2234",
                            routing_source="classifier",
                            routing_strategy="classifier",
                            workspace_mode="current",
                            conversation_state="merged",
                            archive_eligible=True,
                        ),
                    ),
                },
            ],
            "workflow_branches": {"simulation": {"ahead_by": 3}},
            "promotion_prs": [],
        },
    )
    action_ids = [action.action_id for action in actions]
    assert "audit_orphaned_no_pr_task" in action_ids
    assert action_ids.count("audit_archive_eligible_task") == 2
    assert "audit_missing_promotion_pr" in action_ids


def test_plan_security_audit_targets_open_prs() -> None:
    actions = plan_security_audit(
        _policy(),
        {
            "pull_requests": [
                {
                    "number": 60,
                    "state": "OPEN",
                    "head_ref": "codex/simulation/fix-doe-paths",
                    "base_ref": "dev/simulation",
                },
                {
                    "number": 61,
                    "state": "OPEN",
                    "head_ref": "dev/simulation",
                    "base_ref": "main",
                },
            ]
        },
    )
    assert [action.action_id for action in actions] == [
        "audit_security_scan",
        "audit_security_scan",
    ]
    assert actions[1].payload["kind"] == "promotion"


def test_release_audit_uses_project_version_when_no_tags() -> None:
    actions = plan_release_audit(
        _policy(),
        {
            "current_version": read_project_version(),
            "tags": [],
            "main_branch": {"ahead_by": 2},
            "commits_since_latest_tag": ["ci: tighten ownership planning"],
        },
    )
    assert [action.action_id for action in actions] == ["audit_release_ready"]
    assert actions[0].payload["next_tag"] == "v0.1.0"


def test_compute_next_semver_tag_bumps_existing_release() -> None:
    assert (
        compute_next_semver_tag(
            existing_tags=["v0.1.0", "v0.1.2"],
            current_version="0.1.0",
            tag_prefix="v",
        )
        == "v0.1.3"
    )


def test_plan_merge_checker_merges_quiet_green_task_pr_with_housekeeping() -> None:
    task = _task()
    actions = plan_merge_checker(
        _policy(),
        {
            "now": "2026-03-28T12:00:00+00:00",
            "task_pull_requests": [
                {
                    "number": 70,
                    "state": "OPEN",
                    "draft": False,
                    "head_ref": task.branch,
                    "base_ref": "dev/simulation",
                    "body": render_task_pr_body(_policy(), task),
                    "thread_updated_at": "2026-03-24T08:00:00+00:00",
                    "branch_updated_at": "2026-03-24T08:00:00+00:00",
                    "updated_at": "2026-03-24T08:00:00+00:00",
                    "latest_check_run_at": "2026-03-24T08:00:00+00:00",
                    "check_runs": _green_checks("simulation"),
                    "contract_checks_passed": True,
                }
            ],
        },
    )
    assert [action.action_id for action in actions] == [
        "merge_task_pr",
        "finalize_merged_task_pr",
        "delete_task_branch",
        "report_archive_eligible_task",
    ]


def test_plan_merge_checker_refreshes_quiet_pr_behind_base() -> None:
    task = _task()
    actions = plan_merge_checker(
        _policy(),
        {
            "now": "2026-03-28T12:00:00+00:00",
            "task_pull_requests": [
                {
                    "number": 71,
                    "state": "OPEN",
                    "draft": False,
                    "head_ref": task.branch,
                    "base_ref": "dev/simulation",
                    "body": render_task_pr_body(_policy(), task),
                    "thread_updated_at": "2026-03-24T08:00:00+00:00",
                    "branch_updated_at": "2026-03-24T08:00:00+00:00",
                    "updated_at": "2026-03-24T08:00:00+00:00",
                    "latest_check_run_at": "2026-03-24T08:00:00+00:00",
                    "check_runs": _green_checks("simulation"),
                    "contract_checks_passed": True,
                    "behind_base_by": 2,
                }
            ],
        },
    )
    assert [action.action_id for action in actions] == ["refresh_task_pr_branch"]


def test_plan_merge_checker_blocks_quiet_failing_task_pr() -> None:
    task = build_task_context(
        policy=_policy(),
        workflow="training",
        topic_slug="add-manifest-schema-019d2175",
        worktree_path="/tmp/wt-training-add-manifest-schema",
        branch="codex/training/add-manifest-schema-019d2175",
        routing_source="classifier",
        routing_strategy="classifier",
        workspace_mode="current",
        conversation_state="active",
    )
    actions = plan_merge_checker(
        _policy(),
        {
            "now": "2026-03-28T12:00:00+00:00",
            "task_pull_requests": [
                {
                    "number": 72,
                    "state": "OPEN",
                    "draft": False,
                    "head_ref": task.branch,
                    "base_ref": "dev/training",
                    "body": render_task_pr_body(_policy(), task),
                    "thread_updated_at": "2026-03-24T08:00:00+00:00",
                    "branch_updated_at": "2026-03-24T08:00:00+00:00",
                    "updated_at": "2026-03-24T08:00:00+00:00",
                    "latest_check_run_at": "2026-03-24T08:00:00+00:00",
                    "check_runs": [
                        {
                            "name": "Branch Ownership",
                            "status": "completed",
                            "conclusion": "success",
                        },
                        {
                            "name": "Fast Checks (training)",
                            "status": "completed",
                            "conclusion": "failure",
                        },
                    ],
                    "contract_checks_passed": True,
                    "comments": [],
                }
            ],
        },
    )
    assert [action.action_id for action in actions] == [
        "upsert_task_pr_metadata",
        "mark_task_pr_blocked",
        "comment_blocked_task_pr",
    ]
    metadata = parse_task_pr_metadata(actions[0].payload["body"])
    assert metadata["conversation_state"] == "blocked"
    assert metadata["archive_eligible"] is False


def test_plan_merge_checker_marks_blocked_task_archive_eligible_after_timeout() -> None:
    task = build_task_context(
        policy=_policy(),
        workflow="analysis",
        topic_slug="telemetry-pass-019d2234",
        worktree_path="/tmp/wt-analysis-telemetry-pass",
        branch="codex/analysis/telemetry-pass-019d2234",
        routing_source="classifier",
        routing_strategy="classifier",
        workspace_mode="current",
        conversation_state="blocked",
        archive_eligible=False,
        last_thread_seen_at="2026-03-01T08:00:00+00:00",
    )
    blocked_body = render_task_pr_body(_policy(), task)
    actions = plan_merge_checker(
        _policy(),
        {
            "now": "2026-03-20T12:00:00+00:00",
            "task_pull_requests": [
                {
                    "number": 73,
                    "state": "OPEN",
                    "draft": True,
                    "head_ref": task.branch,
                    "base_ref": "dev/analysis",
                    "body": blocked_body,
                    "thread_updated_at": "2026-03-01T08:00:00+00:00",
                    "branch_updated_at": "2026-03-01T08:00:00+00:00",
                    "updated_at": "2026-03-01T08:00:00+00:00",
                    "latest_check_run_at": "2026-03-01T08:00:00+00:00",
                    "check_runs": [
                        {
                            "name": "Branch Ownership",
                            "status": "completed",
                            "conclusion": "success",
                        },
                        {
                            "name": "Fast Checks (analysis)",
                            "status": "completed",
                            "conclusion": "failure",
                        },
                    ],
                    "contract_checks_passed": True,
                    "comments": [],
                }
            ],
        },
    )
    action_ids = [action.action_id for action in actions]
    assert "upsert_task_pr_metadata" in action_ids
    assert "report_archive_eligible_task" in action_ids
    metadata = parse_task_pr_metadata(actions[0].payload["body"])
    assert metadata["archive_eligible"] is True


def test_plan_merge_checker_reports_orphaned_no_pr_branch() -> None:
    actions = plan_merge_checker(
        _policy(),
        {
            "now": "2026-04-10T12:00:00+00:00",
            "task_branches_without_pr": [
                {
                    "branch": "codex/simulation/fix-doe-paths",
                    "updated_at": "2026-03-20T08:00:00+00:00",
                }
            ],
            "task_pull_requests": [],
        },
    )
    assert [action.action_id for action in actions] == ["report_orphaned_no_pr_task"]
    assert actions[0].payload["archive_eligible"] is True


def test_plan_merge_checker_skips_active_task_pr() -> None:
    task = build_task_context(
        policy=_policy(),
        workflow="analysis",
        topic_slug="telemetry-pass-019d2234",
        worktree_path="/tmp/wt-analysis-telemetry-pass",
        branch="codex/analysis/telemetry-pass-019d2234",
        routing_source="classifier",
        routing_strategy="classifier",
        workspace_mode="current",
        conversation_state="active",
    )
    actions = plan_merge_checker(
        _policy(),
        {
            "now": "2026-03-28T12:00:00+00:00",
            "task_pull_requests": [
                {
                    "number": 74,
                    "state": "OPEN",
                    "draft": False,
                    "head_ref": task.branch,
                    "base_ref": "dev/analysis",
                    "body": render_task_pr_body(_policy(), task),
                    "thread_updated_at": "2026-03-27T20:00:00+00:00",
                    "branch_updated_at": "2026-03-27T20:00:00+00:00",
                    "updated_at": "2026-03-27T20:00:00+00:00",
                    "latest_check_run_at": "2026-03-27T20:00:00+00:00",
                    "check_runs": _green_checks("analysis"),
                    "contract_checks_passed": True,
                }
            ],
        },
    )
    assert actions == []
