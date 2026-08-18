# Submodule Push — Pitfall Catalogue

Every entry is a failure mode observed in practice, with the diagnostic and
the fix. Read §1–§6 of SKILL.md first; this file is the expanded detail.

## The three axes, and why axis 3 got missed

Push safety has three axes: parent unpushed commits, submodule unpushed
commits, and **gitlink ↔ HEAD sync**. The third was missed in practice:

- The audit ran `rev-list HEAD --not --remotes=origin` per submodule (axis 2)
  and the parent ahead count (axis 1), and both were green.
- Meanwhile the parent's gitlink for one submodule still recorded an old
  commit — the submodule had been rebased and pushed, but the gitlink update
  was never committed to the parent.
- `git push --recurse-submodules=check` passed, because the old gitlink value
  was itself already pushed long ago. **`check` validates reachability of the
  recorded gitlink; it cannot know the gitlink is stale.**

Fix: before any push, run `git status --short` in the parent and require zero
`M`/`Mm` lines under submodule paths; or `git submodule status` and require no
`+` prefix. This is axis 3 and it is not optional.

## Non-fast-forward: same-topic commits, different hashes

Two forks in this session were rejected with `[rejected] ... (non-fast-forward)`.
Both had a history where the same logical changes ("remove EngineVersion",
"make SetInputDirection public", ...) existed under **different hashes** on
the local branch and on the remote — the local history had been rebased at
some point; the remote kept the old hashes.

Diagnosis:
```
git fetch <remote> --prune
git log --oneline <remote>/<branch>..HEAD    # local-only
git log --oneline HEAD..<remote>/<branch>    # remote-only
```
Look for paired commits with identical subjects. Fix: `git rebase
<remote>/<branch>` — git's cherry-pick detection skips local commits whose
content the remote already has, and only genuinely new work is replayed.
Then push normally. Do **not** force; the remote is usually not wrong, it is
just older.

## "Looks identical but isn't": rebase can silently drop content

The most dangerous trap. In this session, the upstream project had just
merged a fix with the **same subject** as a local commit ("Fixed compilation
errors with ue5-main"). It looked like a duplicate; it was a different
implementation:

```
git diff upstream-merge-commit local-commit --stat   # 7 files, 32+/12-
```
32 lines of real divergence (a `DetailsView` pin fix, include ordering, a
`LexFromString` vs `FString::Format` semantic choice).

What happened: `git rebase --onto <upstream> <local-base> <branch>` replayed
only the incremental diff (`1 file, 2+/1-`), and the base commit carrying
the other 32 lines was dropped. The result compiled-looking but had silently
lost the local fix. **The rebase succeeded; no error fired.**

Guard rails:
1. Before rewriting, diff the local tip against the upstream merge:
   `git diff <upstream-tip> <local-tip> --stat`. Non-trivial divergence =
   do not assume duplication.
2. After any rebase, verify the intended content survived:
   `git diff <pre-rebase-tip> HEAD` must be **empty**.
3. When content must be preserved wholesale, rebuild the commit from the
   known-good tree instead of replaying increments:
   ```
   git reset --hard <upstream-tip>
   git checkout <known-good-commit> -- <source-dir>
   git commit -m "<same message>"
   ```
   then confirm `git diff <known-good-commit> HEAD` is empty.

## Pushed the mid-rebase state

During a multi-commit rebase, one commit conflicted; the rebase paused. The
push ran anyway and published the mid-state tip — the pending commit's
content was silently missing on the remote.

- Symptom: `git status` shows `interactive rebase in progress` / `You are
  currently rebasing branch ... (fix conflicts and then run "git rebase
  --continue")`.
- Rule: **never push while a rebase/merge is in progress.** Finish
  (`git rebase --continue` after resolving) or `--abort`.
- After finishing, the previously-pushed mid-state needs a forced update —
  follow SKILL.md §6 (tree check + `--force-with-lease`).

## False-positive unpushed count for a deleted remote

`git rev-list --count HEAD --not --remotes=origin` counts commits in HEAD
that no remote-tracking ref covers. If a submodule's fork was **deleted**
(remote 404s), the stale cached refs cover almost nothing, and the count can
be absurd (1000+). `git remote -v` confirms the target is gone; a submodule
with no push target is excluded from all counts, not pushed.

Also note `git push --recurse-submodules=check` skips submodules that have no
remote at all — the missing-target case must be handled by the audit, not by
`check`.

## Success-line detection

`git push` prints:
```
To https://github.com/<owner>/<repo>.git
   abc123..def456  HEAD -> main
```
The summary line (the second line) does not start with `To`. Detect success
by the absence of `rejected`/`error:`/`fatal:`, or by the `..` range line —
not by grepping for `^To`.

## Batch classification by owner

`git remote get-url origin` string-match on your account names classifies
submodules as pushable. Two account names may both be yours (a fork account
and a family-org account) — list both in the local companion skill. A
third-party `origin` (original author) is never pushable, even if it is a
clean fast-forward; local-only edits there stay local (e.g. removing
`EngineVersion` from a `.uplugin` for cross-version compatibility).
