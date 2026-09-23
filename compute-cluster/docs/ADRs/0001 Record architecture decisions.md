---
status: "proposed"
date: "2026-08-16"
decision-makers: "Samuel Jones, Simon Hodder, Martyn Gigg, Daniel Nixon"
consulted: "Martyn Gigg"
informed: "Samuel Jones, Simon Hodder, Martyn Gigg, Daniel Nixon"
---

# 1. Record architecture decisions

## Context and Problem Statement

We need to record the significant architectural decisions made on this project,
in-repo and version-controlled. Which format should these records take?

## Considered Options

* MADR (Markdown Architectural Decision Records)
* Michael Nygard's ADR template

## Decision Outcome

Chosen option: "MADR", because it keeps the lightweight, greppable, in-repo
qualities we want while adding more structure (drivers, options, pros/cons) than
Nygard's template. The project originally used Nygard and has since migrated the
existing records to MADR. Records use the
[MADR](https://adr.github.io/adr-templates/) full template (`docs/ADRs/template.md`),
are managed with [adrs](https://github.com/joshrotenberg/adrs), and are numbered
with a zero-padded 4-digit prefix.

### Consequences

* Good, because decisions and their rationale stay next to the code, searchable
  and version-controlled.
* Bad, because the richer template is more effort, and the existing Nygard
  records had to be migrated.

### Confirmation

New records are created from `docs/ADRs/template.md` and reviewed in the normal
Git review flow before being committed.
