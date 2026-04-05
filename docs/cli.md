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
- `reflexive paths`
  Shows the app-owned config, state, cache, and runtime roots.
- `reflexive paths --json`
  Emits the same path mapping in machine-readable form.
- `reflexive purge [--state --cache --runtime --config | --all]`
  Shows which app-owned roots would be removed.
- `reflexive purge [--state --cache --runtime --config | --all] --yes`
  Deletes the selected app-owned roots.
- `reflexive purge ... --json`
  Emits the same purge plan or purge result in machine-readable form.
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
- `reflexive cortex doctor <path>`
  Adds operator-facing recommendations on top of the same read-only inspection
  and check data.
- `reflexive cortex doctor <path> --json`
  Emits the same recommendation payload in machine-readable form.
- `reflexive cortex compare <left> <right>`
  Compares two local tool-state directories at the same read-only summary level.
- `reflexive cortex compare <left> <right> --json`
  Emits the same comparison payload in machine-readable form.
- `reflexive cortex snapshot create <path>`
  Creates an app-owned machine-local snapshot for an explicit path.
- `reflexive cortex snapshot list <path>`
  Lists snapshots stored for an explicit path.
- `reflexive cortex snapshot latest <path>`
  Shows the latest snapshot stored for an explicit path.
- `reflexive cortex snapshot verify <path> [snapshot_ref]`
  Verifies an explicit path against a stored snapshot, defaulting to `latest`.
- `reflexive cortex snapshot diff <path> [snapshot_ref]`
  Shows differences between an explicit path and a stored snapshot, defaulting to `latest`.

## Not yet public

The broader project design includes additional operator workflows, but they are
not part of the current public release.

- doctor and scratch environment staging
- restore workflows
- scaffold and repository-guardrail mutation commands

## Output style

- Human-readable output for operators.
- `--json` on automation-facing surfaces.
- Explicit commands for state-changing actions.

## Uninstall note

The public CLI can purge its own app-owned roots, but Python package uninstall
does not run a reliable user-data cleanup hook. Use `reflexive purge --all
--yes` before uninstalling the package.
