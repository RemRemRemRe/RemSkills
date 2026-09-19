---
name: rem-session-knowledge-distillation
description: >
  Distill reusable knowledge from a working session and write it into the
  knowledge base: harvest the insights, patterns, and pitfalls that emerged,
  classify them by type and generality, decide the destination (a new document
  vs an amendment to an existing document, process, or skill), and write
  generalized, checkable entries. Use at the end of a session or at a
  milestone, and whenever a session's lessons should improve existing
  processes, documents, or skills.
metadata:
  category: workflow
  trigger: manual
---

# Session Knowledge Distillation

## Purpose

A working session produces insights beyond the task at hand: pitfalls that
cost hours, patterns that worked, facts verified against sources, and process
improvements. Left in the chat transcript, they are lost. This skill captures
them into the knowledge base so the next session starts where this one ended.

The skill owns *what to keep, where to put it, and how to write it* — not the
content itself. Writing conventions for skills live in
`rem-write-better-skill`; public-content rules live in
`rem-public-skill-generalization`. Apply those whenever the destination is a
skill or any public document.

## When to run

| Trigger | Action |
|---|---|
| End of a session with substantial work | Full distillation pass |
| A milestone inside a long session | Quick pass — capture only the strong items |
| A pitfall / pattern was re-encountered or re-explained | Capture immediately — do not wait |
| The session corrected an existing skill / doc rule | Fix the target now, then record it in the pass |

## What counts as reusable knowledge

The bar: **would the next session waste time re-learning this?**

| Keep | Skip |
|---|---|
| Pitfalls that caused a real failure (root cause + fix + verification) | One-off debugging noise (a single misconfiguration) |
| Patterns verified to work (recipes, idioms, orderings) | Already-documented knowledge (check the target first) |
| Facts verified against a source (headers, docs, logs) | Unverified claims — mark unverified or drop |
| Process improvements that made the work faster or safer | Session-specific decisions for one task |
| Corrections to existing rules (what was wrong, what is right) | Complaints without a concrete alternative |

Rule of thumb: once, session-specific → skip. The promotion bar for
recurring knowledge is owned by `rem-write-better-skill` §9.

## The workflow

1. **Harvest** — list the candidate insights as one-line bullets: failures +
   root causes, fixes that worked, verified facts, process changes, rule
   corrections. Do this before writing anything.
2. **Classify** — type and generality per item (§Classification). Drop the
   session-specific ones.
3. **Locate the destination** — for each survivor, find its home (decision
   table below) and amend it there (single ownership:
   `rem-write-better-skill` §11).
4. **Write** — one entry per item, in the destination's format (§Entry
   templates) and following the destination's own conventions.
5. **Verify** — the checklist (§Checklist) plus the destination's own
   checklist (for a skill: its closing checklist and
   `rem-public-skill-generalization`).

## Classification

### By type

| Type | Entry shape |
|---|---|
| Pitfall | Symptom → cause → fix → verification |
| Pattern / recipe | When → how → why it works |
| Verified fact | Claim + source citation + verification date |
| Process improvement | Before → after → why better |
| Rule correction | Old rule (wrong) → new rule (right) → why |

### By generality

| Generality | Destination |
|---|---|
| Universal (any project, any tool) | Public knowledge base / skill |
| Project-specific (this codebase, this stack) | The skill's `local/` overlay or the project's local docs |
| Session-specific | Drop, or fold into a general item |

## Destination decision table

| Situation | Destination |
|---|---|
| An existing skill / doc already covers the topic | Amend it in place (single ownership — do not create a parallel doc) |
| The session corrected a rule in a skill | Amend the skill per `rem-write-better-skill` §10 |
| A coherent topic with no home yet | Create a new document — or a new section in the closest document |
| A domain-wide rule with no home | Create a new skill (see `rem-write-better-skill` §9) |
| Project-specific facts | The skill's `local/` overlay or local docs — never the public repo |

When in doubt between "new doc" and "amend existing": **amend**. A new
document is a new place to search; it is justified only by a coherent topic
that no existing document covers.

## Entry templates

### Pitfall

```markdown
### `Thing` does X (verified YYYY-MM)

- **Symptom** — the observable failure (error text, behavior).
- **Cause** — the root reason.
- **Fix** — the concrete correction, self-contained.
- **Verification** — how it was confirmed (build, test, log).
- **Applies to** — the context/versions it was verified in.
```

### Rule correction (in a skill)

```markdown
**Old rule:** ...
**New rule:** ...
**Why:** ...
```

Write the correction back into the skill per `rem-write-better-skill` §10.

## Checklist

Before finishing a distillation pass:

- [ ] Harvested candidates listed before writing (no strong item silently skipped)
- [ ] Every kept item passes the bar: generalizable, verified, and not already documented
- [ ] Each item classified (type + generality); session-specific items dropped
- [ ] Destination per the table: amended the existing home when one exists (single ownership); a new doc only for a coherent new topic
- [ ] Entries follow the type templates (pitfall = symptom/cause/fix/verification; rule correction applied per `rem-write-better-skill` §10)
- [ ] Public content generalized per `rem-public-skill-generalization` (placeholders, no machine paths, no project inventory; real names only when verified public + cited)
- [ ] The destination's own conventions followed (a skill follows `rem-write-better-skill`)
- [ ] Sources cited for facts; "verified YYYY-MM" dates present
- [ ] No stale content left behind (outdated rules removed, not flagged)
- [ ] Workarounds carry a lifecycle annotation (label, failure signal, iteration path) per `rem-write-better-skill` §10.5
- [ ] Session scratch left no trace: one-shot generators, patches and message files swept, the tree free of them per `rem-temp-files`
- [ ] The distillation committed per the repo's workflow (or handed to the user to commit)

## Cross-references

- `rem-write-better-skill` — writing conventions, structure, checklist contract, workaround lifecycle
- `rem-public-skill-generalization` — what may appear in public content and how to generalize
- `rem-commit-workflow` — committing the distilled knowledge
- `rem-temp-files` — where a session's scratch and intermediates belong
