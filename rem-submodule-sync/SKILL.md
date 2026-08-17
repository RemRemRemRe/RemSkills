---
name: rem-submodule-sync
description: >
  Detect and update git submodules to their remote default-branch latest:
  enumerate submodules, fetch and report behind/ahead per remote, fast-forward
  clean ones, rebase local custom commits on top of upstream, resolve
  conflicts, verify by an incremental UE build, then commit. Use when asked to
  check which submodules lag their remote, update submodules, or sync plugin
  submodules to upstream latest. Project-specific values (paths, target,
  filter rule, commit conventions) live in the private companion skill
  `rem-submodule-sync-local`.
metadata:
  category: workflow
  trigger: manual
---

# Submodule Sync

Keep submodules at their remote default-branch latest. Four phases, each with
a checkable exit criterion. Run the detection script first; it drives phases
1 and 2.

Run order: **Detect → Update → Verify → Commit**. Do not skip Verify; do not
commit before Verify passed.

---

## 1. Detect

Run `references/check_submodules.sh --root <project-dir> [--exclude-prefix <prefix>]`.

The script enumerates `.gitmodules`, fetches all remotes, resolves each
remote's **default branch** (never assume `main`), and prints `behind/ahead`
for every submodule against every remote.

Interpretation:

| Reading | Meaning | Action |
|---|---|---|
| `behind=N, ahead=0` | submodule lags its upstream, no local commits | Update: fast-forward |
| `behind=N, ahead=M` (M>0) | submodule lags upstream AND carries local commits | Update: rebase, or skip if the divergence is intentional |
| `behind=0, ahead=M` | submodule is ahead of (or equal to) upstream | **Do not touch** — it has local-only work |
| `behind=0, ahead=0` | up to date | no action |
| `NOT INITIALIZED` | checkout missing | `git submodule update --init` if the parent needs it |

**Exit criterion:** every submodule has a `behind/ahead` number for its
default branch, and you can name which ones need action and why.

---

## 2. Update

Per submodule, in the order the script reported them.

### 2a. Check the working tree

`git status --short --branch` inside the submodule first:

- Clean tree → proceed.
- Dirty tree → inspect the diff before anything else. A small habitual edit
  (for example removing `EngineVersion` from a `.uplugin`) is often meant to
  be kept across the update — stash it and re-apply after, or fold it in (see
  2d).

### 2b. No local commits → fast-forward

```
git merge --ff-only <remote>/<default-branch>
```

If `--ff-only` refuses, the branch actually diverged — re-read the script's
numbers; the local branch may be tracking a stale remote. Re-run
`git fetch --all --prune` and re-check before forcing anything.

### 2c. Local commits exist → rebase, never merge

```
git rebase <remote>/<default-branch>
```

Rebase replays local custom commits **on top of** upstream, so the custom
work sits at the tip of the history — the reviewable surface is exactly the
local changes. A merge buries them behind a merge commit; do not merge.

- Commits upstream already contains are **skipped automatically** by rebase
  (`skipped previously applied commit`). Leave them skipped — restoring them
  duplicates upstream content.
- Resolve each conflict with `git add` then `git rebase --continue`
  (`GIT_EDITOR=true` to accept the default message).
- After rebase, verify the tree is identical to the pre-rebase state:
  `git diff <pre-rebase-commit> HEAD` must be empty for the same resolution
  choices (see 2d).

### 2d. Conflict resolution policy

| Case | Take |
|---|---|
| Upstream improved the line (new API, larger buffer, added `static`/`constexpr`) | upstream version |
| Local edit is a deliberate customization (removing `EngineVersion`, project-specific config) | local version, re-applied over the upstream change |
| Both sides changed the same line for the same purpose | upstream version |

Resolving "take upstream" for a whole file: `git checkout --theirs -- <file>`
during a rebase (upstream is `theirs`). For a whole file of local custom
work, `git checkout --ours -- <file>`.

After resolving, **delete all conflict markers** — grep for
`^<<<<<<<|^=======|^>>>>>>>` and confirm zero hits before `git add`. A sed
edit that replaces only the conflicting line leaves the markers behind and
the file then compiles with garbage; check, don't assume.

**Exit criterion:** each target submodule's tip is `behind=0` against its
default branch; local custom commits (if any) sit at the tip; no conflict
markers remain; working trees are clean.

---

## 3. Verify (build)

Unenabled plugins are **not compiled** by a project build — a successful
project build says nothing about them. Verify only the modules that changed:

| Submodule state | Verify with |
|---|---|
| plugin enabled in the project | project build |
| plugin not enabled | temporarily enable in `<ProjectName>.uproject`, build, then keep or restore per project policy |

Build command:

```
<engine-install-path>\Engine\Build\BatchFiles\Build.bat <target>Editor Win64 Development -Project="<project-dir>\<ProjectName>.uproject" -WaitMutex
```

- **Plugin ID = `.uplugin` file name.** A plugin folder named `<PluginName>`
  whose descriptor is `<Foo>.uplugin` must be listed as `Foo` in the
  `.uproject` — writing the folder name makes UBT report
  `Unable to find plugin`.
- A `.uproject` may already list a plugin twice (once disabled) — **dedupe
  before** enabling, or the build fails with `listed multiple times`.
- Module DLLs land in the **plugin's own** `Binaries/Win64` (never the
  engine's or the project's). Module name = `*.Build.cs` file prefix.
- Confirm real work happened: check the plugin's `Binaries/Win64` DLL
  timestamps match this build; an up-to-date target prints no compile lines.

**Exit criterion:** `Result: Succeeded` in the UBT output, and every changed
plugin's module DLL was rebuilt (timestamp check) or provably untouched by
the change.

---

## 4. Commit

1. Commit inside each submodule first (its own history), then update the
   parent's gitlink (`git add <submodule-path>` in the parent).
2. Commit the parent with one commit covering all gitlink updates.
3. Stage by exact path in the parent; never `git add -A` — unrelated working
   tree changes (`.gitignore`, untracked files) must stay uncommitted.
4. Message and build/test conventions belong to `rem-commit-workflow` — do
   not restate them here; follow that skill for message type, body style, and
   the test run. Submodule updates conventionally use `Changed: update
   submodules ...` with the touched plugins in the summary.
5. History reshaping (amend/fixup) belongs to `rem-rewrite-commit-history`.
6. Push is a separate workflow — see `rem-submodule-push` (three-axis audit,
   batch push, `--recurse-submodules=check` gate). Ask before pushing anything.

**Exit criterion:** parent commit contains only the intended gitlink updates
(plus any agreed `.uproject` change); submodule trees are clean; uncommitted
unrelated changes are untouched.

---

## Pitfall catalogue

Expanded failure modes, including the `.git`-is-a-file trap, default-branch
surprises, dual-remote semantics, and artifact locations, live in
`references/update-playbook.md`. Consult it when a step misbehaves.

## Checklist

- [ ] Detection script ran; every submodule has a behind/ahead number; action list stated
- [ ] Dirty submodules inspected before updating; habitual local edits preserved
- [ ] No-local-commits case used `--ff-only`; divergent case used rebase, not merge
- [ ] Conflict markers grepped to zero (`^<<<<<<<|^=======|^>>>>>>>`) before every `git add`
- [ ] Rebase case verified `git diff <pre-rebase> HEAD` is empty (same resolution)
- [ ] Unenabled plugins were verified by temporary enable + build, not assumed OK
- [ ] Plugin ID checked against `.uplugin` file name; duplicate `.uproject` entries deduped
- [ ] Rebuilt DLL timestamps confirmed per changed module
- [ ] `Result: Succeeded`
- [ ] Submodule commits made before parent gitlink; parent commit staged by exact path only
- [ ] Commit message follows `rem-commit-workflow`; push per `rem-submodule-push` (with the gitlink-sync axis checked)
