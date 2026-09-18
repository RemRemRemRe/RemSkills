# Orchestration policy (main session)

Project-level policy for the main session. Procedures live in the referenced
skills; this file fixes defaults and pointers only, so it stays short - it is
loaded into every session under this directory.

## Tools
- Disk scanning is banned (rem-no-disk-scanning). Search only through the project's
  MCP server: symbol search / find-usages first, then a bounded text search
  (`maxResults` + path/glob). No `rg`, `grep`, `find`, `fd`, no shell equivalents,
  no editor equivalents.
- MCP search unavailable -> stop and tell the user; never substitute a scanner.
- The built-in `explore` / `plan` / `general-purpose` subagent types are shadowed
  by local overrides that are **disabled by default** (`enabled: false`), so those
  names are unavailable. Always pass an explicit `subagent_type` from the project
  profiles (`recon`, `grill`, `review`, `author`, `verify`, `debug`, `git`,
  `skill-authoring`); omitting the type fails loudly instead of spawning a generic
  agent.

## Delegation defaults
- Execution-heavy work goes to a subagent; the main session keeps the decisions and
  the ledger. Write self-contained briefs - never rely on inherited context.
- Subagents default to the background; pass `run_in_background: false` only when the
  parent needs the result in the same turn and has nothing else to do. Reads may run
  in parallel; writes serialize per file.
- Profiles carry no fixed turn cap. Set `max_turns` per call only when a runaway is
  plausible, and treat it as a kill switch: the run gets one wrap-up turn and is then
  aborted (still reported as completed), so read the run directory instead of assuming
  a report exists.
- Verify a run's outcome from its run directory (`report.md`) or the child session's
  final message - not by waiting.

## Iteration and freeze
- Iteration: code only. Per unit: edit, compile the affected target, record test
  intent in `<run-dir>/test-intent.md` (`trigger -> assertion`). No specs, no suite.
- Freeze (end of the iteration, before commit): one review pass over the accumulated
  diff produces the case plan (existing-case index + gaps); then the test-authoring
  pass writes the cases; then one verify pass (build + suite) covers the frozen tree;
  then the docs pass; then git. If the tree did not change after verify, git verifies
  the recorded evidence instead of re-running.
- Bug fixes: prove the regression case by temporarily reverting the fix at the freeze
  point.

## Waiting
- Prefer events over polling: background subagents wake the session on completion; a
  long external process is run as a blocking call with a sufficient tool timeout.
- Do not use `get_subagent_result(wait: true)` as a blocking wait and do not
  sleep-poll. If a run looks stuck, read its run directory / child session for a final
  message before waiting again; report a genuine stall to the user.
- 15 s is the pragmatic ceiling for a poll interval; if a better signal exists, use it.

## Artifacts
- Run directories: `<cwd>/.agents/runs/<run-id>/` (`brief.md` from the parent;
  `state.md`, logs, `report.md` from the executor, append-only).
- `resume` continues the same child session and the same run directory; append to
  `state.md`, never create a new run dir.
