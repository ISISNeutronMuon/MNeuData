<!-- Implementation notes:
- ADRs are the canonical, version-controlled record of every significant architecture decision for the compute-cluster; they live in-repo under docs/ADRs/ alongside the talos/ and gitops/ implementations they describe.
- Files follow Michael Nygard's template (Title, Date, Status, Context, Decision, Consequences) and the joshrotenberg/adrs tool convention for creation/numbering.
- Sequentially numbered with a zero-padded 4-digit prefix (0001..0010) so ordering and cross-referencing are stable; filenames are human-readable (e.g. '0005 Software infrastructure.md').
- Status field (currently 'Pending' across the set) tracks lifecycle (Pending -> Accepted -> Superseded/Deprecated) rather than deleting superseded decisions.
- Kept in Git and changed via the same human-in-the-loop review flow as the rest of the repo (agents draft, humans review/commit/push) so decision history is auditable.
- ADRs 0003-0010 carry a non-rendering HTML comment block of implementation notes (like this one) that ties each decision back to concrete talos/gitops config.
- Rationale: lightweight, low-friction, greppable documentation that stays next to the code so context for 'why' is not lost as the cluster evolves.
-->
# 1. Record architecture decisions

Date: 2026-08-06
## Status

First Draft

## Context

We need to record the architectural decisions made on this project.

## Decision

We will use Architecture Decision Records, as [described by Michael Nygard](http://thinkrelevance.com/blog/2011/11/15/documenting-architecture-decisions).

[adrs](https://github.com/joshrotenberg/adrs) will be used to manage ADRs.

## Consequences

See Michael Nygard’s article, linked above.