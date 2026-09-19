---
name: rem-orchestration
description: >
  Main-session orchestration policy for a project that uses this collection: delegate execution
  to subagents with self-contained briefs (background by default, never inheriting context), run
  the iteration/freeze cadence - compile-only iteration, one build + suite at the freeze point -
  and prefer events over polling when waiting. Use when planning, delegating, or sequencing work
  as the main session in such a project.
metadata:
  category: workflow
  trigger: manual
---

# Main-Session Orchestration

The main session is the decision ledger; executors are its hands. Keep the goals,
constraints, acceptance criteria and pointers; push raw material (diffs, logs, file
bodies) into subagents and run directories. The project's short hard rules live in its
agent context file, which points here for the procedure.

## Delegation

- **Delegate execution, keep decisions.** A unit whose raw output exceeds ~10k tokens, or
  whose process is open-ended (build/fix loops, debugging, batch refactors, repo-wide
  search), belongs to a subagent. Small, high-coupling steps stay in the main session - the
  brief/report fixed cost makes delegation a net loss there.
- **Briefs are self-contained.** Objective / scope (allowed + forbidden) / constraints /
  acceptance / report pointer. Never rely on inherited context; a subagent that cannot
  start without it is a brief defect.
- **Background by default.** Pass `run_in_background: false` only when the next decision
  needs the result in the same turn and nothing else can run meanwhile. Parallelism comes
  from issuing several Agent calls in one message, not from the background flag.
- **Writes serialize, reads parallelize.** Never run two writers over the same file.
- **No profile turn cap.** `max_turns` is a per-call kill switch: at the limit the child
  gets one wrap-up turn and is then aborted (the run is still reported as completed), so
  read the run directory instead of assuming a report exists.
- **Verify from artifacts.** A run's outcome is its run directory (`report.md`, logs) or the
  child session's final message - never "it is still running".

## Iteration and freeze

Iteration is code-only; the expensive gates run once, at the freeze point.

1. **Iteration** - per work unit: edit, compile the affected target, record test intent in
   `<run-dir>/test-intent.md` as one `trigger -> assertion` line per behaviour. No specs,
   no suite run, no docs sweep.
2. **Freeze review** - one review pass over the accumulated diff produces the case plan:
   the existing-case index plus the missing or updated cases.
3. **Test authoring** - write the cases from that plan.
4. **Verify** - one build plus one suite run, at the scope decided up front, on the frozen tree.
5. **Docs, then git** - batch the documentation obligations once, then commit. When the tree
   did not change after verify, the commit stage checks the recorded evidence instead of
   re-running. A bug fix proves its regression case by temporarily reverting the fix at the
   freeze point.

## Waiting

- Prefer events over polling: background subagents wake the session on completion; a long
  external process is run as a blocking call with a sufficient tool timeout.
- Do not use `get_subagent_result(wait: true)` as a blocking wait, and do not sleep-poll. If
  a run looks stuck, read its run directory or child session for a final message before
  waiting again; report a genuine stall to the user.
- 15 s is the pragmatic ceiling for a poll interval; use a better signal when one exists.

## Artifacts

- **Temp first** (`rem-temp-files`): one-shot generators, patches, message files and
  superseded logs stay in a unique temp dir. `<cwd>/.agents/runs/<run-id>/` receives only
  what a later reader needs — `brief.md` (parent), `state.md`, `test-intent.md`, the
  authoritative logs and `report.md` (executor, append-only); the final message stays a
  bounded summary with pointers.
- `resume` continues the same child session and the same run directory: append to
  `state.md`, never create a new run dir.

## Checklist

- [ ] Decisions, constraints and acceptance criteria stayed in the main session; raw material went to executors and run dirs
- [ ] Run dirs hold only what a later reader needs — one-off generators, patches and message files stayed in temp (`rem-temp-files`)
- [ ] Every brief was self-contained (no inherited context) and named its acceptance criteria
- [ ] Execution ran in the background unless the same turn needed the result
- [ ] Iteration stayed compile-only; specs, the build + suite and docs ran once at the freeze point
- [ ] No polling waits, no `wait: true` blocking; completion judged from the run directory
