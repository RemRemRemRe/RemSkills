---
name: rem-write-better-skill
description: >
  Guidelines for writing maintainable, clean skills (custom instructions for AI coding
  agents). Covers frontmatter format, file structure, placeholder types, self-contained
  examples, exception handling, citations, table formatting, and checklist validation.
  Use when creating a new skill or updating an existing one.
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
| `description` | Use `>` for multi-line text (joins lines with spaces); describe what the skill covers AND when to trigger it. Must use generic placeholders — no project-specific names, local paths, or machine-dependent values (see §3a). |
| `category` | Always `meta` for RemSkills |
| `trigger` | Always `manual` — skills are loaded explicitly, never auto-triggered |

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

---

## 3. Use Generic Placeholder Types

Use **completely meaningless, business-unrelated placeholder names** in code
examples — never real project type names. Names must carry zero domain hints
(no "Component", "Event", "Data", "Manager", etc.):

| Do this | Not this |
|---------|----------|
| `FFoo` / `FBar` / `FBaz` | `FRemComponentBase` or `FMyEventObject` |
| `UFoo` / `UBar` / `UBaz` | `URemMoverComponent` or `UMyTriggerSection` |
| `EFoo` / `EBar` / `EBaz` | `ERemTimerType` |
| `SFoo` / `SBar` | `SWarningDialog` |

**Why:** The skill is a reference, not a code snapshot. Real type names go stale
when the codebase evolves. Meaningful placeholder names (e.g., `FMyEventObject`)
still carry domain hints that confuse readers and create false expectations
about structure. Completely abstract names (`FFoo`, `FBar`) force the example
to stand on its own structural merit.

### 3a. Use Generic Placeholder Paths and Names

The generic placeholder rule extends beyond C++ types to **all identifiers** that
could tie the skill to a specific project or machine:

| Category | Do this | Not this |
|----------|---------|----------|
| File paths | `<plugin-source-dir>/Source/...` | `/home/<user>/Projects/MyPlugin/Source/...` |
| Engine paths | `<engine-install-path>/UE_5.7` | `/opt/UE/5.7/Engine/...` |
| Output paths | `<output-dir>/Win64/5.7/...` | `/builds/Win64/5.7/...` |
| Plugin names | `<PluginName>`, `<MyPlugin>` | `MyCompanyPlugin` |
| Dependency names | `<DepA>`, `<DepB>` | `MyDependencyA` |
| Module names | `<DepModule>` | `MyCompanyExtensionModule` |
| Git remotes | `<upstream-remote>` | `origin`, `upstream` (unless standard) |

**Why:** Paths like `/home/<user>/Projects/MyPlugin/...` are meaningless to anyone who doesn't
share the author's exact directory layout. They also change over time as projects
are reorganized. Generic placeholders (`<plugin-source-dir>`) communicate intent
without locking the skill to a specific machine.

**Exception**: `engines.json` and similar config files that are **actual working
files** shipped alongside the skill may contain real paths — they're configuration,
not documentation. The SKILL.md content that references them should still use
placeholders (e.g., `engines.json` is at `<skill-dir>/tools/engines.json`).

Exception: if the skill's entire purpose is to document a specific type's
public API, use the real type name — the skill is the reference for that
specific API.

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

**Public content needs no generalization.** Engine APIs, open-source
libraries, and Epic conventions are public knowledge — keep their real names
(and do not re-document what their own docs already cover; cite them
instead). This applies to **any** open-source library or project: if its
source is publicly available somewhere, its real names are fine.
Generalization applies **only** to content that is not public anywhere.

For the Rem ecosystem specifically, <https://github.com/RemRemRemRe> is the
local reference: if a Rem plugin or skill is visible in the public
repositories of that GitHub organization, it is public and keeps its real
names. That link is a lookup aid for Rem-family content, **not** the general
criterion — any open-source reference anywhere may keep real names.

| Content | Rule |
|---|---|
| Engine APIs (`TObjectPtr`, `FInstancedStruct`, `Cast<T>`) | Real names, cite the header |
| Open-source libraries (`transrangers`, `fmt`, `strong_alias`) — from any source | Real names, cite their docs; don't duplicate their documentation |
| Epic coding conventions | Real names, cite the source |
| Rem ecosystem content visible at <https://github.com/RemRemRemRe> | Real names (local reference for the Rem family) |
| Content that is not public anywhere | Generalize (`<CommonPlugin>`, `<SharedBuildRules>`, `Foo::`); state the concrete names only in conversation |

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

---

## 8.5 Externalize Config & Anonymize Project Data

A skill is **generic knowledge + generic workflow** — it must never carry
machine paths, project names, or project-specific decisions. Keep project
data outside the skill and anonymize what the skill references.

### Three layers

| Layer | Content | Where it lives |
|-------|---------|----------------|
| Skill itself | Generic workflow, decision trees, conventions | `SKILL.md` |
| Generic knowledge | Engine/API differences, error patterns | `references/`, `tools/` templates |
| External config | Per-plugin config + per-plugin adaptation knowledge | outside the skill, e.g. `<config-dir>/<Plugin>/` |

### Rules

1. **Skill directory stays clean** — no machine paths, no project names, no
   per-plugin decisions inside `SKILL.md`, `references/`, or `tools/`.
2. **Per-plugin data lives outside the skill** — each external plugin gets
   its own config directory (e.g. `<config-dir>/<Plugin>/local.json` +
   `adaptation-notes.md`). The skill's tools take the config via a required
   parameter (`--config`) and **error out when it is missing or mismatched**.
3. **Machine-specific paths never enter the skill** — engine roots, plugin
   source paths, dependency source paths stay in external local configs.
   Templates in the skill use placeholders only.
4. **Anonymize code examples** — examples use meaningless placeholders
   (`FFoo`, `Foo::Math::Modulo`, `FooNotNull.h`). Public/open-source project
   names may appear only as source citations (see §6); anything not public
   must be anonymized or moved to the external adaptation notes.
5. **First-use instructions live in the skill** — a "first-time setup"
   section (in `tools/README.md` or `SKILL.md`) explains how to create the
   external configs and what happens when they are missing.

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

---

## Checklist

Before publishing a new or updated skill:

- [ ] Frontmatter present with `name`, `description`, `metadata`
- [ ] `description` covers both what the skill covers AND when to use it — and uses only generic placeholders (no project names, no local paths)
- [ ] One `SKILL.md` per folder; folder name matches `name` in kebab-case
- [ ] Main `SKILL.md` is lean: rules/decision tables/checklist only; long listings and pitfall catalogues live in `references/`
- [ ] All code examples use completely meaningless placeholder types (`FFoo` / `FBar`, no domain hints like "Event" or "Component")
- [ ] All file paths, plugin names, and config values in examples use generic placeholders (`<plugin-source-dir>`, `<DepA>`, not `/home/<user>/Projects/MyPlugin` or `MyCompanyPlugin`)
- [ ] Every code example is self-contained (no prerequisite domain knowledge assumed)
- [ ] No machine paths, project names, or per-project decisions inside the skill — externalized to per-plugin configs (e.g. `<config-dir>/<Plugin>/local.json`) referenced via a required `--config`-style parameter
- [ ] First-use/setup instructions present (how to create the external configs; tools error out when they are missing)
- [ ] Every rule lists exceptions explicitly where they exist
- [ ] Sources cited for conventions that come from external authorities or specific files; dated facts carry "Since UE X.Y" or "Last verified: YYYY-MM"
- [ ] Public content (engine APIs, any open-source library) keeps real names and is cited, not re-documented; only content that is not public anywhere is generalized (Rem family: check <https://github.com/RemRemRemRe>)
- [ ] Reference content formatted as tables where appropriate
- [ ] Closing checklist covers every rule in the body (or has a stated reason why not)
- [ ] No stale or deprecated content — outdated sections removed, not flagged
