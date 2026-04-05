# CLI Overview

The current public release exposes a small read-only CLI surface.

## Available commands

- `reflexive status`
  Shows public release metadata for the installed shell.
- `reflexive status --json`
  Emits the same release metadata in machine-readable form.
- `reflexive version`
  Prints the public package version.
- `reflexive version --json`
  Emits version metadata in machine-readable form.
- `reflexive cortex inspect <path>`
  Inspects a local tool-state directory and reports file, symlink, and SQLite
  runtime details without modifying anything.
- `reflexive cortex inspect <path> --json`
  Emits the same inspection payload in machine-readable form.
- `reflexive cortex check <path>`
  Evaluates a local tool-state directory for operator-risk signals such as live
  SQLite holders and stale sidecar files.
- `reflexive cortex check <path> --json`
  Emits the same check payload in machine-readable form.

## Not yet public

The broader project design includes additional operator workflows, but they are
not part of the current public release.

- snapshot creation and restore workflows
- doctor and scratch environment staging
- scaffold and repository-guardrail mutation commands

## Output style

- Human-readable output for operators.
- `--json` on automation-facing surfaces.
- Explicit commands for state-changing actions.
