# reflexive

`reflexive` is a CLI for safely snapshotting, recovering, and isolating AI coding tool state on a local workstation.

It is designed for situations where tool state matters: recovery after a bad configuration change, staging a safer fallback environment, or creating a disposable scratch environment before risky experimentation.

## What it does

- inspects local tool state and recovery surfaces
- creates and manages snapshots for rollback and diagnostics
- stages isolated recovery and scratch environments
- supports explicit operator workflows for safer experimentation

## Status

Early public release.

## Getting Started

This release currently exposes a docs-first shell of the project.

Start here:

1. Read the [architecture guide](docs/architecture.md).
2. Review the [CLI overview](docs/cli.md).

## Verification

Standalone verification guidance is not yet part of this early public shell.

## Architecture

See [docs/architecture.md](docs/architecture.md).
