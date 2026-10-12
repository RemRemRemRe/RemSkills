---
name: rem-commit-workflow
description: >
  Commit local changes in a UE project and verify them — single-responsibility
  commits, English comments, formatting verified, a pre-build test
  completeness check, then build and run the project's automation tests
  headless. Use when committing plugin changes, splitting a mixed commit for
  review, running the project's test suite, or deciding whether commits may be
  published.
metadata:
  category: workflow
  trigger: manual
---

# Commit Workflow

## Local overlay

`local/` holds machine-local values - git-ignored symlinks into a private repository that tracks
them, never committed here; they win over `references/` and the rules below, and carry values only
(the model is owned by `rem-public-material-generalization`). Files read when present:

- `local/build-test-and-commit.md` - build/headless-test commands, commit-convention snapshot, project inventory and sweep notes
- `local/CommitConventionHelper.json` - commit-type config snapshot

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
config (the local overlay keeps a snapshot of it).
Accept the types the project's config defines. Add a body when the change
spans several concerns or the "why" is non-obvious.

Separate the subject and body with a blank line — without one `git log --oneline`
merges the two lines; after rewording an un-pushed HEAD, confirm `^{tree}` is unchanged.

Generated release notes read only the commit **subject** (`%s`, not `%b`), and an
annotated tag's own message suppresses them — use a lightweight tag to get them.

**Body discipline (collection rule):** a body carries the *why* and the
contracts; the diff carries the *how*.

- One bullet per change (`- <one change>`), never a long paragraph — one line
  per change keeps the history readable and the changelog clean.
- A bullet states the final contract, invariant, measured constraint or
  non-obvious reason. It never narrates diff mechanics ("renamed X", "added the
  include", "moved Y") that the diff already shows.
- **Verification is one short closing line at most**, and only for a
  behaviour-affecting commit: `- Verified: editor DebugGame build and the full
  automation suite are green.` No raw action/case counts, log or run file
  names, per-module breakdowns, warning counts, exit codes or "on this exact
  tree" — the check's raw evidence lives in the run directory; the message says
  only what was verified.
- **No local identifiers**: no consumer-project or editor-target names, no
  machine or drive paths, no private module/test-prefix inventory, no internal
  sweep or campaign names. Describe scope generically. The leak rules are owned
  by `rem-public-material-generalization`.
- Keep it proportional: a body that needs more than a handful of bullets is
  usually restating the diff or a document — that detail belongs in the code
  comment, the reference doc or the pull request; the body keeps the decisions.

## Commit hygiene

- One logical change per commit. Split a mixed commit (rename + bug fix, class
  filter + module tidy) into one commit per reason-to-change. Intermediate
  commits do not need to compile — but order the split so every intermediate
  staged tree still passes the repository's own checks (lint/size budget), not
- **A cross-repository change is one unit.** When one repository removes an API
  and other repositories migrate its call sites, the halves commit **together**,
  and whatever pins the versions (a submodule pointer, a lock file) moves in the
  same batch — staged by exact path so unrelated dirty entries stay out.
- **A file the change set commits carries its pre-existing defects into that
  set.** A defect found inside a file already being committed belongs to the
  change under review — fix it under the same check, or record it explicitly. It
  is not "pre-existing" to a reviewer reading the commit.
- Comments are English, never Chinese.
- **Formatting belongs to the coding round; the commit only verifies it.** That
  round runs the project formatter (Rider MCP `reformat_file`, batched in one
  `mcpScript` loop) on every touched file and compiles *after* it, so the verified
  bytes are the formatted bytes. The commit stage never reformats: doing it here
  invalidates the verified tree, and another tool or version can change more than
  the diff suggests. An unformatted file stops the commit and returns the work to
  authoring; the mid-string split of a long `UPROPERTY` `meta` literal is caught
  here (`rem-cpp-best-practices` §4).
- Stage by exact path; never `git add -A` in the project repository — leave
  unfinished work uncommitted. A **generated tree whose contents are all
  produced by tooling** (the plugin-adapter's build repo) is the stated
  exception, documented at its own commit step. After a broad `git add` or
  `git commit --amend`, verify the commit's file list (`git show --stat`)
  before finalizing — a stray working-tree change swept in by `-A`/amend is
  hard to untangle afterwards (hit in practice).
- **`.gitignore` patterns match at any depth unless anchored.** `NAME` ignores a
  same-named file in every directory (case-insensitively on Windows); write `/NAME` for
  a root-only entry. `git check-ignore` skips already-tracked paths — add `--no-index`
  to ask about them.
- **Force and verify the executable bit for committed scripts.** On a host with
  `core.fileMode=false` (Windows), `git add` records mode `100644`, so a Linux/macOS
  consumer cannot `./<script>`; a `rm --cached` + re-add rebuild silently drops `100755`
  too. Set it explicitly (`git add --chmod=+x <path>`, or plumbing `--cacheinfo 100755`)
  and check `git ls-tree`; only `git diff --summary` shows the mode change.
- **Feeding a commit message from a file**: write that file BOM-free.
  PowerShell's `Set-Content -Encoding utf8` prepends a UTF-8 BOM and
  `git commit -F` passes it through, so the subject silently starts with an
  invisible `\uFEFF` (hit in practice) — use `[System.IO.File]::WriteAllText($path,
  $text, [System.Text.UTF8Encoding]::new($false))`, or pass `-m` arguments.
- Reshaping the history of un-pushed commits (amend, fixup, squash, reorder,
  drop) belongs to `rem-rewrite-commit-history`.

### Staging part of a file (mixed ownership)

When one file holds both this change and someone else's in-progress work, stage **hunks, not the
file**:

1. Build a patch that contains only this change's hunks and apply it to the index:
   `git apply --cached <patch>` (the porcelain equivalent is the interactive `git add -p`).
2. Verify all three before committing:
   - the staged content contains **zero** occurrences of a token unique to the other work
     (`git diff --cached` searched for that token);
   - the other work is still in the working tree and **unstaged** (`git diff` still shows it;
     `git status --short` still reports the file modified);
   - when the file is a gitlink, the staged gitlink equals the submodule's HEAD.
3. **Stop condition.** If the two changes interleave in the same region and no subset of hunks yields
   a compilable intermediate state, **commit them as one** and state the proof in the commit body
   ("cannot be split without a non-compilable intermediate state: <why>") instead of forcing a split.

A plumbing path such as `git apply --cached` bypasses the index's filters, so on a host that
normalizes line endings also check the staged blob's line endings (the porcelain path handles them;
the host-specific detail is in the `local/` overlay).

To stage a constructed blob **without writing the working tree** (a concurrent writer owns the
file), use `git hash-object -w --path=<path>` (applies the clean filter, stores LF) plus
`git update-index --cacheinfo`; verify the staged blob has zero CR and the worktree hash is
unchanged. (The `git apply --cached` recipe above writes a temporary file.)

## Test completeness check

Before building, prove the change set's tests are complete. The methodology —
change-to-case mapping, the five-point criteria, regression-first for fixes —
is owned by `rem-test-completeness`; this section only states the check rules.

**Iteration vs. the full check.** The sequence is owned by `rem-orchestration`; this check
runs **once, in the full check**, on the accumulated change set, before the
single build + suite run.

- **Mandatory** for behavior-affecting changes (logic in `New` / `Changed` /
  `Fixed` / `Improvement` commits). Skip only with a stated reason: pure
  refactor with no semantic change, docs, formatting, naming, config-only. A
  deferred behaviour is not skipped silently - it goes on the debt ledger and is
  paid before the push (`rem-test-completeness` §4).
- Applies to the **whole change set once**, not per split commit.
- Tests incomplete → write the missing cases per `rem-test-completeness`
  **before** building; the build and test run happen once, after tests are
  complete.
- Regression cases bind bug fixes; spot-check core logic by temporarily
  reverting the fix (the case must fail).

## Review check

Before building and committing a change set, run the **review sub-agent**
(`review` type, or the project's review agent) on the changed files. It is a
mandatory step, not optional — the test check proves behavior, the review check
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
facts: see the Local overlay section (`local/build-test-and-commit.md`).

## Test scope

Scope is a two-stage decision, and both stages leave evidence: **enumerate candidates from the
module graph, then prune by symbol**. The procedure - the `tools/scope.py` invocations, the pruning
rules, the behaviour exemptions and the load-time argument - lives in `references/test-scope.md`;
read it when the scope is decided and record its evidence next to the run.

**Exit criterion:** candidates enumerated from the module graph, every dropped candidate carrying its
one-line reason, and the prefixes that cannot reach the change recorded; a change that cannot alter
behaviour needs no test run, with that reasoning stated rather than implied.
## Run tests

```
<engine-install-path>\Engine\Binaries\Win64\UnrealEditor-Win64-<config>-Cmd.exe "<project-dir>\<ProjectName>.uproject" -unattended -nullrhi -ExecCmds="Automation RunTests StartsWith:<test-prefix>; Quit" -TestExit="Automation Test Queue Empty" -DisablePlugins=<nullrhi-crash-plugin> -log
```

- Disable plugins known to crash under `-nullrhi` (the project's list is in the
  Local overlay section, `local/build-test-and-commit.md`); the filter
  is `StartsWith:<test-prefix>`, not `*`.
- **Scope is decided first** (`Test scope` above); this command only runs it.
- **Pick one scope up front and run it once for the evidence.** Narrower filters are for
  iteration only; the pre-commit check is a single run at the authorized scope — never stack
  scopes (narrow, then module, then full).
- The console prints only UBT platform validation — judge red/green from
  `<project-dir>/Saved/Logs/<ProjectName>.log` (search `Result={Fail}`; green
  ends with `**** TEST COMPLETE. EXIT CODE: 0 ****`).

## Publishing is its own step

`commit` and `push` are not two halves of one act. A commit is local and freely
rewritable; a push is public, and once fetched it cannot be taken back
(`rem-public-material-generalization` §1 — public history is permanent, and
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
- **Never delete and re-push a release tag** to retrigger a failed workflow — re-run the
  failed CI run from the Actions page instead.
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
- [ ] Body carries decisions, not evidence dumps — at most one short verification line, no local identifiers
- [ ] One logical change per commit; a mixed commit was split per reason-to-change
- [ ] Comments in the diff are English
- [ ] Formatting came from the coding round; the commit verified it and did not reformat (that would invalidate the verified tree)
- [ ] Long `UPROPERTY` `meta`/`EditCondition` literals are intact after the coding round's reformat (no mid-string split)
- [ ] Staged by exact path (no `git add -A`); `git show --stat` verified the file list after any amend; a message fed via `-F` was BOM-free
- [ ] A file shared with another's work was staged hunk-wise: the other work stayed unstaged, the staged content carried none of its tokens, and the gitlink matched the submodule HEAD — or the split was merged with the non-compilable-intermediate proof stated
- [ ] Un-pushed history folded per `rem-rewrite-commit-history`, not left as follow-up noise
- [ ] Each module's dependencies declared per `rem-cpp-best-practices` §15
- [ ] Test-completeness check run for behavior-affecting changes, or the skip is stated and recorded in `test-debt.md` (paid before the push)
- [ ] Review sub-agent run over the diff; blocking findings fixed and re-verified
- [ ] Docs/config obligations applied per `rem-docs-and-config` §2 (new subsystem, public API, config property, designer-facing behavior)
- [ ] Build succeeded with the project's editor development configuration (or the change was comment/doc-only with no compiled token, per `Test scope`)
- [ ] Test scope: candidates enumerated from the module graph (`tools/scope.py`), pruned by a search of the changed names, every dropped candidate given a reason
- [ ] Headless tests run with the project's filter at that scope; red/green judged from the project log, not the console output
- [ ] Every irreversible act carries its own explicit instruction — push **or upload**, force-push, deleting a branch/tag, pruning (`reflog expire` / `gc --prune`), publishing — never inferred from an approval of the commit work
- [ ] Before a branch's first push: what else becomes public was stated (a first push publishes the whole history)

## Cross-references

- `rem-test-completeness` — the test completeness check methodology and criteria
- `rem-rewrite-commit-history` — reshaping un-pushed commit stacks before push
- `rem-cpp-best-practices` §16 — spec style, test module placement
- `rem-cpp-best-practices` §15 — module/plugin dependency declaration
- `rem-bdd-test-tree` — layered review of the test suite
- `rem-docs-and-config` — which documentation/config artifacts a change must update

