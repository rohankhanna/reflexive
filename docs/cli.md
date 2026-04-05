# CLI Overview

`reflexive` is organized around a small set of operator-safety command
families.

## Command families

- `reflexive status`
  Reports repo and safety-surface status.
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

This public branch is currently a docs-first shell. The standalone packaged
release surface is still being promoted into public `main`.
