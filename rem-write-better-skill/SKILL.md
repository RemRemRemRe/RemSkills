---
name: rem-write-better-skill
description: >
  Guidelines for writing maintainable, clean skills (custom instructions for AI coding
  agents). Covers frontmatter format, file structure, placeholder types, self-contained
  examples, exception handling, citations, table formatting, and checklist validation.
  Use when creating a new skill or updating an existing one. Publication/generalization
  rules live in `rem-public-material-generalization`.
metadata:
  category: meta
  trigger: manual
---

# Skill Writing Guidelines

This skill defines the shared conventions for writing and maintaining skills in
the RemSkills collection. Apply it whenever you create a new skill or update an
existing one.

A skill is a reference document, not a code snapshot. It should remain readable
and correct long after it was written, even for readers unfamiliar with the
specific domain.

---

## 1. Frontmatter Format

Every skill file (`SKILL.md`) starts with YAML frontmatter enclosed in `---`:

```yaml
---
name: skill-name
description: >
  Short summary of what the skill covers and when to use it.
  Use `>` for multi-line descriptions — lines are joined with spaces.
metadata:
  category: meta
  trigger: manual
---
```

| Field | Convention |
|-------|-----------|
| `name` | Lowercase kebab-case, matching the folder name |
| `description` | Use `>` for multi-line text (joins lines with spaces); describe what the skill covers AND when to trigger it. Must use generic placeholders — no project-specific names, local paths, or machine-dependent values (see §3 and `rem-public-material-generalization`). |
| `category` | `meta` (default) or `workflow` — a workflow skill drives a procedure; a meta skill carries rules |
| `trigger` | `manual` (default, loaded on demand) or `always` — `always` means the constraint must also be stated **in the description**: harnesses keep only names + descriptions in context and load `SKILL.md` on demand (progressive disclosure — verified 2026-09 in pi, whose docs state only descriptions are always in context), so the description is the surface guaranteed to be present. Keep such a file under 2 KB |

---

## 2. File & Directory Structure

```
RemSkills/
└── skill-name/
    ├── SKILL.md          ← the skill content (required)
    └── references/       ← supplementary files (optional)
        └── example.md
```

- One skill per folder
- The folder name is the skill name in kebab-case
- `SKILL.md` is the entry point — all other files are supplementary
- Put references, images, example data in subfolders under the skill folder
- No `README.md` — `SKILL.md` serves that role

**Keep the main file lean.** The agent loads `SKILL.md` into its context on
every trigger — it is an index and decision surface, not a handbook:

| Content | Home |
|---|---|
| Rules, decision tables, checklists, short self-contained examples | `SKILL.md` |
| Long code listings, boilerplate templates, engine API tables, pitfall catalogues | `references/` |

A rule of thumb: if a section is only consulted while doing the work (not
while deciding how to work), it belongs in `references/`. If the main file
grows past what a reader can scan in one pass, split it.

### Splitting is a move — verify it mechanically

Detail that moves into `references/` must arrive **verbatim**; a rewritten move
is a second copy that will drift. Two failures of a mechanical move are silent,
and nothing reports either:

- **Lost text.** Verify with a line-level presence check — every non-blank line
  of the original must still exist in `SKILL.md` plus every `references/*` file
  — not by reading the diff. Expect one false positive: a sentence split at its
  sentence boundary shows as missing, because the comparison is line-based.
- **Broken section references.** A `<file> §Section` pointer to content that
  moved neither follows that content nor errors. After a split, re-resolve every
  `§` reference in both the main file and the reference by hand.

Also check what the move *leaves behind*: a `SKILL.md` section whose body was
entirely detail becomes a stub. Keep it only when the heading is a useful
signpost, and prefer folding several stubs into one `## Reference files` table
(`File` / `When to load`) over a row of one-line sections — four pointers to one
file is four doors to the same room.

**Size budget** (enforced by `tools/lint-skills.mjs`): `SKILL.md` warns above
32 KB and fails above 48 KB, with the closing checklist excluded from the
budget — it is the contract and must stay; a `trigger: always` skill fails above
2 KB. The budget exists because the file is loaded on every trigger — detail
belongs in `references/`, the rules and the checklist stay in `SKILL.md`.

**Always-on budget** (same tool): every `description` is in context on every
request, so the collection budgets their sum (warns above 10,500 chars) and
warns on a single description above 800 chars. Each run prints the running
total, and `--discovery <root>...` reports it for any skills root, including
ones outside this repository. §11 governs how to spend it.

### A mechanical check must be able to fail, and must model its own exceptions

A check that cannot go red proves nothing, and two failure modes are silent:

- **Vacuous green.** A check that collects candidates and passes on an empty set
turns an extraction bug into a pass. Treat "found 0 candidates" as a failure,
and mutate the input once — add a deliberate violation — to watch the check fire
before trusting it.
- **A legitimate exception reported as a failure.** A collection-wide assertion
("no file does X") usually has one artifact that *owns* X and may legitimately
do it. Exempt it explicitly, by name and with the reason, rather than letting the
check report the one correct case as a defect: a check that goes red where the
content is right gets waived, and then deleted.

---

## 3. Use Generic Placeholder Types

Use **completely meaningless, business-unrelated placeholder names** in code
examples — never real project type names. Names must carry zero domain hints
(no "Component", "Event", "Data", "Manager", etc.):

| Do this | Not this |
|---------|----------|
| `FFoo` / `FBar` / `FBaz` | `FMyEventObject` |
| `UFoo` / `UBar` / `UBaz` | `UMyTriggerSection` |
| `EFoo` / `EBar` / `EBaz` | `EMyStateType` |
| `SFoo` / `SBar` | `SWarningDialog` |

**Why:** The skill is a reference, not a code snapshot. Real type names go stale
when the codebase evolves. Meaningful placeholder names (e.g., `FMyEventObject`)
still carry domain hints that confuse readers and create false expectations
about structure. Completely abstract names (`FFoo`, `FBar`) force the example
to stand on its own structural merit.

### 3a. Generic Placeholder Paths and Names

Generic placeholder paths/names, the public-content rules, and the
public/private skill split are owned by `rem-public-material-generalization`
(§3 scope, §4 methods). This section no longer restates them — see that skill.

---

## 4. Self-Contained Code Examples

Every code example must be understandable **without prerequisite knowledge** of
any specific codebase:

- Declare all referenced types used in the example
- Show the necessary `#include` directives if they're critical to the point
- Explain what the example demonstrates, not just what it does
- Avoid references to "the project's X system" without describing what X is

```cpp
// GOOD — self-contained example:
template <std::derived_from<UObject> T>
decltype(auto) GetDefaultRef()
{
    return *::GetDefault<T>();
}
```

```cpp
// AVOID — assumes reader knows what FRemComponentBase is:
template <std::derived_from<FRemComponentBase> T>
auto FindComponent();
```

---

## 5. Be Specific About Exceptions

Every rule should list its **exceptions explicitly** — don't leave them
implicit for the reader to guess:

| Vague | Specific |
|-------|----------|
| "No abbreviations" | "No abbreviations except for well-known acronyms (FOV, LOD), the abbreviation that IS the type name (IO), and template parameters (T)" |
| "Always use const" | "Always use const except on locals that will be moved (const inhibits move) and on value parameters in declarations" |

When a rule has a justification, state it. When it has an escape hatch,
describe the escape hatch and the criteria for using it.

## 5.5 One Language per Skill

Each skill file uses **exactly one language**. Public `RemSkills` skills are
English; private `RemSkillsPrivate` content — local-only skills and the tracked
overlay values — is Chinese (the author's working
language). Never mix: no bilingual headings (`Goals (目标)`), no bilingual
descriptions, no translated sentences inline. Technical terms — commands, type
names, plugin names, config values, warning keywords such as `PRIVATE` — stay
as they are; that is vocabulary, not language mixing. Frontmatter
`description` follows the same rule.

Language-switch links are navigation vocabulary: the label is written in the
**target language** — the English README links to the Chinese doc as `中文版`,
the Chinese doc links to the English one as `English version`. This is not
language mixing.

---

## 6. Cite Sources

When a convention comes from an external authority or a specific file, cite it
so future readers can **verify it is still current**:

- Engine header paths (e.g., `Engine/Source/Runtime/Core/Public/...`)
- Project files (e.g., `Plugins/<DepA>/Source/...`)
- External references (Epic docs, CppCoreGuidelines, etc.)
- Use relative paths from the project root where possible

Bad: "Convention says to always use `TObjectPtr`"
Good: "`TObjectPtr<T>` for all `UPROPERTY` UObject members (required since UE 5.1; see `UObject/Pointer.h`)"

**Public content vs. generalization** — which content keeps real names and
what must be generalized (and how) is owned by `rem-public-material-generalization`
(§3 scope, §4 methods). This section no longer restates those rules.

---

## 7. Prefer Tables for Reference Content

Reference material is **more scannable as tables** than as prose. Use tables
for:

| Content type | Why tables |
|-------------|-----------|
| API mappings | Side-by-side comparison is immediate |
| Type comparisons | Decision matrices are visual rather than prose |
| Decision flowcharts | "If X then Y" is clearer as rows |
| Lists of options with descriptions | Reader can scan the option column independently |

Prose is appropriate for:
- Explanations and rationale (why a rule exists)
- Tutorial-style walkthroughs
- Describing architectural concepts

A good skill uses **both**: tables for the reference surface, prose for the
depth and reasoning.

---

## 8. Checklist Is the Contract

Every skill that defines rules should have a **closing checklist**. The
checklist is what actually gets applied at review time — it is the contract
between the skill author and the user.

For every rule in the body of the skill, there must be either:

- A corresponding item in the checklist, or
- A clear reason why it doesn't need one (e.g., "handled automatically by IDE tooling")

```markdown
## Checklist

Before applying this skill:
- [ ] Rule 1 from section X
- [ ] Rule 2 from section Y
- [ ] Rule 3 from section Z — handled by IDE, no manual check needed
```

The checklist format uses `- [ ]` markdown checkboxes. Each item is one
line — avoid multi-paragraph checklist entries.

**Mechanical check.** The collection ships a structural lint:
`node tools/lint-skills.mjs` (zero dependencies). It enforces the parts of this
skill that fail silently — frontmatter shape and allowed values, `name` vs
folder, a description that states a trigger, the closing checklist, and the
size budget. The leak and name checks it also runs are owned by
`rem-public-material-generalization`.

**Always-on audit.** The same tool answers "what does this cost every request?":
`node tools/lint-skills.mjs --discovery <root>...` lists every skill a skills root
puts in context with its description size, and fails when a non-`SKILL.md` file
carries skill frontmatter. Run it over both roots after adding or adapting a skill.

**Run it before committing a skill change**, and never let a failing run reach
the remote: the repo's `pre-push` hook (`.githooks/pre-push`, installed with
`git config core.hooksPath .githooks`) runs it again before anything leaves the
machine. Errors must be fixed; a warning is either fixed or explained in the
commit message. When the tool is absent (skills copied outside this collection),
apply this checklist manually — the lint is the mechanical half of it, not a
replacement for it.

---

## 8.5 Externalize Config & Anonymize Project Data

Externalizing project config and anonymizing project data is owned by
`rem-public-material-generalization` (§4 methods: external per-plugin configs,
per-skill `local/` overlays linked from `RemSkillsPrivate`, link-based
reference docs). This section no longer restates the rules.

---

## 9. When to Create a Skill vs. Inline Instructions

| Situation | Choice |
|-----------|--------|
| Content applies to **all** work in a domain (e.g., all C++ in a project) | Create a skill |
| Content is **reusable** across sessions and tasks | Create a skill |
| Content is **specific to a single task** | Inline instructions in the prompt |
| Content is a **one-time debugging note** | Inline instructions |

If you find yourself pasting the same rules 3+ times across sessions, it's
time for a skill.

---

## 10. Keep It Current

- **Date statements of fact** — "Since UE 5.1" or "Last verified: 2026-07"
  helps readers judge freshness
- **Remove dead content** — if a section no longer applies to the current
  state of the codebase, delete it; don't add a "DEPRECATED" banner
- **Prefer deletion over deprecation** — stale content is worse than missing
  content; the reader can always find old versions in git history
- **Use generic placeholder types** (see Section 3) so examples don't rot
  when a specific class is renamed

**When to update a skill** (concrete triggers — not "whenever it feels stale"):

| Trigger | Action |
|---|---|
| A project convention changed (build flags, naming, module layout) | Update the rule AND its checklist item |
| The same pitfall/instruction got pasted or re-explained 3+ times across sessions | Promote it into the skill (same bar as §9 for creation) |
| Engine version bump changed an API the skill documents | Re-verify cited headers/paths; update the dated facts |
| A rule caused confusion or was ignored twice | Rewrite it or delete it — ignored rules are dead weight |

Session lessons that should improve a document, a process **or** a skill are
harvested and routed by `rem-session-knowledge-distillation` — run it to pick
the destination, then apply this section for a skill destination.

## 10.5 Mark Workarounds and Iterative Plans

A stopgap — a workaround, a local patch pending an upstream merge, a solution
that still needs iteration — must carry its own lifecycle annotation, or it
silently rots into a permanent convention:

- **Label it**: mark the entry `Workaround` / `Temporary` / `Pending upstream`
  so it is clearly not the final state
- **State the failure signal**: the observable symptom that means the entry is
  stale or broken and needs re-verification (e.g. "the headless run crashes
  again with `EXCEPTION_ACCESS_VIOLATION` at `<file>`")
- **State the iteration path**: the concrete steps that converge to the final
  state (upstream PR → merge → sync → delete this entry), ending with the
  action that removes the annotation

Never document only *how* a stopgap is used without saying *why it is
temporary* and *when it can be removed*. Once resolved, delete the entry —
keep no "DEPRECATED" banner (§10).

---

## 11. Conflicts and Overlap Between Skills

A collection grows; skills will overlap. Handle it explicitly instead of
letting each skill restate the same rules:

| Situation | Rule |
|---|---|
| Two skills cover the same ground | Single ownership: keep the rule in ONE skill; the other cross-references it ("see `<other-skill>` §N") |
| Two descriptions claim the same situation | One entry point: every *situation phrase* in a "when to use" half belongs to exactly one description; the other skills state their distinctive trigger and point at the entry point |
| A general skill and a specialized skill disagree on a domain point | The specialized skill wins for its domain; the general skill links to it instead of restating |
| A skill is loaded alongside others and rules seem contradictory | The skill that names the concrete domain (module, system, workflow) overrides the generic rule |

Copying a rule into two skills is the failure mode to avoid — the copies
silently drift apart and each review finds a different version.

Descriptions pay their cost on **every** request, so the same reasoning applies
there with one twist: optimize **duplication, not length**. A long description
that enumerates genuinely distinct triggers earns its keep; a short one that
restates a sibling's situation does not. The check is mechanical — take each
situation phrase ("when committing", "when a submodule lags its remote"), count
how many descriptions claim it, and treat any count above one as the defect.

Two corollaries the same measurement makes visible:

- **A pointer is a body sentence.** "The real values live in the overlay", "the
  config sits in `<config-dir>`", "call `<tool> --config`" — text that every
  adapted skill has to repeat is not a trigger, so it belongs in the body, where
  it is read once the skill has loaded. Repeating it across N descriptions pays
  it on every request of every session, and the repetition itself inflates the
  trigger overlap this section exists to remove.
- **Trimming needs evidence.** Delete a *situation* phrase only when another
  skill owns that situation. Do not shorten the "what it covers" half on style
  grounds: retrieval matches the whole description, so a step list that reads
  like detail may be the only surface a differently-worded request ever hits.
  Cut duplication, not coverage — and collect the phrasings users actually use
  before cutting anything.

## Checklist

Before publishing a new or updated skill:

- [ ] Frontmatter present with `name`, `description`, `metadata`
- [ ] Single language per file — English (public RemSkills) or Chinese (private RemSkillsPrivate content); no bilingual headings, descriptions, or inline sentences; language-switch link labels use the target language (navigation vocabulary, not mixing)
- [ ] `description` covers both what the skill covers AND when to use it — and uses only generic placeholders (no project names, no local paths)
- [ ] Description duplication audited: each situation phrase is claimed by exactly one description; overlapping skills name the entry point instead of restating the situation
- [ ] One `SKILL.md` per folder; folder name matches `name` in kebab-case
- [ ] Main `SKILL.md` is lean: rules/decision tables/checklist only; long listings and pitfall catalogues live in `references/`
- [ ] After a split, the move was verified mechanically (line-level presence check) and every `§` reference still resolves
- [ ] All code examples use completely meaningless placeholder types (`FFoo` / `FBar`, no domain hints like "Event" or "Component")
- [ ] All file paths, plugin names, and config values in examples use generic placeholders (`<plugin-source-dir>`, `<DepA>`) — no literal machine path and no example project name
- [ ] Every code example is self-contained (no prerequisite domain knowledge assumed)
- [ ] No machine paths, project names, or per-project decisions inside the skill — externalized per `rem-public-material-generalization` (per-plugin configs, per-skill `local/` overlays, link-based reference docs)
- [ ] First-use/setup instructions present (how to create the external configs; tools error out when they are missing)
- [ ] Every rule lists exceptions explicitly where they exist
- [ ] Sources cited for conventions that come from external authorities or specific files; dated facts carry "Since UE X.Y" or "Last verified: YYYY-MM"
- [ ] Public-content / generalization rules per `rem-public-material-generalization` — real names only for verified-public content (cited); everything else generalized, or moved to the private overlay (values) or a private skill (rules)
- [ ] Reference content formatted as tables where appropriate
- [ ] Overlapping rules have single ownership — cross-referenced, not copied
- [ ] Closing checklist covers every rule in the body (or has a stated reason why not)
- [ ] `node tools/lint-skills.mjs` reports 0 errors — every warning fixed or explained (when the tool is present)
- [ ] No stale or deprecated content — outdated sections removed, not flagged
- [ ] Workarounds and iterative plans carry a lifecycle annotation: label (`Temporary` / `Pending upstream`), failure signal, iteration path ending in the deletion step
