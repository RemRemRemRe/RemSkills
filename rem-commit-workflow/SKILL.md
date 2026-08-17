---
name: rem-commit-workflow
description: >
  Commit local changes in a UE project and verify them — single-responsibility
  commits, English comments, reformat edited files, a pre-build test
  completeness gate, then build and run the project's automation tests
  headless. Use when committing plugin changes, splitting a mixed commit for
  review, running the project's test suite, or deciding whether commits may be
  published.
metadata:
  category: workflow
  trigger: manual
---

# Commit Workflow

## Commit message

Follow `Type: short desc` in English. The accepted types for this collection are:

| Type | Use for |
|---|---|
| `New` | new things |
| `Changed` | it changed |
| `Improvement` | better thing |
| `Removed` | it gets removed |
| `Fixed` | fixed a bug |
| `Misc` | typo, formatting, naming |

The per-project authoritative list lives in the project's commit-convention
config (the local overlay keeps a path-free snapshot: `rem-local` →
`references/CommitConventionHelper.json`).
Accept the types the project's config defines. Add a body when the change
spans several concerns or the "why" is non-obvious.

**Body readability (collection rule):** a body with multiple details lists
each change as **one bullet line** (`- <one change>`), never a long paragraph.
One line per change keeps the diff readable and the changelog clean — a
multi-sentence paragraph body is a review smell.

## Commit hygiene

- One logical change per commit. Split a mixed commit (rename + bug fix, class
  filter + module tidy) into one commit per reason-to-change. Intermediate
  commits do not need to compile — the split serves review and maintenance.
- Comments are English, never Chinese.
- **Unified format pass before committing.** Edited files are reformatted so the
  code matches the solution code style — use the Rider MCP `reformat_file` tool
  on every changed file (batched in one `mcpScript` loop). Hand-edited spacing
  is not a substitute; the build + test gates run on the reformatted code. After
  a reformat, re-check long `UPROPERTY` `meta` string literals
  (`rem-cpp-best-practices` §4).
- Stage by exact path; never `git add -A` in the project repository — leave
  unfinished work uncommitted. A **generated tree whose contents are all
  produced by tooling** (the plugin-adapter's build repo) is the stated
  exception, documented at its own commit step. After a broad `git add` or
  `git commit --amend`, verify the commit's file list (`git show --stat`)
  before finalizing — a stray working-tree change swept in by `-A`/amend is
  hard to untangle afterwards (hit in practice).
- **Feeding a commit message from a file**: write that file BOM-free.
  PowerShell's `Set-Content -Encoding utf8` prepends a UTF-8 BOM and
  `git commit -F` passes it through, so the subject silently starts with an
  invisible `\uFEFF` (hit in practice) — use `[System.IO.File]::WriteAllText($path,
  $text, [System.Text.UTF8Encoding]::new($false))`, or pass `-m` arguments.
- Reshaping the history of un-pushed commits (amend, fixup, squash, reorder,
  drop) belongs to `rem-rewrite-commit-history`.

## Test completeness gate

Before building, prove the change set's tests are complete. The methodology —
change-to-case mapping, the five-point criteria, regression-first for fixes —
is owned by `rem-test-completeness`; this section only states the gate rules.

- **Mandatory** for behavior-affecting changes (logic in `New` / `Changed` /
  `Fixed` / `Improvement` commits). Skip only with a stated reason: pure
  refactor with no semantic change, docs, formatting, naming, config-only.
- Applies to the **whole change set once**, not per split commit.
- Tests incomplete → write the missing cases per `rem-test-completeness`
  **before** building; the build and test run happen once, after tests are
  complete.
- Regression cases bind bug fixes; spot-check core logic by temporarily
  reverting the fix (the case must fail).

## Review gate

Before building and committing a change set, run the **review sub-agent**
(`review` type, or the project's review agent) on the changed files. It is a
mandatory step, not optional — the test gate proves behavior, the review gate
catches design defects, lifecycle hazards and vacuous tests that tests alone
miss (real case 2026-08: a registration-scope clobbering defect and a
source-lifecycle gap were only found by the review pass; the test suite was
green).

- Run it read-only over the diff/working tree before committing; fix the
  substantive findings, then re-run the build + tests.
- Findings are not all equal: treat medium-high severity (state-machine
  correctness, lifetime/dangling, provider lifecycle) as blocking for the
  commit; fold lower-severity style nits in the same pass or list them.
- Include the review findings (and which were fixed) in the commit body when
  they shaped the change, so the history documents the review.
- The review covers the **documentation obligation** too: a diff that adds or
  changes a subsystem, a public API, a config property or a designer-facing
  behavior must satisfy `rem-docs-and-config` §2 — a one-line default change
  still updates the config reference.

## Build

```
<engine-install-path>\Engine\Build\BatchFiles\Build.bat <target>Editor Win64 <config> -project="<project-dir>\<ProjectName>.uproject" -waitmutex
```

Use the project's editor development configuration — never build a different
editor config for this. Exact engine path, target, and config are project
facts: see the local overlay (`rem-local` → `references/rem-commit-workflow.md`).

## Run tests

```
<engine-install-path>\Engine\Binaries\Win64\UnrealEditor-Win64-<config>-Cmd.exe "<project-dir>\<ProjectName>.uproject" -unattended -nullrhi -ExecCmds="Automation RunTests StartsWith:<test-prefix>; Quit" -TestExit="Automation Test Queue Empty" -DisablePlugins=<nullrhi-crash-plugin> -log
```

- Disable plugins known to crash under `-nullrhi` (the project's list is in the
  local overlay — `rem-local` → `references/rem-commit-workflow.md`); the filter
  is `StartsWith:<test-prefix>`, not `*`.
- Scope the filter to the change when it is confined to one plugin/module: run
  `StartsWith:<module-prefix>` (e.g. the camera suite `StartsWith:Rem.Camera`)
  instead of the whole project prefix. Run the full project prefix only when the
  change touches shared/public code that other modules consume. The full build
  still compiles everything either way.
- The console prints only UBT platform validation — judge red/green from
  `<project-dir>/Saved/Logs/<ProjectName>.log` (search `Result={Fail}`; green
  ends with `**** TEST COMPLETE. EXIT CODE: 0 ****`).

## Publishing is a separate gate

`commit` and `push` are not two halves of one act. A commit is local and freely
rewritable; a push is public, and once fetched it cannot be taken back
(`rem-public-skill-generalization` §1 — public history is permanent, and
rewriting what is already published is a separate, deliberate call).

- **Never infer authorization to publish.** An approval of the work — "go
  ahead", "continue", a plan that happens to end with a push — covers the
  reversible half only. Ask for the push itself.
- **Never bundle** an irreversible act into the approval of a reversible one.
  The reply answers what was asked; a plan that quietly appends a push extends
  that answer past what was granted.
- **The irreversible acts**, each needing its own explicit instruction — whether it is
  local or remote makes no difference, only whether the act can be undone: **any push or
  upload** (`git push` to any remote, `push --force` / `--force-with-lease`, uploading a
  package, release or marketplace build, uploading assets or data to any service),
  deleting or renaming a branch (local or remote) or a tag, publishing a release or a
  package, rewriting published history, and destroying local recovery state (`git reflog
  expire`, `git gc --prune=now`, `filter-branch` / `filter-repo` cleanup, deleting the
  only reference to un-pushed work).
- **Irreversibility is the criterion, not the blast radius.** An act that removes the
  only copy of un-pushed work — or the record that could bring it back — is as
  irreversible as a push, and an upload is irreversible the moment it leaves the machine:
  a copy someone else has fetched, or a package someone else has installed, cannot be
  recalled. Run such an act only under its own explicit instruction, never as a tidy-up
  appended to another task; when a cleanup or an upload looks tempting but was not asked
  for, describe it and ask.
- **State what will be published before publishing it.** A branch's first push
  publishes its whole history, not only the commits just made: check
  `git ls-remote --heads origin` against `git log origin/<branch> --oneline`
  (`-1`, `| wc -l`) and name the count.
- **When the scope grows, re-ask.** Five commits becoming fifteen does not carry
  the original approval along with it.

## Checklist

Before committing:

- [ ] Message follows `Type: short desc` with a type from the project's config
- [ ] Body lists each change as one bullet line — no multi-sentence paragraphs
- [ ] One logical change per commit; a mixed commit was split per reason-to-change
- [ ] Comments in the diff are English
- [ ] Every edited file went through the Rider MCP `reformat_file` pass
- [ ] Long `UPROPERTY` `meta`/`EditCondition` literals survived the reformat intact
- [ ] Staged by exact path (no `git add -A`); `git show --stat` verified the file list after any amend; a message fed via `-F` was BOM-free
- [ ] Un-pushed history folded per `rem-rewrite-commit-history`, not left as follow-up noise
- [ ] Each module's dependencies declared per `rem-cpp-best-practices` §15
- [ ] Test-completeness gate run for behavior-affecting changes, or skipped with a stated reason
- [ ] Review sub-agent run over the diff; blocking findings fixed and re-verified
- [ ] Docs/config obligations applied per `rem-docs-and-config` §2 (new subsystem, public API, config property, designer-facing behavior)
- [ ] Build succeeded with the project's editor development configuration
- [ ] Headless tests run with the project's filter; red/green judged from the project log, not the console output
- [ ] Every irreversible act carries its own explicit instruction — push **or upload**, force-push, deleting a branch/tag, pruning (`reflog expire` / `gc --prune`), publishing — never inferred from an approval of the commit work
- [ ] Before a branch's first push: what else becomes public was stated (a first push publishes the whole history)

## Cross-references

- `rem-test-completeness` — the test completeness gate methodology and criteria
- `rem-rewrite-commit-history` — reshaping un-pushed commit stacks before push
- `rem-cpp-best-practices` §16 — spec style, test module placement
- `rem-cpp-best-practices` §15 — module/plugin dependency declaration
- `rem-bdd-test-tree` — layered review of the test suite
- `rem-docs-and-config` — which documentation/config artifacts a change must update

