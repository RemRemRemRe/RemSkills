---
name: rem-submodule-push
description: >
  Push a parent repo and its git submodules to their remotes safely: run the
  three-axis audit (parent unpushed commits / submodule unpushed commits /
  gitlink-to-HEAD sync), classify submodules by remote ownership, batch-push
  with explicit origin refs, use `push --recurse-submodules=check` as the
  authoritative gate, handle non-fast-forward by rebase instead of force, and
  follow force-push discipline. Use when asked to push a project with
  submodules, or after `rem-submodule-sync` updated submodules. Project values
  (paths, account lists, per-submodule ownership) live in the private
  companion skill `rem-submodule-push-local`.
metadata:
  category: workflow
  trigger: manual
---

# Submodule Push

Push the parent repo and its submodules to their remotes. The order is fixed:
**audit → classify → push submodules → push parent with check → verify**.
Never push the parent before the submodules it points at are reachable.

The companion `rem-submodule-sync` covers pulling updates in; this skill
covers pushing local work out. History-rewrite mechanics (squash, reorder,
drop) belong to `rem-rewrite-commit-history`; this skill only sets the
discipline around pushing rewritten history.

---

## 1. Three-axis audit

Push safety is three independent axes. Checking two of them is not enough.

| Axis | Command | Failure mode if skipped |
|---|---|---|
| Parent unpushed commits | `git rev-list --count refs/remotes/<origin>/<branch>..HEAD` | parent history missing on remote |
| Submodule unpushed commits | `git rev-list --count HEAD --not --remotes=origin` per submodule | submodule commits missing on remote |
| **Gitlink ↔ HEAD sync** | parent `git status --short` shows `M`/`Mm` for the submodule; `git submodule status` prefix `+` means gitlink != submodule HEAD; per submodule `git ls-tree HEAD <sub>` vs `git rev-parse HEAD` | a submodule was updated but its gitlink was never committed to the parent |

The gitlink axis is the one most often missed: a submodule can be fully
pushed (axis 2 green) and the parent fully committed (axis 1 green) while the
parent still records an **old** gitlink. `git status --short` in the parent
lists it as ` M <submodule-path>` — that line must be empty for every
submodule before pushing.

**Exit criterion:** all three axes reported; every submodule's gitlink equals
its HEAD; every `M`/`Mm` submodule accounted for.

---

## 2. Classify by remote ownership

For each submodule, `git remote get-url origin` decides whether it can be
pushed at all:

| origin owner | Can push? | Note |
|---|---|---|
| your own account(s) | yes | batch-push normally |
| original author (third party) | **no** | local-only edits stay local; no push |
| deleted / inaccessible | no | no push target; `--not --remotes=origin` may report a large false positive from stale cached refs — confirm with `git remote -v` before trusting the count |

A submodule may track `upstream` while its push target is `origin` (a fork).
The audit in §1 counts against `origin` (or every remote); do not rely on
`@{upstream}` for the push decision.

---

## 3. Batch-push submodules

Push per submodule with an **explicit** remote and branch:

```
git push origin HEAD:<branch>
```

Never a bare `git push` — the local branch may track `upstream`, and a bare
push would target the author's repo. Group pushes by account (credential
failures then fail per account, not mid-list). Record per-submodule results;
a rejected push stops that submodule only.

Detecting success: the output line `   <old>..<new> HEAD -> <branch>` means
success. Grep for `rejected`, `error:`, `fatal:` to detect failure — grepping
for `To <url>` misses the success line when the summary line is the tail.

**Exit criterion:** every classifiable submodule reports `unpushed=0` for
`origin` (`git rev-list --count HEAD --not --remotes=origin`).

---

## 4. Parent push with the check gate

```
git push --recurse-submodules=check origin <branch>
```

This is the authoritative gate: git verifies that **every gitlink commit
recorded in the parent** is reachable on the submodule's remotes, and aborts
listing the offenders otherwise. A green `check` means "everything the parent
records is out there".

**Blind spot:** `check` does NOT verify that the gitlink is the submodule's
latest HEAD — a stale gitlink pointing at an old, already-pushed commit
passes. That is axis 3's job, done in §1, immediately before this push.

On failure: `The following submodule paths contain changes that can not be
found on any remote:` — push the listed paths (go to §3), then re-run. Do
not switch to `--recurse-submodules=on-demand` to paper over the failure;
understand why each path is missing first.

---

## 5. Non-fast-forward: rebase, never force

A rejected push (remote has commits the local branch lacks) means the branch
diverged. Do not `--force`. Instead:

1. `git fetch <remote> --prune`, then `git log --oneline <local>..<remote>/<branch>` and the reverse to see both sides.
2. A common pattern: **same-topic commits with different hashes** on both
   sides (the local history was rebased at some point; the remote kept the
   old hashes). Content overlaps.
3. `git rebase <remote>/<branch>` — commits whose content the remote already
   contains are skipped automatically; only genuinely local work is replayed
   on top. Then push normally (fast-forward).

See `references/push-playbook.md` for the "looks identical but isn't" trap
that makes a plain rebase silently drop local content, and for the
verification that must precede any forced update.

---

## 6. Force-push discipline

Only when the history is deliberately rewritten (user-requested cleanup),
and then:

- **Verify the tree first**: after the rewrite, `git diff <pre-rewrite-tip> HEAD` must be **empty** (same resolution choices). A non-empty diff means content changed during the rewrite — investigate before pushing anything.
- Use `git push --force-with-lease` — it refuses if the remote moved since your last fetch.
- **Never push while a rebase/merge is in progress.** `git status` shows
  `rebase in progress`; pushing the mid-state tip publishes a partial
  history and silently omits the pending commits. Finish (`git rebase
  --continue`) or abort first.
- Forced history rewrites are irreversible on the remote; state clearly what
  was rewritten and why.

---

## 7. Verify

After the parent push:

- Parent: `git status -sb` shows `## <branch>...origin/<branch>` with no ahead.
- Submodules: `git rev-list --count HEAD --not --remotes=origin` is 0 for
  every classifiable submodule (exclude submodules with no push target).
- Unrelated working-tree changes (`.gitignore`, untracked files) are
  untouched.

**Exit criterion:** parent ahead=0, classifiable submodules unpushed=0,
unrelated changes untouched.

---

## Pitfall catalogue

Expanded failure cases — the PropertyHistory content-loss, the mid-rebase
push, the stale-gitlink miss, and the false-positive unpushed count — live in
`references/push-playbook.md`.

## Checklist

- [ ] Three-axis audit done: parent unpushed count, per-submodule unpushed count, gitlink==HEAD for every submodule
- [ ] No `M`/`Mm` submodule lines in parent `git status --short` before push
- [ ] Submodules classified by origin ownership; third-party / no-target submodules excluded
- [ ] Push used explicit `push origin HEAD:<branch>`; no bare `git push`
- [ ] Every classifiable submodule reports unpushed=0
- [ ] Parent pushed with `--recurse-submodules=check`; green on first try or after pushing the listed paths
- [ ] Rejected push handled by rebase, never `--force`
- [ ] Rewritten history: `git diff <pre-rewrite-tip> HEAD` empty before forced push
- [ ] `--force-with-lease` used, never bare `--force`
- [ ] No push while a rebase/merge is in progress
- [ ] Final: parent ahead=0; classifiable submodules unpushed=0; unrelated changes untouched
