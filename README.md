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
```

4. Read the [architecture guide](docs/architecture.md).
5. Review the [CLI overview](docs/cli.md).

## Verification

This early public release supports a lightweight install-and-test path:

```bash
python3 -m pip install -e .
python3 -m unittest discover -s tests -v
```

## Current public surface

The public branch currently includes:

- release metadata via `reflexive status` and `reflexive version`
- read-only filesystem inspection via `reflexive cortex inspect <path>`
- read-only operator-risk checks via `reflexive cortex check <path>`
- read-only operator recommendations via `reflexive cortex doctor <path>`
- read-only directory comparison via `reflexive cortex compare <left> <right>`

State-changing workflows such as snapshots, doctor homes, scratch homes, and
scaffold mutation are not part of the current public release.

## Architecture

See [docs/architecture.md](docs/architecture.md).
