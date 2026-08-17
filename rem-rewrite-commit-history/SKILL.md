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

## Cross-references

- `rem-commit-workflow` — commit-message convention, one-logical-change, split
  at commit time, build/test validation of the final state
- `rem-public-skill-generalization` — this skill is public; keep it generalized
