# Rebuild Playbook

Detail moved out of `SKILL.md` so the workflow steps stay scannable: the
mid-stack folding recipe and the verified platform/tooling pitfalls. Read this
while a rebuild is running — the rules and the step order live in `../SKILL.md`.

---

## 1. Mid-stack folding

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
  (§2 below) is the pragmatic alternative.

Recipe (on a disposable branch, per the Execute step in `../SKILL.md`):

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

## 2. Operational tips (verified 2026-08)
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
- **Tree rebuild without text-pipe corruption (verified 2026-08):** piping
  `git ls-tree` into `git mktree` through a shell pipe (Windows PowerShell
  converts LF to CRLF) silently appends `\r` to every entry name — every
  blob appears "renamed" to a `\r`-suffixed name. Rebuild a stripped tree
  with a temp index instead: `GIT_INDEX_FILE=<tmp> git read-tree
  <commit>^{tree}` → `git rm --cached -f -r <paths>` → `git write-tree`.
  The temp index also bypasses PowerShell entirely.
- **`git rm --cached` on a temp index needs `-f` (verified 2026-08):** when
  the temp index's content differs from HEAD, git's safety guard refuses
  ("staged content different from both the file and the HEAD") — add `-f`;
  check the exit code instead of swallowing stderr.
- **Fold into the file's last toucher (verified 2026-08):** a `fixup!`
  commit's patch is computed against HEAD, so it applies cleanly only to a
  commit whose version of the file equals HEAD's. Fold a correction into
  the commit that LAST touched the file (or amend the tip); folding into
  an earlier toucher produces context conflicts with the intermediate
  commits' patches.
- **Locate the fold target by its role, not by `git log -1 -- <path>`
  (verified 2026-09).** While the work you are folding is still a commit, that
  command answers with **that commit** — it is the most recent toucher of the
  path — so the fixup ends up aimed at its own descendant, and `--autosquash`
  replays the change onto the wrong ancestor and stops mid-flight
  (`Could not apply <sha> … # fixup!`). Reset the later commit away first (its
  changes return to the worktree), then match the target by subject — a `fixup!`
  needs the target's subject verbatim anyway — or by its position in the rebuilt
  history. That ordering is what makes the fold clean: the artifact commit is a
  valid fixup target exactly when it has become the file's last toucher again.
  After an aborted attempt, prove nothing moved before retrying (`git diff
  <pre-rebase-tip> HEAD` is empty — a rebase reorders commits, it does not touch
  the worktree), and treat the fold as done only when each artifact file is
  touched by exactly one commit (`git log --oneline -- <path>`).
- **State the expected content delta before you look (verified 2026-09).** Two
  folds an hour apart needed opposite expectations: folding commits into the
  artifact commit that owns their files is a pure regroup, so the end diff must
  be **empty**; carrying a new edit through the same rebase must show **exactly
  that edit and nothing else**. A copied invariant fails both ways — accepting a
  diff because you expected one hides a loss, and demanding emptiness after an
  edit hunts a discrepancy that is your own intended change. Name the expected
  delta first ("empty", or "the N lines I just wrote") and diff the result
  against the pre-rewrite tip.
- **Never push quoted text through several escaping layers (verified 2026-09).**
  A commit message, patch or search pattern that travels shell → JSON → tool
  loses backslashes silently, and an argument quoted with single quotes ends at
  the first apostrophe in the text; the wrapper still reports success. Write such
  text to a file and pass the file (`git commit -F <file>`, `--file`), or use a
  quoted heredoc. Then **verify the mutation**: grep for the text you added. A
  replace-all that reported "applied 2 edits" failed exactly there — both
  backslash-bearing patterns never matched, while a forward-slash pattern in the
  same call did.
- **`rebase --continue` re-invokes GIT_EDITOR (verified 2026-08):** the
  continue re-commits the resolved commit and runs the editor with its
  message file. A one-purpose message editor (e.g. written for a squash)
  will overwrite the wrong commit's message — scope the editor or reword
  the damaged commit afterwards.
- **Reorder + squash can mis-attribute diffs (verified 2026-08):** the
  3-way merge during a reordered rebase may attribute a file's change to
  the wrong commit (a later "move X to Public" diff landed inside a
  squashed benchmark commit). After the reshape, audit per file
  (`git log -p <base>..HEAD -- <file>`) and verify each commit's diff
  matches its subject.
- **Editor paths on Windows need forward slashes (verified 2026-08):**
  Git Bash mangles backslashes in `GIT_SEQUENCE_EDITOR` / `GIT_EDITOR`;
  use `<script-dir>/script.cmd`, and make the script a .cmd that echoes the
  message / rewrites the todo.
- **Gitlink stat ghosts (verified 2026-08):** the parent repo may report a
  submodule gitlink as ` M` while HEAD==INDEX==WORKTREE hash-match —
  untracked files inside the submodule (local-only docs) trigger it.
  Cosmetic: `git status --ignore-submodules=untracked` confirms the
  gitlink itself is clean; `git update-index --refresh` does not always
  clear it.
