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

- [`rem-commit-workflow`](rem-commit-workflow/SKILL.md) — single-responsibility commits, pre-build test completeness gate, headless build & test
- [`rem-rewrite-commit-history`](rem-rewrite-commit-history/SKILL.md) — reshape un-pushed commit stacks (amend / fixup / rebase -i)
- [`rem-submodule-sync`](rem-submodule-sync/SKILL.md) — update submodules to remote latest, verify by build, commit
- [`rem-submodule-push`](rem-submodule-push/SKILL.md) — three-axis audit + batch push with `--recurse-submodules=check` as the gate

**C++ development conventions**

- [`rem-cpp-best-practices`](rem-cpp-best-practices/SKILL.md) — the C++ review checklist (build settings, file/include structure, naming, const, UPROPERTY, logging, test modules) plus the pre-commit checklist
- [`rem-ranges-transrangers`](rem-ranges-transrangers/SKILL.md) — functional pipeline code with `Rem::Ranges`, transrangers, `RemStd::bind_back`

**UE modules & editor extensions**

- [`rem-create-new-module`](rem-create-new-module/SKILL.md) — scaffold a new module or plugin from the RemMyBlank boilerplate
- [`rem-customize-factory-asset-menu`](rem-customize-factory-asset-menu/SKILL.md) — place a custom `UFactory` in specific Content Browser "Add" categories and sub-menus
- [`rem-sequencer-custom-channel-section`](rem-sequencer-custom-channel-section/SKILL.md) — custom `FMovieSceneChannel` / `UMovieSceneSection` with per-key struct editing

**Testing**

- [`rem-test-completeness`](rem-test-completeness/SKILL.md) — the pre-commit gate: change-to-case mapping, five-point completeness criteria, regression-first for fixes
- [`rem-bdd-test-tree`](rem-bdd-test-tree/SKILL.md) — hierarchical BDD test tree (mind-map index) + layered review workflow

**Multi-engine plugin adaptation**

- [`rem-ue-plugin-adapter`](rem-ue-plugin-adapter/SKILL.md) — adapt a UE plugin from upstream latest down to 5.3–5.8, with branch management and the build-fix-commit loop

**Skill meta**

- [`rem-write-better-skill`](rem-write-better-skill/SKILL.md) — writing conventions for this collection
- [`rem-public-skill-generalization`](rem-public-skill-generalization/SKILL.md) — publication rules: placeholders, private companion skills, pre-push checklist

**Environment constraints**

- [`rem-no-disk-scanning`](rem-no-disk-scanning/SKILL.md) — always loaded: no `rg` / `grep` / `fd`, all text search goes through Rider MCP

## Daily Reference Workflow

- **Start a session** — `rem-no-disk-scanning` is always loaded; all text search goes through Rider MCP
- **Write**
  - Write / review C++ — `rem-cpp-best-practices` (rules + §17 pre-commit checklist); `rem-ranges-transrangers` for pipeline code
  - Scaffold a module / plugin — `rem-create-new-module`
  - UE editor / asset work — `rem-customize-factory-asset-menu`, `rem-sequencer-custom-channel-section`
- **Test**
  - Make sure the tests are complete — `rem-test-completeness` (the gate); `rem-bdd-test-tree` (review index); spec templates & run gotchas in `rem-cpp-best-practices` `references/tests.md`
- **Commit & push**
  - Commit — `rem-commit-workflow` (message, hygiene, completeness gate, build, headless tests); project facts come from its `-local` companion skill
  - Clean history before push — `rem-rewrite-commit-history`
  - Sync / push submodules — `rem-submodule-sync`, `rem-submodule-push`
- **Extend & maintain**
  - Adapt to multiple engine versions — `rem-ue-plugin-adapter`
  - Write / publish a skill — `rem-write-better-skill`, `rem-public-skill-generalization`

## Installation

- Clone this repo (or copy the skill folders you need). Every skill is
  self-contained in its own folder.
- Point your agent at the collection. With [pi](https://github.com/earendil-works/pi):
  add the path to the `skills` array in your settings, or pass `--skill <path>`
  (repeatable). Any Agent Skills–compatible harness works.
- Project-local skills: place them under your project's `.agents/skills`
  (trusted on harness startup).
- Private companion skills (`*-local`) live in a separate private repository
  with no public remote — see the split below.

## Prerequisites

- An Agent Skills–compatible agent harness (pi recommended).
- **Rider MCP** — required by `rem-no-disk-scanning`: text search goes through
  Rider, never disk scanners.
- An Unreal Engine project with automation test support (`DEFINE_SPEC` BDD
  specs and a headless `-nullrhi` run path).

## Public / Private Split

Public skills carry generalized knowledge only — generic placeholders, no
project names, paths, or internal decisions. Project-specific facts live in
**private companion skills** (`*-local`) in a separate private repository
(never a public remote), or in external per-plugin configs. The rules are owned
by
[`rem-public-skill-generalization`](rem-public-skill-generalization/SKILL.md).

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
