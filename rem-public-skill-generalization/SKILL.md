---
name: rem-public-skill-generalization
description: >
  Publication rules for the RemSkills collection: why public/open-source skill
  content must be generalized, what keeps real names, and how — placeholder
  types and paths, external configs, private companion skills in
  RemSkillsPrivate, link-based reference docs, and a pre-push verification
  checklist. Use when creating, editing, or publishing any skill, or when a
  skill needs project-specific facts without leaking them.
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
- **Machine paths are meaningless elsewhere.** `/home/<user>/Projects/...` or
  `D:\...` means nothing to a reader on another machine, and it goes stale as
  projects move.
- **Real names rot.** Type/module/plugin names change as the codebase evolves;
  a skill that names them reads as wrong a year later.
- **Placeholders that look meaningful mislead.** `FMyEventObject` still carries
  domain hints; abstract placeholders (`FFoo`) force the example to stand on
  structural merit (placeholder style: `rem-write-better-skill` §3).
- **The skill is a reference document, not a code snapshot.** It must stay
  correct long after writing, for readers unfamiliar with the domain.

## 2. Goals

- Public skills carry **generic knowledge + generic workflow** only.
- Nothing in a public skill can be traced to a specific machine, project, or
  private decision.
- Project-specific facts live **outside** the public skill: in external configs
  (tool-parameterized skills) or in **private companion skills** in
  `RemSkillsPrivate`.
- Private skills carry a **PRIVATE header** so a stray `git add -A` never ships
  them to the public repo.

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
criterion — any open-source reference anywhere may keep real names. Verify by
looking the name up (org / public repo) before writing it.

**Exceptions**: (a) actual working config files shipped alongside the skill
(e.g. `tools/engines.json`) may contain real paths — they are configuration,
not documentation; the SKILL.md text referencing them still uses placeholders.
(b) A skill whose entire purpose is documenting a specific public type's API
uses the real type name.

### 3.3 Repository split

| Repo | Contents |
|---|---|
| `RemSkills` (public) | Generalized skills only — everything here obeys this skill |
| `RemSkillsPrivate` (local-only) | Project-specific skills with a PRIVATE header; committed normally in the local repo (no remote), never pushed |

## 4. How to generalize

- **Placeholder types** — meaningless, domain-free (`FFoo`/`FBar`/`UFoo`/`EFoo`/`SFoo`);
  style owned by `rem-write-better-skill` §3.
- **Placeholder paths/names** — angle-bracket intent names:
  `<plugin-source-dir>`, `<engine-install-path>`, `<project-dir>`, `<ProjectName>`,
  `<target>`, `<config>`, `<test-prefix>`, `<nullrhi-crash-plugin>`, `<DepA>`.
  Never `/home/<user>/...` or `D:\...`; never `MyCompanyPlugin`-style names.
- **External configs** (tool-parameterized skills) — per-plugin config outside
  the skill (`<config-dir>/<Plugin>/local.json` + `adaptation-notes.md`); tools
  take `--config` and **error out** when missing (pattern: `rem-ue-plugin-adapter`).
- **Private companion skills** (workflow facts) — same name + `-local` in
  `RemSkillsPrivate`, PRIVATE header, mirrors the public skill's structure with
  the real values filled in (e.g. `rem-commit-workflow-local`).
- **Reference docs for live configs** — commit a **path-free snapshot copy**
  of a live project config (e.g. the commit-convention JSON); never a symlink
  (a link's target path leaks the machine layout) and no link/skip-worktree
  tricks. Refresh by copying the source file over the copy and committing;
  document that procedure in the skill.
- **Conversation-only disclosure** — concrete names may be stated in chat when
  needed; they never enter public files.
- **Citing public sources** — keep real names + cite; do not re-document what
  the source's own docs cover.

## 5. Verification (pre-push checklist)

The checklist is the contract — run it before pushing any skill:

- [ ] No machine paths: grep `[A-Za-z]:\`, `/home/`, `/Users/` in all files
- [ ] No private project/plugin/module/target names: grep the known names
- [ ] No project plugin inventory; third-party names only if verified public AND the mention adds value
- [ ] Placeholders are meaningless (no domain hints) — see `rem-write-better-skill` §3
- [ ] Generic paths use `<placeholder>` syntax
- [ ] Project-specific facts live in a `RemSkillsPrivate` skill with a PRIVATE header (committed locally, never pushed)
- [ ] Tool-parameterized skills require an external config (`--config`), erroring when missing
- [ ] Real-name content verified public (org/repo lookup) and cited
- [ ] Reference docs for live configs are path-free snapshot copies — no symlinks, no skip-worktree tricks

## Cross-references

- `rem-write-better-skill` — placeholder-type style (§3), structure & checklist conventions
- `rem-ue-plugin-adapter` — external-config pattern (per-plugin `local.json`, `--config`)
- `rem-commit-workflow-local` (RemSkillsPrivate) — example private companion skill
- ADR-001 — project plugin inventory is non-public by default
