#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: scripts/finish_parallel_task.sh <worktree-path>" >&2
  exit 1
fi

worktree_path="$(cd "$1" && pwd)"
control_worktree="$(git -C "$worktree_path" worktree list --porcelain | awk '/^worktree / {print $2; exit}')"
branch="$(git -C "$worktree_path" rev-parse --abbrev-ref HEAD)"

if [[ "$branch" != codex/* ]]; then
  echo "finish_parallel_task.sh only supports codex/* task worktrees. Current branch is '$branch'." >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI (gh) is required so task cleanup can verify PR state safely." >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "GitHub CLI is installed but not authenticated. Run 'gh auth login' before finishing a parallel task." >&2
  exit 1
fi

if [[ -n "$(git -C "$worktree_path" status --short)" ]]; then
  echo "Worktree '$worktree_path' has uncommitted changes. Commit, stash, or discard them before cleanup." >&2
  exit 1
fi

if ! git -C "$worktree_path" rev-parse --verify "@{u}" >/dev/null 2>&1; then
  echo "Branch '$branch' has no upstream. Push it before cleanup so the task is not orphaned." >&2
  exit 1
fi

read -r behind ahead <<<"$(git -C "$worktree_path" rev-list --left-right --count '@{u}...HEAD')"
if [[ "$ahead" != "0" ]]; then
  echo "Branch '$branch' has unpushed commits. Push it before cleanup." >&2
  exit 1
fi

pr_payload="$(gh pr list --state all --head "$branch" --json number,state,isDraft,url,headRefName,baseRefName,mergedAt)"
pr_state="$(printf '%s' "$pr_payload" | python3 -c 'import json,sys; data=json.load(sys.stdin); print(data[0]["state"] if data else "")')"
pr_url="$(printf '%s' "$pr_payload" | python3 -c 'import json,sys; data=json.load(sys.stdin); print(data[0]["url"] if data else "")')"

if [[ -z "$pr_state" ]]; then
  echo "No pull request was found for '$branch'. Refusing cleanup because the task lifecycle is incomplete." >&2
  exit 1
fi

if [[ "$pr_state" == "OPEN" ]]; then
  echo "Pull request '$pr_url' is still open. Merge or close it before removing the worktree." >&2
  exit 1
fi

git -C "$control_worktree" worktree remove "$worktree_path"
git -C "$control_worktree" worktree prune

printf 'Removed worktree: %s\n' "$worktree_path"
printf 'Task branch: %s\n' "$branch"
printf 'PR state: %s\n' "$pr_state"
