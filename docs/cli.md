# CLI Overview

The current public release exposes a minimal CLI shell.

## Available commands

- `reflexive status`
  Shows public release metadata for the installed shell.
- `reflexive status --json`
  Emits the same release metadata in machine-readable form.
- `reflexive version`
  Prints the public package version.
- `reflexive version --json`
  Emits version metadata in machine-readable form.

## Intended command domains

The broader project design centers on a small set of operator-safety command
families.

## Command families

- `reflexive status`
  Reports release metadata in the current public shell.
- `reflexive cortex ...`
  Covers inspection, snapshots, recovery workflows, and isolated runtime
  environments.
- `reflexive doctor ...`
  Uses a safer fallback environment for recovery-oriented work.
- `reflexive scratch ...`
  Uses a disposable environment for experimentation.
- `reflexive scaffold ...`
  Covers documentation and guardrail-oriented repository surfaces.

## Output style

- Human-readable output for operators.
- `--json` on automation-facing surfaces.
- Explicit commands for state-changing actions.

## Status

This release currently ships only the minimal `status` and `version` commands.
The remaining command families are documented here as the intended operator
surface, not yet as a claim of full public availability.
