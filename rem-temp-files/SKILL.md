---
name: rem-temp-files
description: >
  Route ephemeral scratch files — patches, generated message files, plan data,
  throwaway clones, temporary git worktrees — to the OS temp directory resolved
  from the environment (`%TEMP%`/`%TMP%` on Windows, `$TMPDIR`/`/tmp` on POSIX),
  never into the project tree or a project-adjacent scratch folder. Use this
  constraint whenever a session writes intermediate files.
metadata:
  category: meta
  trigger: always
---

# Temp Files

**Scratch goes to the OS temp directory, resolved from the environment — never
hardcoded, never beside the project.**

| Platform | Variable | Fallback |
|---|---|---|
| Windows | `%TEMP%` (`$env:TEMP`) | `%TMP%` |
| POSIX | `$TMPDIR` | `/tmp` |

One unique subdirectory per task (`mktemp -d`) keeps parallel runs from
colliding. Lifetime decides the home: a by-product that bridges two commands is
scratch (temp); a log or report a later review must read is an artifact (the
project's run/artifact directory — its own convention).

- Clean up what you own — above all a temporary git worktree: the directory
  lives in temp, but the registration stays in the repository, and a stale
  entry blocks a later branch switch.
- Temp may vanish between commands; keep a durable copy of a result the task
  must not lose.
- State the temp path whenever it holds evidence (a patch, a log).

## Checklist

- [ ] Scratch files, clones and worktrees live under the OS temp dir resolved from the environment — no project-tree or drive-root scratch
- [ ] One unique subdirectory per task, so parallel runs cannot collide
- [ ] Temporary git worktrees removed; no registration left behind
- [ ] Durable artifacts (reports, logs to review later) live in the project's artifact directory, not temp
- [ ] The temp path is stated where it holds evidence
