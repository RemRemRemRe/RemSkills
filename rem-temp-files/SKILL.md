---
name: rem-temp-files
description: >
  Route scratch — patches, generated message files, throwaway clones, temporary
  git worktrees — to the OS temp dir resolved from the environment
  (`%TEMP%`/`%TMP%`, `$TMPDIR`/`/tmp`): temp is the default; only files a later
  reader needs persist into the run/artifact directory, never the working tree.
  Use whenever a session writes intermediate files.
metadata:
  category: meta
  trigger: always
---

# Temp Files

**Scratch goes to the OS temp dir resolved from the environment — never
hardcoded, never beside the project.** Windows `%TEMP%` (`%TMP%` fallback),
POSIX `$TMPDIR` (`/tmp`).

One unique subdirectory per task (`mktemp -d`) keeps parallel runs apart.
**Temp is the default; persistence is earned:** persist only files a later
reader needs (report/gate citation, a later stage, a reviewer) into the
run/artifact directory; one-shot patches, message files, probe inputs,
intermediate dumps and superseded copies stay in temp.

- Clean up what you own — above all a temporary git worktree: the dir lives in
  temp, its registration in the repository; a stale entry blocks a branch switch.
- Temp may vanish between commands; keep a durable copy of what the task must
  not lose.
- State the temp path whenever it holds evidence (a patch, a log).
- Executors too: log to temp; copy into the run dir only what the report or gate
  cites — never the working tree, never a command's output path.

## Checklist

- [ ] Scratch, clones and worktrees live under the OS temp dir — no project-tree or drive-root scratch
- [ ] One unique subdirectory per task, so parallel runs cannot collide
- [ ] Temporary git worktrees removed; no registration left behind
- [ ] Only later-reader files sit in the artifact dir; generators, patches and message files stayed in temp
- [ ] Nothing scratchy in the repository tree, ignored paths included — the run's output is in its run dir
- [ ] The temp path is stated where it holds evidence
