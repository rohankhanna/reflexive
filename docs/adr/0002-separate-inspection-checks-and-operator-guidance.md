# 0002: Separate inspection, checks, and operator guidance

- Status: Accepted
- Date: 2026-04-06

## Context

Operator tooling needs both trustworthy raw facts and higher-level guidance.
If those layers are collapsed together, automation loses access to stable raw
data and operator recommendations become harder to evolve safely.

## Decision

`reflexive` exposes raw inspection, policy-style checks, and operator guidance
as separate layers:

- `inspect` reports facts
- `check` evaluates operator-risk signals
- `doctor` adds recommendations on top of the same inspection and check data

The same separation also informs snapshot verification and diff surfaces, which
stay read-only until an explicit restore or staged workflow is chosen.

## Consequences

- Automation can consume raw facts without parsing advice text.
- Policy checks can evolve without redefining the raw inspection contract.
- Operator guidance can become richer without hiding the underlying evidence.
- State-changing recovery flows remain explicit rather than being smuggled into
  read-only commands.
