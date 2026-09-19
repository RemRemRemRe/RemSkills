# Orchestration policy (main session)

Hard rules for this project, always in force. The procedure behind them - delegation
mechanics, the iteration/freeze sequence, run-directory and `resume` conventions, waiting
discipline - lives in the `rem-orchestration` skill; load it when planning, delegating or
sequencing work.

- **Disk scanning is banned** (`rem-no-disk-scanning`). Search only through the project's
  MCP server; when it is unavailable, stop and tell the user - never substitute a scanner.
- **Delegate execution.** The main session keeps decisions and the ledger; subagents get
  self-contained briefs, default to the background, and never inherit context. Profiles
  carry no turn cap - `max_turns` is a per-call kill switch.
- **Nothing scratch in the repository.** Temp files, throwaway clones and worktrees go to the
  OS temp dir, a run's own output to its run directory (`rem-temp-files`); never into the
  working tree, ignored paths included.
- **Iteration is code-only.** Compile the affected target and record test intent; specs,
  the build + suite run, docs and commits happen once, at the freeze point.
- **Prefer events over polling.** Never use `get_subagent_result(wait: true)` as a blocking
  wait and never sleep-poll - read the run directory instead.
- **Always pass an explicit `subagent_type`** - the built-in names are disabled.
