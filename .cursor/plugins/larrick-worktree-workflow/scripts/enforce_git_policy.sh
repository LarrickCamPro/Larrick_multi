#!/bin/bash
# Deprecated name: delegate to the single canonical hook target under scripts/worktree_agent/.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
exec "$REPO_ROOT/scripts/worktree_agent/branch_policy_guard.sh"
