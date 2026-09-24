# Agent Context — Larrick Multi Repository

This file is read by Claude Code and other AI coding agents.

## Canonical context

Read **[AGENTS.md](AGENTS.md)** in full first. It is the single source of truth for workflow, external `larrak-*` packages (`pyproject.toml` / `uv` vs `requirements-external.txt`), CI, domain map, umbrella documentation links, and Cursor worktree notes.

If anything in this file ever disagrees with `AGENTS.md`, **`AGENTS.md` wins.**

## Optional Cursor worktree plugin

When the in-repo [larrick-worktree-workflow](.cursor/plugins/larrick-worktree-workflow/) plugin is active, [workflow-ownership.mdc](.cursor/plugins/larrick-worktree-workflow/rules/workflow-ownership.mdc) and [hooks/hooks.json](.cursor/plugins/larrick-worktree-workflow/hooks/hooks.json) add branch and shell guardrails **on top of** the baseline in `AGENTS.md`. See the plugin [README.md](.cursor/plugins/larrick-worktree-workflow/README.md) for installation and validation gates.
