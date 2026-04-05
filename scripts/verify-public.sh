#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

require_file() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "missing required file: $path" >&2
    exit 1
  fi
}

require_absent() {
  local path="$1"
  if [[ -e "$path" ]]; then
    echo "private-only path must not exist on public main: $path" >&2
    exit 1
  fi
}

require_grep() {
  local pattern="$1"
  local path="$2"
  if ! grep -Eq "$pattern" "$path"; then
    echo "expected pattern not found in $path: $pattern" >&2
    exit 1
  fi
}

deny_grep() {
  local pattern="$1"
  local path="$2"
  if grep -Eqi "$pattern" "$path"; then
    echo "forbidden pattern found in $path: $pattern" >&2
    exit 1
  fi
}

require_file README.md
require_file LICENSE
require_file CONTRIBUTING.md
require_file SECURITY.md
require_file CODEOWNERS
require_file docs/architecture.md
require_file docs/architecture.mmd
require_file docs/cli.md
require_file scripts/verify-public.sh

require_absent AGENTS.md
require_absent PUBLIC_PRIVATE_BOUNDARY.md
require_absent .hot-reload.watch
require_absent AGENTS.md.sha256
require_absent reflexive.toml
require_absent state
require_absent content
require_absent feedback
require_absent learnings

require_grep '^# reflexive$' README.md
require_grep '^## Getting Started$' README.md
require_grep '^## Verification$' README.md
require_grep '^## Architecture$' README.md
require_grep '\./scripts/verify-public\.sh' README.md

deny_grep '\badaptive-chrysalis\b|\brelay\b|\bfeedback\b|\bpolestar\b|\boverarch\b' README.md
deny_grep '\binternal\b|\bprivate branch\b' README.md
deny_grep '\badaptive-chrysalis\b|\brelay\b|\bfeedback\b|\bpolestar\b|\boverarch\b' docs/architecture.md
deny_grep '\badaptive-chrysalis\b|\brelay\b|\bfeedback\b|\bpolestar\b|\boverarch\b' docs/cli.md

echo "public shell verification passed"
