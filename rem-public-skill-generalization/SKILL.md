---
name: rem-public-skill-generalization
description: >
  Publication rules for the RemSkills collection: why public/open-source skill
  content must be generalized, what keeps real names, and how — placeholder
  types and paths, external configs, the private local overlay and its
  per-skill reference files, link-based reference docs, and a pre-push
  verification checklist. Use when creating, editing, or publishing any skill,
  or when a skill needs project-specific facts without leaking them.
metadata:
  category: meta
  trigger: manual
---

# Public-Skill Generalization

This skill is the **single owner** of the generalization rules for the RemSkills
collection (per `rem-write-better-skill` §11, a rule lives in exactly one skill —
copies drift). It was extracted from `rem-write-better-skill` §3a/§6/§8.5.
Apply it to every skill before it is pushed to a public repository.

A skill in the public `RemSkills` repo is **visible to anyone, forever**. The
rules below decide what a public skill may say.

---

## 1. Why generalize

- **A public skill is permanent and public.** Real project names, paths, and
  internal decisions leak private information: repository layout, module
  structure, unreleased features, tooling choices.
- **Machine paths are meaningless elsewhere.** A literal home or drive path
  means nothing to a reader on another machine, and it goes stale as projects
  move.
- **Real names rot.** Type/module/plugin names change as the codebase evolves;
  a skill that names them reads as wrong a year later.

## 2. Goals

- Public skills carry **generic knowledge + generic workflow** only.
- Nothing in a public skill can be traced to a specific machine, project, or
  private decision.
- Project-specific facts live **outside** the public skill: in external configs
  (tool-parameterized skills) or in the **local overlay** — one private skill
  (`rem-local`) whose `references/` holds one file per public skill.
- The overlay and its reference files carry a **PRIVATE header** so a stray
  `git add -A` never ships them to the public repo.

## 3. Scope

### 3.1 What must be generalized (non-public content)

| Category | Example |
|---|---|
| Machine paths | `<engine-install-path>`, `<project-dir>` |
| Project / target / module / asset names | `<ProjectName>`, `<DepA>`, `<target>` |
| Build & test configuration | `<config>`, `StartsWith:<test-prefix>` |
| Project plugin inventory | **non-public by default** (ADR-001): real third-party names only when the plugin is verified public AND the mention adds reader value — the project's *use* of it is still project fact |
| Private decisions | disabled-plugins lists, dependency policy, dev-config choices |
| Private type / convention names | `Foo::Math::Modulo` → placeholder |

### 3.2 What keeps real names (public content)

| Content | Rule |
|---|---|
| Engine APIs (`TObjectPtr`, `FInstancedStruct`, `Cast<T>`) | Real names, cite the header; don't re-document |
| Any open-source library from anywhere (`transrangers`, `fmt`, `strong_alias`, `CrystalNodes`) | Real names, cite their docs |
| Epic conventions | Real names, cite the source |
| Rem ecosystem content visible at <https://github.com/RemRemRemRe> | Real names (the org is the Rem-family lookup reference) |

The org lookup is a lookup aid for Rem-family content, **not** the general
criterion — any open-source reference anywhere may keep real names. Verify a
name **anonymously** before writing it:
`git -c credential.helper= -c core.askPass= ls-remote --heads <repo>` — a stored
credential quietly resolves a private repository, so an authenticated lookup
proves nothing. A name that fails that check is generalized, or moved to the
local overlay (`rem-local`); a `Rem` prefix is not evidence of ecosystem
membership. `tools/lint-skills.mjs` enforces the outcome: every Rem-family
identifier in a skill (`RemXxx` and the type-prefixed `URemXxx`/`ERemXxx`
forms) must be listed in `tools/public-names.json` with a public source.

Shipped files are **not** exempt: the leak and name checks scan a skill's
scripts, templates and configs exactly like its prose, and the repository-level
files (README, LICENSE, workflows, hooks, `tools/`) in the same pass, because a
file that ships ships to everyone. A shipped file is therefore placeholder-only
— a skill holds no machine or project data (`rem-ue-plugin-adapter`'s config
templates carry `<...>` placeholders for this reason). The only file not scanned
is `tools/public-names.json`, which *is* the reference data for the name check.
**Exception**: a skill whose entire purpose is documenting a specific public
type's API uses the real type name.

### 3.3 Repository split

| Repo | Contents |
|---|---|
| `RemSkills` (public) | Generalized skills only — everything here obeys this skill |
| `RemSkillsPrivate` (private, no public remote) | The **local overlay**: one skill (`rem-local` — PRIVATE header, mapping table, precedence rule) plus `references/<public-skill>.md` files holding the real values; committed normally in the local repo; a private remote is allowed, a public one never |

## 4. How to generalize

- **Placeholder types** — meaningless, domain-free (`FFoo`/`FBar`/`UFoo`/`EFoo`/`SFoo`);
  style owned by `rem-write-better-skill` §3.
- **Placeholder paths/names** — angle-bracket intent names:
  `<plugin-source-dir>`, `<engine-install-path>`, `<project-dir>`, `<ProjectName>`,
  `<target>`, `<config>`, `<test-prefix>`, `<nullrhi-crash-plugin>`, `<DepA>`.
  Never a literal home or drive path, and never an example project name.
- **External configs** (tool-parameterized skills) — per-plugin config outside
  the skill (`<config-dir>/<Plugin>/local.json` + `adaptation-notes.md`); tools
  take `--config` and **error out** when missing (pattern: `rem-ue-plugin-adapter`).
- **Local overlay** (workflow facts) — the private `rem-local` skill plus one
  `references/<public-skill>.md` per adapted skill: the file name is the public
  skill's name, so the public side maintains no list. Reference files hold **no
  skill frontmatter** — pi loads any `.md` that carries it as a skill, which
  would restore the always-on description this pattern exists to avoid. Overlay
  values override the public defaults, and a project-specific **rulebook**
  (rules, not values) stays a skill instead: the split is public/private *and*
  rules/values. The pointer to the overlay is a **body** sentence, never a
  description line — a sentence every adapted skill repeats is duplicated
  always-on text (`rem-write-better-skill` §11).
- **Reference docs for live configs** — commit a **path-free snapshot copy**
  of a live project config (e.g. the commit-convention JSON); never a symlink
  (a link's target path leaks the machine layout) and no link/skip-worktree
  tricks. Refresh by copying the source file over the copy and committing;
  document that procedure in the skill.
- **Conversation-only disclosure** — concrete names may be stated in chat when
  needed; they never enter public files.
- **Name allowlist** — the mechanical half of the rule:
  `tools/public-names.json` lists every Rem-family name a public skill may
  state — `publicNames` for what a public repository actually contains,
  `documentedExamples` for a placeholder or engine type — each with its source.
  The lint matches `RemXxx` and the type-prefixed `URemXxx`/`ERemXxx` forms, and
  an unlisted name fails it, so the check is a gate rather than a memory test.
- **Case catalogues** (false positives, pitfalls, "verified YYYY-MM" notes) —
  state the **shape** of the case, not the file it was seen in. A private file
  name in a catalogue entry leaks the plugin layout and gives the reader a
  citation they can never resolve; cite a public path (engine header, public
  repo) or describe the construct instead.
- **Citing public sources** — keep real names + cite; do not re-document what
  the source's own docs cover.

## 5. Verification (pre-push checklist)

The checklist is the contract — run it before pushing any skill:

- [ ] No machine paths — drive-letter paths, posix and macOS home paths (enforced by `tools/lint-skills.mjs`)
- [ ] The collection lint passes before pushing — `node tools/lint-skills.mjs`; the run obligation and the tool itself are owned by `rem-write-better-skill` §8
- [ ] Publishing was authorized as its own explicit instruction, never inferred from an approval of the edits (`rem-commit-workflow` — Publishing is a separate gate)
- [ ] No private project/plugin/module/target/type names — the lint fails on any Rem-family identifier (`RemXxx`, `URemXxx`) missing from `tools/public-names.json`; a name is added only with a public source
- [ ] Names verified **anonymously** (`git -c credential.helper= -c core.askPass= ls-remote --heads <repo>`) — an authenticated lookup resolves private repositories and proves nothing
- [ ] Catalogue citations name a public path or the case's shape, never a private file ("observed in `<private-file>`")
- [ ] Leak and name checks cover every non-binary file that ships — the skill's own files (`SKILL.md`, `references/**`, `tools/**`) and the repository-level files; only the allowlist itself is exempt
- [ ] A leak that is already pushed is fixed forward (public history is permanent; rewriting it is a separate, deliberate call — `rem-rewrite-commit-history`)
- [ ] No project plugin inventory; third-party names only if verified public AND the mention adds value
- [ ] Placeholders are meaningless (no domain hints) — see `rem-write-better-skill` §3
- [ ] Generic paths use `<placeholder>` syntax
- [ ] Project-specific facts live in the local overlay (`rem-local` → `references/<this-skill>.md`) with a PRIVATE header — one always-loaded description for the layer, not one per adaptation
- [ ] No `.md` outside `SKILL.md` carries skill frontmatter (each one would be loaded as a skill and pay an always-on description)
- [ ] Tool-parameterized skills require an external config (`--config`), erroring when missing
- [ ] Real-name content verified public (org/repo lookup) and cited
- [ ] Reference docs for live configs are path-free snapshot copies — no symlinks, no skip-worktree tricks

## Cross-references

- `rem-write-better-skill` — placeholder-type style (§3), structure & checklist conventions
- `rem-ue-plugin-adapter` — external-config pattern (per-plugin `local.json`, `--config`)
- `rem-local` (RemSkillsPrivate) — the local overlay: mapping table, precedence rule, per-skill reference files
- `tools/public-names.json` — the Rem-family name allowlist consumed by `tools/lint-skills.mjs`
- ADR-001 — project plugin inventory is non-public by default
