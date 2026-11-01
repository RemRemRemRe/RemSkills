# Orchestration policy (main session)

Hard rules, always in force. The procedure behind them - delegation, the write-code / full-check
sequence, run directories, waiting - lives in the `rem-orchestration` skill; load it when planning,
delegating or sequencing work.

- **Disk scanning is banned** (`rem-no-disk-scanning`). Search only through the project's MCP
  server; if it is unavailable, stop and tell the user - never substitute a scanner.
- **Delegate execution, keep decisions.** Briefs are self-contained, run in the background unless
  this turn needs the result, and always pass an explicit `subagent_type` (the built-in names are
  disabled); the main session owns the decisions and the ledger. `max_turns` is a per-call kill
  switch, not a profile setting.
- **Nothing scratch in the repository.** Temp files and throwaway clones go to the OS temp dir, a
  run's own output to its run directory (`rem-temp-files`).
- **Iteration is code-only; the full check runs on settled work.** Iterate with a compile plus test
  intent lines; specs, docs and the one build + suite run happen once the surface stops moving.
- **Fewest cycles, best method.** Take the cheapest route that still yields the evidence: batch
  edits into one compile, script mechanical sweeps, run independent work in parallel, reuse
  evidence on an unchanged tree. Count round trips, not keystrokes.
- **Every round names its slowest step and attacks it.** Merge repeats, cache the artifact or defer
  the step to the full check; a slow step that runs twice inside one round means the order was
  wrong. The target is more useful rounds per hour, not fewer keystrokes.
- **One writer per resource.** Before dispatching in parallel, name each unit's write set and the
  build/test/git/IDE resource it needs; overlap means serialize, and verification reads a tree
  nobody is writing. Sessions sharing one project lease those resources (`rem-shared-resources`).
- **A deferral leaves a record; a push carries no test debt.** Whatever is postponed gets one line -
  what, why, when - written when the need appears, in `plan.md`, `test-debt.md` or
  `knowledge-candidates.md`; a deferred test for a behaviour change is paid before the code leaves
  the machine (`rem-test-completeness` §4).
- **Write for the operator: plain and short.** Few terms, no coined shorthand ("verification run",
  not "VR"), an unfamiliar term explained once; write in whichever language carries the point best.
  Each claim says what changed, why it matters, what it affects and what comes next; about a
  screenful; detail by pointer to the artifact. Delete a line the operator can neither learn from
  nor act on. Procedure: `rem-orchestration` (*Talking to the user*).
- **Prefer events over polling.** Never block on `get_subagent_result(wait: true)`, never sleep-poll;
  read the run directory.
