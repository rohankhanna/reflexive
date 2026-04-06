# 0001: Use app-owned state roots for the public-safe surface

- Status: Accepted
- Date: 2026-04-06

## Context

`reflexive` needs a public-safe command surface that can be installed and used
outside the private operator checkout. Public-safe commands should not depend
on repo-relative mutable state or a live development checkout.

## Decision

The public-safe surface uses app-owned config, state, cache, and runtime roots
instead of repo-managed mutable state.

Those roots are resolved through standard user-level locations, and cleanup is
explicit through `reflexive purge` rather than implicit during package
uninstall.

## Consequences

- Public-safe commands can run outside the private operator checkout.
- Public state is machine-local and explicit instead of hidden in the repo.
- Package uninstall does not imply destructive user-data cleanup.
- Richer repo-managed operator state remains a separate concern on the private
  operator branch.
