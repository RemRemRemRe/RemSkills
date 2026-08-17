---
name: rem-commit-workflow
description: >
  Commit local changes in a UE project and verify them — single-responsibility
  commits, English comments, reformat edited files, then build and run the
  project's automation tests headless. Use when committing plugin changes,
  splitting a mixed commit for review, or running the project's test suite.
  Machine- and project-specific values (paths, target, config, test prefix,
  disabled plugins) live in the private companion skill
  `rem-commit-workflow-local`.
metadata:
  category: workflow
  trigger: manual
---

# Commit Workflow

## Commit message

Follow `Type: short desc` in English. The accepted types for this collection are:

| Type | Use for |
|---|---|
| `New` | new things |
| `Changed` | it changed |
| `Improvement` | better thing |
| `Removed` | it gets removed |
| `Fixed` | fixed a bug |
| `Misc` | typo, formatting, naming |

The per-project authoritative list lives in the project's commit-convention
config (the local companion skill `rem-commit-workflow-local` keeps a copy).
Accept the types the project's config defines. Add a body when the change
spans several concerns or the "why" is non-obvious.

## Commit hygiene

- One logical change per commit. Split a mixed commit (rename + bug fix, class
  filter + module tidy) into one commit per reason-to-change. Intermediate
  commits do not need to compile — the split serves review and maintenance.
- Comments are English, never Chinese.
- Reformat edited files before committing so the code matches the solution code
  style.
- Stage by exact path; never `git add -A` — leave unfinished work uncommitted.
- Reshaping the history of un-pushed commits (amend, fixup, squash, reorder,
  drop) belongs to `rem-rewrite-commit-history`: a follow-up "fix" is folded
  into its target before push, not left as noise in the pushed history.

## Dependency declaration

Each module lists its own dependencies explicitly; nothing is inherited
transitively. Leaf/third-party types leaking into a public header are declared
by each consumer, not promoted to `PublicDependencyModuleNames`. See
`rem-cpp-best-practices` §15.

## Build

```
<engine-install-path>\Engine\Build\BatchFiles\Build.bat <target>Editor Win64 <config> -project="<project-dir>\<ProjectName>.uproject" -waitmutex
```

Use the project's editor development configuration — never build a different
editor config for this. Exact engine path, target, and config are project
facts: see `rem-commit-workflow-local`.

## Run tests

```
<engine-install-path>\Engine\Binaries\Win64\UnrealEditor-Win64-<config>-Cmd.exe "<project-dir>\<ProjectName>.uproject" -unattended -nullrhi -ExecCmds="Automation RunTests StartsWith:<test-prefix>; Quit" -TestExit="Automation Test Queue Empty" -DisablePlugins=<nullrhi-crash-plugin> -log
```

- Disable plugins known to crash under `-nullrhi` (the project's list is in
  `rem-commit-workflow-local`); the filter is `StartsWith:<test-prefix>`, not `*`.
- The console prints only UBT platform validation — judge red/green from
  `<project-dir>/Saved/Logs/<ProjectName>.log` (search `Result={Fail}`; green
  ends with `**** TEST COMPLETE. EXIT CODE: 0 ****`).
