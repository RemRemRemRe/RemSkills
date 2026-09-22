---
name: rem-public-material-generalization
description: >
  Publication rules for every public material — skills, docs, source code,
  commit messages, pull requests and release notes: why public content must be
  generalized, what keeps real names, how project-specific facts live in an
  ignored `local/` overlay, and the pre-push checklist that covers the whole
  outgoing history. Use when creating or publishing a skill, writing public
  docs or commit messages, or when a public library must not leak the project
  that consumes it.
metadata:
  category: meta
  trigger: manual
---

# Public-Material Generalization

This skill is the **single owner** of the generalization rules for the RemSkills
collection (per `rem-write-better-skill` §11, a rule lives in exactly one skill —
copies drift). It was extracted from `rem-write-better-skill` §3a/§6/§8.5, and
covers **every material that becomes public** — a skill, a README, a source file
and its comments, a commit message, a pull request or release note, a shipped
sample. Apply it before the material is pushed to a public repository.

Anything in the public `RemSkills` repo, in a public library, in its docs and in
its history is **visible to anyone, forever**. The rules below decide what public
material may say.

---

## 1. Why generalize

- **Public material is permanent and public.** Real project names, paths, and
  internal decisions leak private information: repository layout, module
  structure, unreleased features, tooling choices.
- **Machine paths are meaningless elsewhere.** A literal home or drive path
  means nothing to a reader on another machine, and it goes stale as projects
  move.
- **Real names rot.** Type/module/plugin names change as the codebase evolves; a
  skill, doc or comment that names them reads as wrong a year later.
- **A public library's history is public too.** Commit messages and the pull-request
  text around them are fetched, mirrored and quoted; a leak there cannot be
  recalled by editing a file.

## 2. Goals

- Public material carries **generic knowledge + generic workflow** only.
- Nothing public can be traced to a specific machine, project, or private
  decision.
- Project-specific facts live **outside** public material: in external configs
  (tool-parameterized skills) or in the owning skill's **local overlay** — a
  `local/` directory next to `SKILL.md`, git-ignored and created as symlinks into
  a private repository that tracks the values.
- The private value files carry a **machine-local note** so a reader knows they
  are never copied into a public repo, and the public repo's `**/local/` ignore
  pattern is never narrowed, so a stray `git add -A` cannot ship them.

## 3. Scope

### 3.1 What must be generalized (non-public content)

The fact types are the same whatever the artifact:

| Category | Example |
|---|---|
| Machine paths | `<engine-install-path>`, `<project-dir>` |
| Project / target / module / asset names | `<ProjectName>`, `<DepA>`, `<target>` |
| Build & test configuration | `<config>`, `StartsWith:<test-prefix>` |
| Project plugin inventory | **non-public by default** (ADR-001): real third-party names only when the plugin is verified public AND the mention adds reader value — the project's *use* of it is still project fact |
| Private decisions | disabled-plugins lists, dependency policy, dev-config choices |
| Private type / convention names | `Foo::Math::Modulo` → placeholder |

The same rules reach every material that ships, not only skill prose:

| Artifact | What leaks | What to write instead |
|---|---|---|
| Source code & comments | a real module / plugin / target / type / asset name; a pointer to a private issue or doc; a machine path in a comment, a default value or a debug string; a comment that names the internal project or a ticket only the project can see | the construct's shape and the invariant it upholds, with an engine or public-repo citation; a `<placeholder>` for a value the host project supplies |
| Docs / README | the consuming project's layout, inventory and decisions; a local log or tool name; an example taken from real data | the mechanism and the decision in generic terms; a synthetic example; `<placeholder>` paths and `<ProjectName>` |
| Commit messages | the consumer project or editor-target name; a local log / run file name; a machine or drive path; the private module or test-prefix inventory; an internal sweep or campaign name; a raw evidence block (action or case counts, per-module breakdowns, warning counts, exit codes) | the scope and the reason in generic terms — one bullet per change and at most one short verification line; the raw evidence stays in the run / CI record, and the message discipline itself is owned by `rem-commit-workflow` |
| Pull request & release text | the same identifiers as a commit message plus the surrounding narrative — a raw evidence block repeated in the PR body, a consumer-project reference, a local run / log file name | the scope and the decision in generic terms; the evidence stays in the run / CI record, which the PR links rather than restates |
| Shipped samples, configs, fixtures | a real value pasted into a template (host, account, test prefix, plugin list); a fixture captured from the project's data | placeholder-only values; a synthetic fixture; the real value in the owning skill's `local/` overlay |
| Published history | any of the above, already fetched and mirrored — editing a file no longer removes it | the scan runs **before push**; a leak that is already published is handled as below |

**History is public material.** The scan happens **before push**, because a push
is the point of no return: once someone has fetched the commits they cannot be
recalled. A leak that is already published is therefore fixed forward by default;
rewriting published history is a separate, explicit call with its own
instructions (`rem-rewrite-commit-history`), never a tidy-up appended to another
task.

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
skill's `local/` overlay; a `Rem` prefix is not evidence of ecosystem
membership. `tools/lint-skills.mjs` enforces the outcome: every Rem-family
identifier in a skill (`RemXxx` and the type-prefixed `URemXxx`/`ERemXxx`
forms) must be listed in `tools/public-names.json` with a public source.

Shipped files are **not** exempt: the leak and name checks scan a skill's
scripts, templates and configs exactly like its prose, and the repository-level
files (README, LICENSE, workflows, hooks, `tools/`) in the same pass, because a
file that ships ships to everyone. A shipped file is therefore placeholder-only
— a skill holds no machine or project data (`rem-ue-plugin-adapter`'s config
templates carry `<...>` placeholders for this reason). Two exemptions: the
git-ignored `local/` overlay is not scanned, because it ships nowhere, and
`tools/public-names.json` is not scanned, because it *is* the reference data
for the name check. **Exception**: a skill whose entire purpose is documenting a
specific public type's API uses the real type name.

### 3.3 Repository split

| Repo | Contents |
|---|---|
| `RemSkills` (public) | Generalized skills only — everything here obeys this skill; a skill may carry a git-ignored `local/` overlay directory, which ships nothing |
| `RemSkillsPrivate` (private, no public remote) | Local-only skills plus the tracked overlay values (`overlays/<public-skill>/<name>`) that the public skills link in as ignored `local/` symlinks; committed normally in the local repo; a private remote is allowed, a public one never |

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
- **Local overlay** (values, not rules) — `<skill>/local/` next to
  `SKILL.md`: git-ignored, created as symlinks into the private repository that
  tracks the values under `overlays/<skill>/`. The public body lists the file
  names it reads, so no mapping table is needed and the private side maintains
  no list; the file names are free-form, chosen for what they hold. The value
  files hold **no skill frontmatter** — pi loads any `.md` that carries it as a
  skill, which would restore the always-on description this pattern exists to
  avoid; adding a local adaptation therefore costs no always-on context. A file
  in `local/` takes precedence over `references/` and the generic rules, while
  `SKILL.md` stays the single source of the skill's instructions and the local
  files carry values or configuration only; a clone without the private
  repository has no `local/` and falls back to the generic rules. A project-specific **rulebook**
  (rules, not values) stays a skill instead: the split is public/private *and*
  rules/values. The pointer to the overlay is a **body** sentence, never a
  description line — a sentence every adapted skill repeats is duplicated
  always-on text (`rem-write-better-skill` §11).
- **Live project configs** — a snapshot of a live project config (e.g. the
  commit-convention JSON) is a value: it lives in the private overlay, and the
  public repo gets only the ignored `local/` symlink. Never a committed copy or
  a tracked symlink (a link's target path leaks the machine layout) and no
  skip-worktree tricks. Refresh by copying the source file over the tracked
  value in the private repository; document that procedure in the skill.
- **Commit messages** — a private term list cannot live in a public file, so the
  scan reads it from the owning skill's overlay: run
  `node tools/lint-commit-messages.mjs --repo <repo> --range <remote>/<branch>..HEAD`
  before pushing a public repository's branch. The checker combines generic
  machine-path shapes with every term in `local/forbidden-commit-terms.txt`, the
  overlay file this skill points at (default input; the private repository tracks
  it). Cite the checker here — never paste the term file or its contents into a
  public file.
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

The checklist is the contract — run it before pushing any public material:

- [ ] No machine paths — drive-letter paths, posix and macOS home paths (enforced by `tools/lint-skills.mjs`)
- [ ] The collection lint passes before pushing — `node tools/lint-skills.mjs`; the run obligation and the tool itself are owned by `rem-write-better-skill` §8
- [ ] Publishing was authorized as its own explicit instruction, never inferred from an approval of the edits (`rem-commit-workflow` — Publishing is a separate gate)
- [ ] No private project/plugin/module/target/type names — the lint fails on any Rem-family identifier (`RemXxx`, `URemXxx`) missing from `tools/public-names.json`; a name is added only with a public source
- [ ] Names verified **anonymously** (`git -c credential.helper= -c core.askPass= ls-remote --heads <repo>`) — an authenticated lookup resolves private repositories and proves nothing
- [ ] Catalogue citations name a public path or the case's shape, never a private file ("observed in `<private-file>`")
- [ ] Leak and name checks cover every non-binary file that ships — the skill's own files (`SKILL.md`, `references/**`, `tools/**`) and the repository-level files; only the allowlist and the git-ignored `local/**` are exempt
- [ ] Outgoing commit messages scanned before a public push — `node tools/lint-commit-messages.mjs --repo <repo> --range <remote>/<branch>..HEAD` reports nothing (private terms come from the skill's `local/forbidden-commit-terms.txt`)
- [ ] Shipped code, docs, configs, fixtures and PR/release text follow the same rules as skill files (placeholder-only)
- [ ] A published leak is fixed forward by default; rewriting published history is a separate, deliberate call (`rem-rewrite-commit-history`)
- [ ] No project plugin inventory; third-party names only if verified public AND the mention adds value
- [ ] Placeholders are meaningless (no domain hints) — see `rem-write-better-skill` §3
- [ ] Generic paths use `<placeholder>` syntax
- [ ] Project-specific facts live in the skill's `local/` overlay (when present) — git-ignored, linked from the private repository, and listed in the body; adding a local adaptation costs no always-on context
- [ ] No `local/` path is tracked by git (enforced by `tools/lint-skills.mjs`)
- [ ] Every file under `local/` is a symlink whose target resolves — never a committed copy
- [ ] Data directories (`references/`, `tools/`, `local/`) contain no `SKILL.md`
- [ ] No `.md` outside `SKILL.md` carries skill frontmatter (each one would be loaded as a skill and pay an always-on description)
- [ ] Tool-parameterized skills require an external config (`--config`), erroring when missing
- [ ] Real-name content verified public (org/repo lookup) and cited
- [ ] Live project configs are private-overlay values — no committed copy, no tracked symlink, no skip-worktree trick

## Cross-references

- `rem-write-better-skill` — placeholder-type style (§3), structure & checklist conventions
- `rem-commit-workflow` — commit-message body discipline (bullets, one verification line, no local identifiers)
- `rem-rewrite-commit-history` — reshaping un-pushed history; the separate call that published-history rewriting requires
- `rem-ue-plugin-adapter` — external-config pattern (per-plugin `local.json`, `--config`)
- `RemSkillsPrivate` — the private repository that tracks the overlay values each skill links into `local/`
- `tools/public-names.json` — the Rem-family name allowlist consumed by `tools/lint-skills.mjs`
- `tools/lint-commit-messages.mjs` — the outgoing-commit-message leak checker
- ADR-001 — project plugin inventory is non-public by default
