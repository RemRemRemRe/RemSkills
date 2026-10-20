---
name: rem-session-knowledge-distillation
description: >
  Distill reusable knowledge from a working session and write it into the
  knowledge base: harvest the insights, patterns, and pitfalls that emerged,
  classify them by type and generality, decide the destination (a new document
  vs an amendment to an existing document, process, or skill), and write
  generalized, checkable entries once the operator has approved them. Use at the end of a session or at a
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
`rem-public-material-generalization`. Apply those whenever the destination is a
skill or any public document.

## When to run

| Trigger | Action |
|---|---|
| End of a session with substantial work | Full distillation pass |
| A milestone inside a long session | Quick pass — capture only the strong items |
| A pitfall / pattern was re-encountered or re-explained | Put it in the candidate list at once — the write still waits for approval |
| The session corrected an existing skill / doc rule | Fix the target now, then record it in the pass |

## When the session ends by context pressure

A handoff is written for the **next session**, not for the operator and not as a session log. It carries only what
the code and the skills cannot answer:

- the requirement **as verified** - the interpretation actually implemented, not the source document restated;
- the implemented design's load-bearing facts (ordering guarantees, lifecycle, ownership) with file entry points;
- the next unit's plan **and its acceptance** - otherwise the next session invents its own "done";
- the open decisions with a recommendation and its reason, so the next round re-asks them instead of settling them;
- one line per trap a fresh session would pay for again, pointing at the skill that owns the detail.

It omits git state (it ages within the hour), anything a skill already teaches, and the operator's own wording
where a verified fact exists. Keep it to a screen or two in the run directory, and leave a one-screen pointer in the
project's local context file. The next session's first round re-asks the open items - a recommendation is not an answer.

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

**Wait for the surface to settle.** A design that is still moving yields a candidate, not a rule: hold
it and write the rule once the surface stops changing (`rem-orchestration` — the full-check premise). A
rule written too early is documentation churn paid twice.

## The operator approves before anything is written

A pass **proposes**; it never writes on its own initiative. Harvest and classify first, then show the
candidates in one batch — one line each: the item, its destination, what it costs (a new section or an
amended bullet). Write only what the operator approves; silence is not approval. "Interesting" is not a
reason: an entry nobody acts on costs context in every later session and dilutes the entries that
matter.

- **Budget the entry.** When the destination is a skill, say what the entry replaces or compresses;
  prefer amending a bullet to adding a section, and keep the skill inside the collection's size budget
  (`rem-write-better-skill`).
- **A rejection sticks.** Keep rejected candidates, one line each, in
  `local/rejected-candidates.md` beside this skill (git-ignored, linked from the private repository)
  and read that file before proposing — it outlives the session; a project without the overlay keeps
  the same list in its run directory.

## The workflow

1. **Harvest** — list the candidate insights as one-line bullets: failures +
   root causes, fixes that worked, verified facts, process changes, rule
   corrections. List just as plainly what the knowledge base should *lose*: an
   entry a new one supersedes, two entries saying the same thing, an entry
   nothing ever used, and the three to five oldest dated entries re-checked for
   still being true. Do this before writing anything.
2. **Classify** — type and generality per item (§Classification). Drop the
   session-specific ones.
3. **Locate the destination** — for each survivor, find its home (decision
   table below) and amend it there (single ownership:
   `rem-write-better-skill` §11).
4. **Propose** — put the survivors in front of the operator (item / destination /
   cost) and wait: only approved items are written; a rejection goes to
   `<run-dir>/knowledge-candidates.md`.
5. **Write** — one entry per item, in the destination's format (§Entry
   templates) and following the destination's own conventions.
6. **Verify** — the checklist (§Checklist) plus the destination's own
   checklist (for a skill: its closing checklist and
   `rem-public-material-generalization`).

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
| A hard-to-reverse design decision (not a fact) | The project's decision log / ADR — `rem-docs-and-config` |
| A term that needs one shared definition | The project's glossary, when it keeps one |

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
- [ ] Every write was approved by the operator first; rejected candidates recorded (`local/rejected-candidates.md`, or the run directory when the skill has no overlay)
- [ ] The pass proposed deletions and merges as well as additions (superseded, duplicated, or unused entries)
- [ ] The oldest dated entries were re-checked (date refreshed, or proposed for deletion)
- [ ] An entry is self-contained: a reader who never saw the session can act on it
- [ ] Each entry states what it replaced or compressed where the destination is a skill (the skill stayed inside its size budget)
- [ ] Every kept item passes the bar: generalizable, verified, and not already documented
- [ ] Each item classified (type + generality); session-specific items dropped
- [ ] Destination per the table: amended the existing home when one exists (single ownership); a new doc only for a coherent new topic
- [ ] Entries follow the type templates (pitfall = symptom/cause/fix/verification; rule correction applied per `rem-write-better-skill` §10)
- [ ] Public content generalized per `rem-public-material-generalization` (placeholders, no machine paths, no project inventory; real names only when verified public + cited)
- [ ] The destination's own conventions followed (a skill follows `rem-write-better-skill`)
- [ ] Sources cited for facts; "verified YYYY-MM" dates present
- [ ] No stale content left behind (outdated rules removed, not flagged)
- [ ] Workarounds carry a lifecycle annotation (label, failure signal, iteration path) per `rem-write-better-skill` §10.5
- [ ] Session scratch left no trace: one-shot generators, patches and message files swept, the tree free of them per `rem-temp-files`
- [ ] Operational facts found in the session (toolchain / harness behaviour) were routed to their local overlay home — never left only in the conversation
- [ ] A multi-unit session left a unit/commit ledger (per-unit check evidence + commit hash + run-dir pointer) in a local document or run directory, not inside a skill
- [ ] The distillation committed per the repo's workflow (or handed to the user to commit)

## Cross-references

- `rem-write-better-skill` — writing conventions, structure, checklist contract, workaround lifecycle
- `rem-public-material-generalization` — what may appear in public content and how to generalize
- `rem-commit-workflow` — committing the distilled knowledge
- `rem-temp-files` — where a session's scratch and intermediates belong
