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

A local commit that is not pushed is **amended to fold in the final state**
(e.g. a comment-language fix) instead of leaving a follow-up "fix" commit —
this is the collection's rule, owned here.

## Workflow

1. **Inspect** — `git log <remote>/<branch>..HEAD`: list the un-pushed commits,
   their messages, and what each actually changed.
2. **Plan** — group the changes by final logical change (one per commit); decide
   per commit: keep / reword / squash / drop / reorder.
3. **Execute** — `git rebase -i <base>` (or `--autosquash` with `fixup!`
   commits); resolve conflicts like any rebase.
4. **Verify** — once the stack is coherent, run the project's build + tests
   once on the final state (see `rem-commit-workflow`). Intermediate commits
   need not compile; the final state must.

## Boundaries

- **Do not rewrite**: pushed commits, shared branches, tags, releases, hashes
  referenced in docs or issue trackers.
- **Already pushed a mistake?** Do not rewrite — add a corrective commit.
- When in doubt whether a commit was pushed, treat it as pushed.

## Cross-references

- `rem-commit-workflow` — commit-message convention, one-logical-change, split
  at commit time, build/test validation of the final state
- `rem-public-skill-generalization` — this skill is public; keep it generalized
