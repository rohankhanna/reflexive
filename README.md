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

This release currently exposes a minimal installable CLI shell plus public
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

3. Read the [architecture guide](docs/architecture.md).
4. Review the [CLI overview](docs/cli.md).

## Verification

This early public release supports a simple runtime sanity check:

```bash
python3 -m pip install -e .
reflexive status --json
reflexive version
```

## Architecture

See [docs/architecture.md](docs/architecture.md).
