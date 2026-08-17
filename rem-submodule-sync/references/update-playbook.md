# Submodule Sync — Pitfall Catalogue

Consult this when a phase misbehaves. Every entry is a failure mode observed
in practice, with the diagnostic and the fix.

## Detection

### The submodule `.git` is a file, not a directory

Modern git checkouts a submodule with `.git` as a **file** containing
`gitdir: <path>`. A `[[ -d "$d/.git" ]]` probe reports every submodule as
"NOT INITIALIZED". Probe with `-e` (existence), or check
`git -C "$d" rev-parse --git-dir` succeeds.

### Default branch is not `main`

Resolve it per remote, never assume:

```
git symbolic-ref refs/remotes/<remote>/HEAD        # local resolution
git ls-remote --symref <remote> HEAD               # authoritative, hits network
```

Observed defaults: `5.x` (FlowGraph upstream), `dev` (UEGitPlugin — the
repo has no `main` at all), `master` (several). A submodule that is
"behind 0, ahead N" against the wrong branch tells you nothing.

### Dual remotes: fork vs upstream

A submodule often has `origin` = the user's fork and `upstream` = the
original author. The two answer different questions:

| Remote | `behind` against it means |
|---|---|
| `upstream` (author) | missing real upstream work — this is what "update to latest" means |
| `origin` (own fork) | the fork's own main moved; usually the user's own pushes, **not** an update to pull |

Report both, but only flag `upstream` divergence as "needs update" unless
the fork branch is a deliberate target.

### Stale tracking after upstream branch moves

`git status` can report `[behind N]` against a tracking branch that no
longer exists upstream (`upstream/ue-5.8 [gone]`). Re-run
`git fetch --all --prune` before trusting any number; `--prune` is what
drops the gone ref.

### behind/ahead orientation

`git rev-list --count HEAD..<branch>` = commits on `<branch>` missing from
HEAD (**behind**). `<branch>..HEAD` = commits on HEAD missing from the
branch (**ahead**). Getting the direction backwards flips the report — a
submodule that is ahead of upstream would read as "behind". Sanity-check one
submodule with `git log --oneline <remote>/<branch>..HEAD` when the numbers
look surprising.

## Update

### `--ff-only` refuses on a "clean" submodule

The branch diverged because the local branch tracks a stale ref (branch
renamed/moved upstream, or the submodule's local branch was recreated).
Re-fetch, re-check the script's numbers, then decide: rebase onto the
remote default (2c in SKILL.md), or update the tracking config with
`git branch --set-upstream-to`.

### Rebase skips already-applied commits — don't restore them

`warning: skipped previously applied commit <hash>` means upstream already
contains that change (often the same author's own upstream commit). Leaving
it skipped is correct; `--reapply-cherry-picks` would duplicate the change
and cause merge noise. Verify with `git log --oneline <remote>/<branch>..HEAD`
that the remaining tip commits are exactly the intended custom work.

### sed resolution leaves conflict markers

Fixing a conflict by `sed`-replacing only the changed line removes the
content but **not** the `<<<<<<<` / `=======` / `>>>>>>>` lines — the file
then stages clean (git sees it as resolved) and fails to compile with
garbage. After any resolution, grep `^<<<<<<<|^=======|^>>>>>>>` and require
zero hits before `git add`. Prefer the `edit` tool (exact block replace) over
sed for conflict blocks.

### Rebase vs merge tree equivalence

After rebasing a divergent branch, the resulting tree must equal the
pre-rebase tree given the same resolution choices:
`git diff <old-HEAD> HEAD` empty. If not, a resolution differed — check each
conflict again. (A skipped commit also removes its delta; that is expected
and shows up as an upstream-identical change, not a divergence.)

## Verification

### Unenabled plugins are invisible to a project build

A plugin not listed in `<ProjectName>.uproject` (or listed `Enabled: false`)
is not compiled; `Result: Succeeded` says nothing about it. Verify it by
temporarily enabling it (see below), or explicitly state it was not verified.

### Plugin ID = `.uplugin` file name

The plugin folder `Plugins/FlowGraph` ships `Flow.uplugin`; the `.uproject`
must list **`Flow`**, not `FlowGraph`. Wrong name → UBT aborts with
`Unable to find plugin 'FlowGraph' (referenced via <ProjectName>.uproject)`. When in
doubt, `ls <plugin-dir>/*.uplugin` is the source of truth.

### Duplicate plugin entries in the .uproject

The project may already list a plugin once with `Enabled: false`; adding an
`Enabled: true` entry creates a duplicate and the build fails with
`Plugin '<Name>' is listed multiple times in project file`. Dedupe by name
(merge, keep one entry) before building.

### Module output lands in the plugin's own Binaries

Project plugin module DLLs go to `<plugin-dir>/Binaries/Win64`
(`UnrealEditor-<Module>.dll`), not the engine's or the parent project's
`Binaries`. Module name = `*.Build.cs` file prefix — `FlowGraph`'s modules
are `Flow`, `FlowDebugger`, `FlowEditor`. Look in the plugin directory;
searching engine Binaries finds nothing.

### "Target is up to date" when you expected a rebuild

If the plugin was already compiled and nothing changed, UBT prints no
compile lines and the DLL timestamp is old. That is correct when the change
is gitlink-only. When you did change source, verify the DLL timestamp
updated — a stale timestamp means the plugin wasn't actually part of the
build (usually: not enabled).

### `-Plugin=<path>` does not force compilation

Passing `-Plugin=` to Build.bat for a plugin the target doesn't include
results in "Target is up to date" — it does not compile the plugin. Enable
the plugin in the `.uproject` instead.

## Commit

### Parent gitlink vs submodule state

`Mm Plugins/<X>` (uppercase M = staged gitlink) vs `m Plugins/<X>`
(lowercase = dirty submodule working tree). The parent commit records the
gitlink; the submodule's own commits are made inside the submodule first.
Amending the parent after a submodule-internal commit needs another
`git add <submodule-path>`.

### Never `git add -A` in the parent

The parent repo accumulates unrelated working-tree changes (`.gitignore`,
untracked content, ADR docs). Stage by exact path
(`git add Plugins/<X> <ProjectName>.uproject`); leave everything else alone.
