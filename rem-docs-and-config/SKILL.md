---
name: rem-docs-and-config
description: >
  Documentation and configuration obligations for project changes: which
  artifacts exist (module docs, subsystem/technical docs, config references,
  decision records, editor tooltips), when a change must update which one, how
  to write a technical doc that stays useful, and how to document configuration
  so a reader can change it safely — with the review checklist. Use when writing
  or reviewing a change that adds a subsystem, a public API, a config property
  or a designer-facing behavior.
metadata:
  category: meta
  trigger: manual
---

# Documentation & Configuration

Owns one review dimension: **can a reader who was not in the room use this
change, and change its configuration, without reading the source?**

| Concern | Owner |
|---|---|
| Comment format and comment discipline (`/** */` vs `//`, why-not-what, Doxygen keywords) | `rem-cpp-best-practices` §4 |
| Keeping a *skill* current, delete-over-deprecate | `rem-write-better-skill` §10 |
| **Technical docs, config documentation, change-linked doc obligations** | this skill |

Project-specific facts — where docs live, which config files exist, which
subsystem owns which key — belong in the skill's `local/` overlay (when
present) or the project's own conventions doc, never here.

---

## 1. Documentation artifacts

| Artifact | Answers | Lives |
|---|---|---|
| Module doc (`README.md` next to the module) | what this module is for, how to depend on it, entry points | beside the code |
| Subsystem / technical doc | how it works, its invariants, its lifecycle, its extension points | one per subsystem, linked from the module doc |
| Config reference | every cvar/setting: purpose, default, range, effect, when it applies | with the subsystem doc or the project's config doc |
| Decision record (ADR) | why a hard-to-reverse choice was made | the project's decision log |
| Editor tooltip / property metadata | what a designer needs to set this value correctly | on the property itself |
| Code comment | why this line exists, which invariant it protects | at the declaration |

If a fact can be expressed **on the artifact itself** (a tooltip, a help
string, a clamp range), do that instead of writing prose elsewhere — metadata
cannot drift from the code it sits on, prose can.

## 2. Change → documentation obligation

| Change | Obligation |
|---|---|
| New subsystem | module doc section: purpose, entry points, lifecycle, config keys |
| New or changed config property | config reference entry **and** an editor tooltip / cvar help string |
| New or changed public API | declaration doc comment; update any usage doc that shows the old signature |
| New workflow or tooling step | the workflow doc it belongs to, plus the tool's own help output |
| Behavior visible to designers/players | the designer-facing doc or the property tooltip that controls it |
| Removed feature or key | **delete** its documentation — no deprecation banner, no "no longer used" note |
| Refactor with no behavior change | nothing, unless the doc named the old structure |

The obligation is per **artifact**, not per file changed: a one-line default
change still updates the config reference, because that is the only place a
reader looks for the default.

**Iteration vs. freeze.** The sequence is owned by `rem-orchestration`; external docs
(module doc, subsystem doc, config reference) are batched in the freeze docs pass. The
code-embedded obligations — API comments, tooltips, cvar help — still ship with the
change that triggers them.

## 3. Writing a technical doc

- **One doc per subsystem.** A doc per source file duplicates the include graph
  and rots; a doc per subsystem survives refactors.
- **Lead with the contract**: what the subsystem guarantees, what it requires,
  what it refuses to do. Implementation detail goes below, and only where it
  explains a guarantee.
- **State the invariants explicitly** — the facts that must remain true for the
  code to work. These are exactly the facts a reader cannot recover from the
  code alone.
- **Prefer a table to a diagram.** A state table or a config table is
  greppable, diffable and reviewable; a diagram is none of those. Use a diagram
  only for topology a table cannot express.
- **Date the volatile facts.** "Last verified: YYYY-MM" on anything tied to an
  engine version, an external service or a tool.
- **No code snapshots.** Show the shape of an API, not a copy of its
  implementation — snapshots rot silently (same reasoning as the placeholder
  rules in `rem-public-skill-generalization`).
- **Delete, don't deprecate.** A stale doc that says "this is no longer used"
  costs a reader more than a missing doc.

## 4. Documenting configuration

Every configurable value — cvar, config file entry, exposed property — needs
five facts, in the place a user will look for it:

| Fact | Where |
|---|---|
| Purpose (what it changes and why it exists) | help string / tooltip |
| Default and why that default | help string / tooltip |
| Valid range or accepted values | clamp range + `meta` / help string |
| Effect and scope (per-instance, per-world, global) | tooltip / config reference |
| When it applies (immediately, on restart, on reload) | help string / config reference |

Rules:

- **The default must be the safe value.** If enabling a feature by default is
  risky, the default is off and the doc says so; a documented footgun is still
  a footgun.
- **Express dependencies as metadata, not prose** — the mechanism is owned by
  `rem-cpp-best-practices` §10; this skill's obligation is that the condition
  stays discoverable to the reader.
- **Always state the unit.** A number without a unit is a bug report waiting to
  happen; pair the value with `meta = (ForceUnits = "<unit>")` (see
  `rem-cpp-best-practices` §10) and repeat the unit in the tooltip.
- **Group related keys** in the config file and give the group a header
  comment; an ungrouped config file is unreadable at scale.
- **Deprecated keys**: either delete the key and its doc in the same change, or
  (when a migration window is required) document the replacement and the removal
  condition — never leave a key that silently does nothing.
- **A cvar/command help string is the documentation.** If it is empty, the
  value is undocumented, whatever the external doc says.

## Checklist

Before declaring a documentation/config change (or reviewing one) done:

- [ ] §2 — every row of the obligation table was applied to this change, per artifact
- [ ] §1 — a fact expressible as tooltip/metadata is on the artifact, not only in prose
- [ ] §3 — technical docs are per subsystem, lead with the contract, and state the invariants
- [ ] §3 — volatile facts carry "Last verified: YYYY-MM"
- [ ] §3 — no code snapshots; the doc describes the API shape, not a copy of it
- [ ] §3 — superseded docs were deleted, not flagged as deprecated
- [ ] §4 — every new/changed config value documents purpose, default, range, scope and when it applies
- [ ] §4 — defaults are the safe value and are stated
- [ ] §4 — every numeric config value states its unit (and pairs with `ForceUnits`)
- [ ] §4 — mode-dependent values keep their condition discoverable (mechanism: `rem-cpp-best-practices` §10)
- [ ] §4 — every new cvar/console command has a non-empty help string
- [ ] §4 — removed keys are deleted from code, config and docs in the same change
