# Orchestration policy (main session)

Hard rules for this project, always in force. The procedure behind them - delegation
mechanics, the writing-code / full-check sequence, run-directory and `resume` conventions, waiting
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
- **Iteration is code-only.** Compile the affected target and record test intent; specs and the
  build + suite run happen once, in the full check. Working records - a decision, a deferral, a design
  note - are written when the need appears; they are what makes a deferral safe.
- **Fewest cycles, best method.** Every stage takes the cheapest route that still produces the
  evidence it needs: batch related edits into one compile, script mechanical sweeps, run independent
  work in parallel, reuse evidence on an unchanged tree, and never repeat a cycle that a better
  order avoids. Count round trips, not keystrokes - a round trip costs more than a larger first
  attempt.
- **Run the full check on settled work only.** Specs and deliverable docs wait until the surface a
  change exposes stops moving; until then keep iterating (compile + intent lines) with no spec and no
  deliverable doc. The settling criteria and the ceiling on unfrozen work live in
  `rem-orchestration`.
- **A deferred step leaves a record.** Whatever is postponed - a test, a doc, a refactor, a
  decision - gets one line: what, why, and when it must be handled, in a ledger (`plan.md`,
  `test-debt.md`, `knowledge-candidates.md`). No record means the step is dropped, not deferred.
- **A push carries no test debt.** A deferred test for a behaviour change goes on
  `<run-dir>/test-debt.md` and must be paid before the code leaves the machine
  (`rem-test-completeness` §4).
- **What the operator reads is plain and short.** Anything addressed to the operator - the main
  session's replies and the subagent reports the harness shows them - keeps terms few, avoids jargon
  and coined shorthand (write "verification run", not "VR"; "test scope", not "scope"), and explains
  a term the operator did not introduce the first time it appears; the writer picks the language
  (English, Chinese or mixed) for whatever carries the point best, not by rule. Every claim carries
  context - what changed, why it matters, what it affects, what happens next - prefers numbers, file
  paths and quoted evidence to adjectives, stays about a screenful, and points at the artifact for
  detail; a line the operator can neither learn from nor act on is deleted.
  `rem-orchestration` carries the procedure (*Talking to the user*).
- **Prefer events over polling.** Never use `get_subagent_result(wait: true)` as a blocking
  wait and never sleep-poll - read the run directory instead.
- **Always pass an explicit `subagent_type`** - the built-in names are disabled.
