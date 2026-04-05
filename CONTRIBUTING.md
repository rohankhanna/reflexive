# Contributing

Thanks for your interest in `reflexive`.

This public branch is a standalone shell of the project. Contributions here
should improve the public-facing code, docs, architecture, and verification
surface without depending on private workstation context or internal support
artifacts.

## Before you propose a change

1. Check that the change belongs on public `main`.
2. Keep the branch standalone: do not assume private helper tools or local
   workstation scaffolding.
3. Avoid adding machine-local state, recovery artifacts, support-system files,
   or internal-only documentation.

## Verification

Run the canonical public verification command before submitting a change:

```bash
./scripts/verify-public.sh
```

## Public-bound documentation rules

- Write for a technically literate outsider.
- Avoid internal shorthand.
- Do not mention sibling or ecosystem projects unless the reference is truly
  necessary for a public user to understand or use this repository.

## Change review

All public-bound changes should be human-reviewed before publication.
