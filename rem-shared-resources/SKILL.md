---
name: rem-shared-resources
description: >
  Coordinate several agent sessions working in one project directory: claim the files a session will
  write, lease the build, test, git and IDE resources with a TTL and stale takeover, keep per-session
  logs, and bind build/test evidence to the tree that produced it. Use when two or more sessions or
  operators work on the same project at the same time, or before a build, suite run, git rewrite or
  formatter run that another session might also use.
metadata:
  category: workflow
  trigger: manual
---

# Shared Resources

Sessions that share one working directory cannot be isolated from each other: they share the source
files, the build outputs, the test runtime and the repository. Coordination replaces isolation:

- **Claims** say what a session will write; overlapping claims are the one conflict no lease can fix.
- **Leases** serialize the resources that cannot be shared.
- **Evidence identity** stops a green result from being reused on a tree someone else changed.

The tool that enforces the protocol is `tools/lease.mjs` (zero dependencies, POSIX and Windows). Every
session of the project points it at one lock directory (`--dir`, or `LEASE_DIR`); the project's path
and its resources are values in the local overlay, not in this file.

The project-specific values - lock directory, resource keys, log redirection - live in
`local/project-resources.md` when the overlay is present.

The protocol is advisory: a session that ignores it can still write. Its value is that a session that
follows it never collides, and a session that ignores it is visible in `status`.

## 1. Claim before the first edit

A session claims its write set before editing: the module directories, or finer - the files it will
touch. Module granularity is the fallback; a finer claim lets two sessions work inside one module when
their files do not intersect.

```
node tools/lease.mjs claim <module-or-file> ...
node tools/lease.mjs unclaim <path>...
node tools/lease.mjs status
```

A conflicting claim is refused with the other session's paths and identity. Resolve it by splitting the
unit, waiting, or agreeing on ownership; `--force` records an accepted overlap and is a deliberate
exception, never a habit. A session never writes outside its claims.

## 2. Lease a shared resource

```
node tools/lease.mjs run <resource> [--ttl 900] [--wait 120] [--intent "<what>"] -- <command...>
```

`run` takes the lease, runs the command, and releases it on exit, error or signal; it carries its pid
and renews the TTL while the command runs. The resource name is the key: different keys run in
parallel, the same key queues.

| Resource | Key | Parallelism |
|---|---|---|
| Build | `build:<target>:<configuration>` | different configurations of one target may run in parallel when their outputs are disjoint; the same key is exclusive. The engine installation is read-only shared state - never write it |
| Test suite | `test:<project>` | one suite at a time; each session redirects its log to its own run directory |
| Git | `git:<repository>` | one owner at a time for commit, history rewrite and push |
| IDE / formatter | `ide:<project>` | one session formats or drives the debugger at a time |

A session holds **one lease at a time**: never acquire a second resource while holding one - that is how
two sessions deadlock. An operation that needs two resources takes one combined key, or runs them in
sequence. `acquire` without `run` is TTL-only: it exists for multi-step work, and the holder releases it
when done.

## 3. Identity, not trust

Every build and test result records the tree it ran on: `HEAD`, a digest of `git status --porcelain`,
and the session's claims. Evidence is reused only when that identity is unchanged; a change by any
session invalidates it, and the full check re-runs. A build reporting "target is up to date" is not
evidence either (`rem-orchestration`).

## 4. Failure handling

- **Crash or kill.** A `run` lease carries its pid and a heartbeat; a dead holder is taken over, and the
  takeover prints who held it, so the record exists.
- **Expired manual lease.** A manual `acquire` is TTL-only; once the TTL passes another session takes it
  over. Release it when the work ends, and keep the TTL short enough to be a useful signal.
- **Live but expired.** A live process is never stolen without `--force` - a full build may legitimately
  run long. Confirm with the other session first.
- **Deadlock.** Structural: one lease at a time, bounded waits, TTL. Nothing waits for a second resource
  while holding one.
- **Git lock files.** A held `index.lock` usually means another session is writing the index. Wait and
  retry; remove the file only after proving no git process is alive.

## 5. Rules that keep the tree honest

- Stage by exact path; never `git add -A`, and never commit a path outside your claims.
- One session never edits another's claimed files, and never resolves a conflict by overwriting.
- Logs, reports and scratch stay in the session's own run directory (`rem-temp-files`, `rem-orchestration`);
  a test log is redirected there rather than shared through the project's default log path.
- The engine installation is read-only for every session.
- Without concurrency the protocol costs nothing: a single session skips claims and leases entirely.

## Checklist

- [ ] The write set was claimed before the first edit; conflicting claims were resolved or recorded
- [ ] Build, test, git and formatter runs used a lease keyed by the resource, never one global lock
- [ ] Parallel builds used different configuration keys; the engine was never written
- [ ] The test log was redirected to the session's own run directory
- [ ] No second lease was acquired while one was held
- [ ] Build/test evidence carries the tree identity and was not reused across a change
- [ ] Takeovers and accepted overlaps were reported, and a live holder was never stolen without agreement
