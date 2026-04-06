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

This release currently exposes a small installable CLI plus public
documentation.

Start here:

1. Install the package:

```bash
python3 -m pip install -e .
```

2. Inspect the public release surface:

```bash
reflexive status --json
```

3. Inspect a local tool-state directory:

```bash
reflexive cortex inspect ~/.codex --json
reflexive cortex check ~/.codex --json
reflexive cortex doctor ~/.codex --json
reflexive cortex compare ~/.codex ~/backup-codex --json
reflexive cortex snapshot create ~/.codex --json
reflexive cortex snapshot verify ~/.codex --json
reflexive cortex snapshot diff ~/.codex --json
```

4. Inspect the app-owned storage roots:

```bash
reflexive paths --json
```

5. Read the [adoption guide](docs/adoption.md).
6. Read the [architecture guide](docs/architecture.md).
7. Review the [CLI overview](docs/cli.md).

## Verification

This branch verifies with:

```bash
python3 -m compileall src tests
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

If you prefer to test the installed package path as well, you can still run:

```bash
python3 -m pip install -e .
python3 -m unittest discover -s tests -v
```

## Current public surface

The public branch currently includes:

- release metadata via `reflexive status` and `reflexive version`
- app-owned storage root discovery via `reflexive paths`
- explicit app-data cleanup via `reflexive purge`
- read-only filesystem inspection via `reflexive cortex inspect <path>`
- read-only operator-risk checks via `reflexive cortex check <path>`
- read-only operator recommendations via `reflexive cortex doctor <path>`
- read-only directory comparison via `reflexive cortex compare <left> <right>`
- app-owned path snapshots via `reflexive cortex snapshot ...`

Doctor homes, scratch homes, restore workflows, and scaffold mutation are not
part of the current public release.

## Uninstall cleanup

Python package uninstall does not provide a reliable hook for deleting user data
automatically. The supported cleanup sequence is:

```bash
reflexive purge --all --yes
python3 -m pip uninstall reflexive
```

## Architecture

See [docs/architecture.md](docs/architecture.md).
