# Adoption

`reflexive` is currently packaged as a standalone CLI for inspecting local tool
state, storing explicit snapshots, and managing its own app-owned state roots.

## Install

Install the package from the repo checkout:

```bash
python3 -m pip install -e .
```

## First session

Start by checking the installed surface and the app-owned roots:

```bash
reflexive status --json
reflexive paths --json
```

Then inspect a real tool-state directory:

```bash
reflexive cortex inspect ~/.codex --json
reflexive cortex check ~/.codex --json
reflexive cortex doctor ~/.codex --json
```

If you want a point-in-time copy for later comparison, create a snapshot:

```bash
reflexive cortex snapshot create ~/.codex --json
reflexive cortex snapshot list ~/.codex --json
reflexive cortex snapshot verify ~/.codex --json
```

## State model

The current public release keeps its mutable data under app-owned config, state,
cache, and runtime roots rather than inside the source checkout. Use
`reflexive paths` to see the resolved locations on your machine.

## Current public posture

The current public release emphasizes:

- explicit-path inspection
- explicit snapshots
- explicit cleanup of app-owned state
- read-only operator recommendations before higher-risk workflows

Richer recovery, staging, and repository-mutation workflows are intentionally
deferred from the current public release.

## Cleanup

To remove app-owned `reflexive` state before uninstalling:

```bash
reflexive purge --all --yes
python3 -m pip uninstall reflexive
```
