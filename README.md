# RemSkills

AI skills for developing Rem modules — an [Agent Skills](https://agentskills.io/specification)-format
collection that guides an AI coding agent through Unreal Engine plugin development:
C++ conventions, testing, commit workflow, submodule maintenance, and multi-engine
adaptation. Each skill is a folder with a `SKILL.md` entry point and loads on demand.

> **中文版**: [README.zh-CN.md](README.zh-CN.md)

Both language versions are maintained in lockstep — the one-liners mirror each
skill's own `SKILL.md` description. When a skill's description changes, update
both files in the same change.

## What's Inside

**Commit & Git workflows**

- [`rem-commit-workflow`](rem-commit-workflow/SKILL.md) — Commit local changes in a UE project: single-responsibility commits, formatted and reviewed, then one build. Use when committing or splitting a mixed commit.
- [`rem-rewrite-commit-history`](rem-rewrite-commit-history/SKILL.md) — Fold un-pushed WIP into single-purpose commits with amend, fixup + autosquash or rebase -i. Use when reshaping a local branch before push.
- [`rem-submodule-sync`](rem-submodule-sync/SKILL.md) — Fast-forward or rebase git submodules onto their remote default branch, verify by build, commit. Use when submodules lag or a plugin submodule needs syncing.
- [`rem-submodule-push`](rem-submodule-push/SKILL.md) — Push a parent repo and its submodules safely: three-axis audit, explicit origin refs, `--recurse-submodules=check`. Use when pushing a project with submodules.

**C++ development conventions**

- [`rem-cpp-best-practices`](rem-cpp-best-practices/SKILL.md) — C++ review checklist for module code: includes, naming, const, UPROPERTY metadata, logging, tests. Use when reviewing a pre-commit diff or writing module code.
- [`rem-observability-and-profiling`](rem-observability-and-profiling/SKILL.md) — Logging, toggle-gated debug drawing, console and cvar hooks, profiling tags. Use when writing or reviewing code that must be observable at runtime.
- [`rem-docs-and-config`](rem-docs-and-config/SKILL.md) — Document what a change adds: technical docs, config references, tooltips. Use when adding a subsystem, public API, config property or designer-facing behavior.
- [`rem-ranges-transrangers`](rem-ranges-transrangers/SKILL.md) — Functional pipeline code with Rem::Ranges, transrangers and RemStd::bind_back. Use whenever you write or read filter/transform/group pipelines.

**UE modules & editor extensions**

- [`rem-create-new-module`](rem-create-new-module/SKILL.md) — Copy the RemMyBlank template to scaffold a module or plugin by keyword substitution. Use when adding a module or starting a plugin. Last verified: 2026-07.
- [`rem-customize-factory-asset-menu`](rem-customize-factory-asset-menu/SKILL.md) — Place a custom UFactory in a Content Browser Add/New Asset category or sub-menu. Use when a factory misses its menu or GetAssetMenuPathsForCategory is ignored.
- [`rem-sequencer-custom-channel-section`](rem-sequencer-custom-channel-section/SKILL.md) — Add a custom FMovieSceneChannel and UMovieSceneSection with per-key struct editing in Sequencer. Use when keys hold struct data that must be editable per key.
- [`rem-ue-localization`](rem-ue-localization/SKILL.md) — UE localization: localization targets, namespace+key lookups for editor text, gather/translate/compile. Use when adding a language or text stays untranslated.

**Testing**

- [`rem-test-completeness`](rem-test-completeness/SKILL.md) — Judge whether a change's automation tests are complete: change-to-case mapping, five criteria, regression-first for fixes. Use when writing the missing tests.
- [`rem-bdd-test-tree`](rem-bdd-test-tree/SKILL.md) — Build a hierarchical mind-map index of UE automation spec files (DEFINE_SPEC / Describe / It). Use when reviewing a large suite or asking for a test tree.

**Multi-engine plugin adaptation**

- [`rem-ue-plugin-adapter`](rem-ue-plugin-adapter/SKILL.md) — Adapt a UE plugin from upstream latest down to engine 5.3-5.8: branches, embedded dependencies, build-fix-commit loop. Use when running cross-version builds.

**Skill meta**

- [`rem-write-better-skill`](rem-write-better-skill/SKILL.md) — Skill writing conventions: frontmatter, file structure, placeholders, examples, checklist. Use when creating or updating a skill in this collection.
- [`rem-public-material-generalization`](rem-public-material-generalization/SKILL.md) — Publication rules for public material: placeholders, the local/ overlay, the pre-push leak checklist. Use when writing a public doc, commit message or skill.
- [`rem-session-knowledge-distillation`](rem-session-knowledge-distillation/SKILL.md) — Distill a session's reusable lessons into a new doc or an amendment to an existing doc, process or skill. Use when a session ends or at a milestone.

**Main-session orchestration**

- [`rem-orchestration`](rem-orchestration/SKILL.md) — Delegate to subagents, run the iteration / freeze / push-gate cadence, cut each round's slowest step. Use when sequencing work as the main session.
- [`rem-shared-resources`](rem-shared-resources/SKILL.md) — Coordinate agent sessions in one project: claim files, lease build, test, git and IDE resources, keep per-session logs. Use when two sessions share a project.

**Environment constraints**

- [`rem-no-disk-scanning`](rem-no-disk-scanning/SKILL.md) — always loaded: Disk text search (rg, grep, find, ripgrep, findstr) is banned; search goes through the project's MCP server (Rider MCP). Use whenever you search files.
- [`rem-temp-files`](rem-temp-files/SKILL.md) — always loaded: Route scratch to the OS temp dir, not the working tree; only what a later reader needs persists in the run directory. Use whenever a session writes temp files.

## Daily Reference Workflow

- **Start a session** — `rem-no-disk-scanning` and `rem-temp-files` are always loaded; all text search goes through Rider MCP
- **Write**
  - Write / review C++ — `rem-cpp-best-practices` (rules + §17 pre-commit checklist); `rem-ranges-transrangers` for pipeline code
  - Instrument and profile — `rem-observability-and-profiling` (logs, debug draw, hooks, tags)
  - Document and expose config — `rem-docs-and-config` (technical docs, config references, tooltips)
  - Scaffold a module / plugin — `rem-create-new-module`
  - UE editor / asset work — `rem-customize-factory-asset-menu`, `rem-sequencer-custom-channel-section`
  - Ship editor text in another language — `rem-ue-localization`
- **Test**
  - Make sure the tests are complete — `rem-test-completeness` (the completeness check); `rem-bdd-test-tree` (review index); spec templates & run gotchas in `rem-cpp-best-practices/references/tests.md`
- **Commit & push**
  - Commit — `rem-commit-workflow` (message, hygiene, review, build); the suite runs at the push gate; project facts come from its `local/` overlay
  - Clean history before push — `rem-rewrite-commit-history`
  - Sync / push submodules — `rem-submodule-sync`, `rem-submodule-push`
- **Extend & maintain**
  - Adapt to multiple engine versions — `rem-ue-plugin-adapter`
  - Write / publish a skill — `rem-write-better-skill`, `rem-public-material-generalization`
  - Distill session knowledge — `rem-session-knowledge-distillation`

## Installation

- Clone this repo (or copy the skill folders you need). Every skill is
  self-contained in its own folder.
- Point your agent at the collection. With [pi](https://github.com/earendil-works/pi):
  add the path to the `skills` array in your settings, or pass `--skill <path>`
  (repeatable). Any Agent Skills–compatible harness works.
- Project-local skills: place them under your project's `.agents/skills`
  (trusted on harness startup).
- Machine-local values live in each skill's git-ignored `local/` overlay,
  linked in from a separate private repository with no public remote — see the
  split below.

## Prerequisites

- An Agent Skills–compatible agent harness (pi recommended).
- **Rider MCP** — required by `rem-no-disk-scanning`: text search goes through
  Rider, never disk scanners.
- An Unreal Engine project with automation test support (`DEFINE_SPEC` BDD
  specs and a headless `-nullrhi` run path).

## Public / Private Split

Public skills carry only rules — generic placeholders, no project names, paths,
or internal decisions. Machine-local values live in each skill's git-ignored
`local/` overlay: created as symlinks into a private repository that tracks
them, never committed here. `RemSkillsPrivate` keeps local-only skills and the
tracked overlay values; tool-parameterized skills keep their values in external
per-plugin configs. The rules are owned by
[`rem-public-material-generalization`](rem-public-material-generalization/SKILL.md).

## Skill lint

```bash
node tools/lint-skills.mjs
```

Zero-dependency check of the collection conventions: frontmatter shape and
allowed values, `name` matching the folder, a description that states when to
trigger and stays within 160 characters (3,500 for the collection — it is in
context on every request), a closing checklist, the size budget (32 KB warn /
48 KB fail, checklist excluded), leak patterns (drive-letter and home paths), and
the Rem-family name allowlist in [`tools/public-names.json`](tools/public-names.json).

Leak and name checks read **every non-binary file that ships** — each skill's
own files (`SKILL.md`, `references/**`, the scripts and templates under
`tools/`) and the repository-level files (README, LICENSE, workflows, hooks,
`tools/`) — so detail moved into a reference file, or into a shipped script,
stays covered. Only the allowlist is exempt: a file that ships, ships to
everyone. The git-ignored `local/` overlay ships nowhere and is not scanned;
the lint keeps it that way — no tracked `local/` path, every file under
`local/` a symlink whose target resolves, and no `SKILL.md` outside a top-level
skill folder. An unknown `Rem*`/`URem*` name fails the run; give it a publicly
verifiable source in the allowlist or generalize it.

It is a **local check**, not a CI job — it must pass before a change
leaves the machine, not after. Install the hook once per clone:

```bash
git config core.hooksPath .githooks
```

## Project Notes

- [`orchestration-policy.md`](orchestration-policy.md) — the project's always-on
  hard rules for the main session (scanning ban, delegation defaults, code-only
  iteration, cutting the round's slowest step, event-driven waiting); the procedure behind them is the
  `rem-orchestration` skill. It is the source of the project-root `AGENTS.md`
  symlink, so a harness pointed at that symlink loads exactly this file. Like the
  root READMEs, it is repository documentation, not a skill.

## Star History

<a href="https://star-history.com/#RemRemRemRe/RemSkills&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=RemRemRemRe/RemSkills&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=RemRemRemRe/RemSkills&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=RemRemRemRe/RemSkills&type=Date" />
 </picture>
</a>

## License

[MIT](LICENSE)
