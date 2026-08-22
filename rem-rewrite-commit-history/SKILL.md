---
name: rem-rewrite-commit-history
description: >
  Rewrite the history of un-pushed commits before it reaches collaborators:
  fold iterative local work into coherent single-purpose commits (amend,
  fixup + autosquash, rebase -i reword/reorder/squash/drop), so the pushed
  history — and the changelog it feeds — stays clean. Use when a local branch
  accumulated WIP, backtracking, or experiment commits that have not been
  pushed, or when a commit series should be reshaped before push. Never for
  pushed or shared history.
metadata:
  category: workflow
  trigger: manual
---

# Rewrite Un-Pushed Commit History

## Why

Local commits are an **iterative scratchpad**: intermediate states, direction
changes, and experiments accumulate naturally while working. What gets pushed
is the **curated, collaborator-facing final artifact**. Commit messages also
feed automated changelog / release-note generation (see `rem-commit-workflow`
§Commit message) — noise in history is noise in the changelog. Rewriting
**before push** removes that noise at zero cost to anyone else.

## Goals

- Pushed history reads as **one deliberate change per commit** (see
  `rem-commit-workflow` — one logical change per commit).
- Every final message matches the commit convention and describes the final
  state, not the path taken.
- No WIP, no fixup noise, no dead-end experiments in the pushed history.

## Safety contract

- **Only rewrite commits that have not been pushed.** Check the range first:
  `git log <remote>/<branch>..HEAD`.
- **Never rewrite** pushed or shared history, tagged/released commits, or
  commits referenced anywhere else.
- **No force-push.** If a remote branch must be corrected and you are the only
  author, prefer a corrective commit or a new branch; `force-with-lease` only
  as a last resort and never on shared branches.
- **The reflog is the safety net**: `git reflog` recovers anything for ~90
  days. `git rebase --abort` bails out of a messy interactive session.

## Operations

| Goal | Command |
|---|---|
| Fold staged changes into the last commit (keep message) | `git commit --amend --no-edit` |
| Amend message or author | `git commit --amend` |
| Fold a follow-up commit into its target | `git commit --fixup=<target>` then `git rebase -i --autosquash` |
| Interactive reshape: reword / reorder / squash / drop / split | `git rebase -i <base>` |
| Edit a commit mid-stack (split, partial rework) | `git rebase -i <base>` → mark `edit` → `git reset HEAD^` → re-commit the parts |
| Rebuild the stack from a point | `git reset --soft <base>` → re-commit one logical change at a time |
| Complex reshape (split + merge + redistribute many commits) | rebuild onto the upstream base with `cherry-pick -n` + file checkout — see §Workflow |
| Strip paths (docs, scripts, sensitive files) from the range | drop pure-path commits; in mixed commits `cherry-pick -n` + `git rm --cached <path>` — see §Workflow |
| Fold a correction across several target commits | split by file ownership, rebuild with `cherry-pick -n` + per-target `git apply --reject`, verify per commit — see §Workflow (mid-stack folding) |

A local commit that is not pushed is **amended to fold in the final state**
(e.g. a comment-language fix) instead of leaving a follow-up "fix" commit —
this is the collection's rule, owned here.

## Workflow

1. **Inspect** — `git log <remote>/<branch>..HEAD`: list the un-pushed commits,
   their messages, and what each actually changed. If the branch has no upstream
   set, compare against the remote-tracking ref directly (`git log
   origin/main..HEAD` — the tracking ref exists even when `@{u}` is unset); a
   zero-count range means there is nothing to rewrite.
2. **Plan** — group the changes by final logical change (one per commit); decide
   per commit: keep / reword / squash / drop / reorder. Map every file a
   follow-up/hygiene commit touches to the earlier commit that **owns** it (a
   stability fix to a file added in commit X folds into X, not into a lumped
   cleanup commit). Apply the **net-zero principle**: if a follow-up removes
   something an earlier commit added (e.g. a dependency added then dropped),
   skip introducing it in the first place — the final history shows only the
   net state. A follow-up that touches **production code** (not just
   test/hygiene files) is a production change — keep it as its own
   `Fixed:`/`Improvement:` commit even when it sits inside a test-work stack
   (e.g. a misspelled include fixed in a source file).
3. **Execute** — `git rebase -i <base>` (or `--autosquash` with `fixup!`
   commits); resolve conflicts like any rebase. For complex surgery (splitting
   a commit, merging two, redistributing a cleanup commit's files across many
   targets), rebuilding onto the upstream base is more controllable: `git
   switch -c rewrite <remote>/<branch>`, recreate each target commit with `git
   cherry-pick -n <source>`, prune or supply a file's exact state with `git
   checkout <commit> -- <path>` (also the clean way to resolve a hunk
   conflict: take a known-good version), then commit with the final message.
   To **strip paths** (docs, scripts, sensitive files): drop commits that touch
   only those paths; for an add-then-remove pair inside the range, drop both —
   the path never enters the history. In mixed commits, `git cherry-pick -n`
   then `git rm --cached <path>` **and remove the worktree copy** — an
   untracked leftover blocks a later branch switch to a tree that tracks it
   (hit twice in practice). Keep stripped files locally by extracting them from
   the old tip (`git show <old-tip>:<path>`) before finalizing — they end up
   untracked on disk.
   Rebuild on a **disposable branch** from the base: the original branch stays
   untouched until the tree-identity check passes, so any failed attempt is
   recovered by simply deleting the branch. Reuse the same rebuild recipe
   across the repos of a batch; when scripting it, do not use `:` as a field
   delimiter — commit messages contain colons (`Type: desc`) — and note that
   `cherry-pick` takes no `-q` flag. When the finalize involves `reset --hard`,
   preserve uncommitted changes as a patch file (`git diff > <patch>`) rather
   than a stash — a stash popped by a half-failed command chain gets silently
   wiped by the later reset.
   **Mid-stack folding — fold one correction across several target commits.**
   A review/correction commit often touches files owned by *different* earlier
   commits (code parts belong to feature commits, test parts to the test-module
   commit). Folding it requires splitting its diff by file ownership and
   replaying each part at its target's position. Assess the case first:

   - Single target or no shared files → plain `fixup` + `rebase -i --autosquash`.
   - Several targets, shared files, but the correction's regions are disjoint
     (different functions/regions per file) → the rebuild below; mostly clean,
     a few hand-merged hunks.
   - The same file is owned by several targets *and* the correction overlaps
     those regions → per-file conflict surgery; the single "phase commit"
     (§folding cost) is the pragmatic alternative.

   Recipe (on a disposable branch, per §Execute):

   1. **Split by file ownership.** `git show <correction> -- <files-of-target-T>`
      yields T's part. Test/hygiene parts fold into the commit that first adds
      those files (e.g. the test-module commit), not into the code commits.
   2. **Rebuild in the ideal order**: `git cherry-pick -n <original-commit>` for
      each commit, then apply the target's part onto the just-built state with
      `git show <correction> -- <files> > <patch>` + `git apply --reject
      <patch>` (write to a file — the stdin pitfall applies). Rejected hunks
      are region-context mismatches; apply them by hand from the `.rej` file.
   3. **Hand-merge split-ownership hunks.** The 3-way merge can combine a
      signature change from one side with a body change from the other,
      producing a non-compiling mix (e.g. `SwapLocator` signature with an
      `OperationHandle` body). Fix each to the final form; intermediate
      commits need not compile, but the mix must not survive into the final.
   4. **Verify per commit, not once at the end.** After each rebuilt commit,
      grep for leftover conflict markers (`<<<<<<<` / `=======` / `>>>>>>>`
      and stray `xxxxxxx (subject` fragments) and diff the touched files
      against the original tip's corresponding state. Dropped lines and marker
      remnants are exactly what a single end-check discovers too late. The
      definitive end check stays `git diff <original-tip> <fold-branch>`
      empty — but reach it through per-step checks.
   5. **Audit the file history, not just the tip tree.** A junk fragment can
      enter in one rebuilt commit and be removed in a later one (a net-zero
      pair): the final tree is clean but the history still shows it added and
      removed — a reviewer sees it in `git log -p`. After the rebuild, for
      each touched file run `git log -p <base>..HEAD -- <file>` and check it
      shows no junk entering and leaving the range (no add-then-remove of
      markers or stray fragments). Fix by rewriting the commit where it
      entered (e.g. `git filter-branch --tree-filter` deleting the junk
      lines), not by a later cleanup commit.

4. **Operational tips (verified 2026-08)**
   - Non-interactive autosquash: `GIT_SEQUENCE_EDITOR=: git rebase -i
     --autosquash` accepts the generated todo without an editor.
   - Bulk message rewrite: `git filter-branch --msg-filter '<script>'` with a
     script that maps each subject to its final message; run on `<base>..HEAD`
     and clean `refs/original/` afterwards.
   - Parent-repo gitlink rebuild after a submodule rewrite: build the new
     parent commits with `git commit-tree` on the old trees, then fix the
     submodule entry via a temp index — `GIT_INDEX_FILE=<tmp> git read-tree
     <commit>^{tree}`, `git update-index --cacheinfo
     160000,<new-submodule-head>,<path>`, `git write-tree`, commit-tree, and
     `git update-ref refs/heads/main <new>`. Never `reset --hard` on a parent
     with unrelated dirty work.
   - `git apply` via **stdin can corrupt patches on Windows** (text-mode stdin
     translates LF to CRLF, so contexts never match). Write the patch to a
     file and apply that; prefer file-based `git apply` or the interactive
     rebase's 3-way merge machinery over hand-applying hunks. After
     `git apply --cached`, verify the staged blobs kept LF
     (`git show :<file> | grep -c $'
'` must be 0) — a CRLF-indexed blob
     diffs wholesale against an LF worktree.
   - **Folding cost trade-off:** when a review/follow-up commit shares files
     with several earlier commits (e.g. one source file owned by three
     feature commits), folding it into each owner needs conflict surgery per
     file. A pragmatic alternative that keeps history honest: merge the
     follow-ups into a single deliberate "review round" commit instead —
     acceptable when per-target folding is disproportionate.

4. **Verify** — first prove content is unchanged: `git diff <original-tip>
   <rewritten-branch>` must be empty (only grouping changed). Then run the
   project's build + tests once on the final state (see `rem-commit-workflow`).
   Intermediate commits need not compile; the final state must. For a
   multi-repo batch: per-repo tree identity plus one integration test run
   covers the whole batch — the project's test suite exercises every module.
   Path-stripping needs a **history-level check** in addition: `git log
   --oneline -- <paths>` must be empty — tree identity alone misses files
   added and removed within the range.

## Boundaries

- **Do not rewrite**: pushed commits, shared branches, tags, releases, hashes
  referenced in docs or issue trackers.
- **A fix whose target content came from a pushed commit cannot be folded** —
  keep it as its own commit (the origin is outside the rewritable range).
- **Already pushed a mistake?** Do not rewrite — add a corrective commit.
- When in doubt whether a commit was pushed, treat it as pushed.

## Checklist

Before rewriting history:

- [ ] Range is un-pushed only: `git log <remote>/<branch>..HEAD` — never rewrite pushed/shared commits, tags, or releases
- [ ] Rebuild runs on a disposable branch; the original branch is untouched until the tree-identity check passes
- [ ] Final messages follow the commit convention and describe the final state (no WIP/fixup noise in the result)
- [ ] Corrections to un-pushed commits fold into their targets (amend/fixup), not new follow-up commits
- [ ] Net-zero: add-then-remove pairs never enter the range; file history audited (`git log -p <base>..HEAD -- <file>`) for junk that entered and left
- [ ] Uncommitted changes preserved as a patch file before any `reset --hard`-style finalize (stashes get wiped)
- [ ] Tree identity proven at the end: `git diff <original-tip> <rewritten-branch>` empty; per-commit checks done during the rebuild (conflict markers, touched-file diffs)
- [ ] Build + tests run once on the final state (see `rem-commit-workflow`)

## Cross-references

- `rem-commit-workflow` — commit-message convention, one-logical-change, split
  at commit time, build/test validation of the final state
- `rem-public-skill-generalization` — this skill is public; keep it generalized
