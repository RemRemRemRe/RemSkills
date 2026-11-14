# Orchestration policy (main session)

Hard rules, always in force. The procedure behind them - delegation, the write-code / freeze /
push-gate sequence, run directories, waiting - lives in the `rem-orchestration` skill; load it when
planning, delegating or sequencing work.

- **Disk scanning is banned** (`rem-no-disk-scanning`). Search only through the project's MCP
  server; if it is unavailable, stop and tell the user - never substitute a scanner.
- **Delegate execution, keep decisions.** Briefs are self-contained, run in the background unless
  this turn needs the result, and always pass an explicit `subagent_type` (the built-in names are
  disabled); the main session owns the decisions and the ledger. `max_turns` is a per-call kill
  switch, not a profile setting.
- **Nothing scratch in the repository.** Temp files and throwaway clones go to the OS temp dir, a
  run's own output to its run directory (`rem-temp-files`).
- **Iteration writes the case and runs nothing.** A round edits the code and writes or updates the
  case for the behaviour it changes, in the same commit, then compiles - no suite, no single spec, no
  `Automation RunTests` invocation, no editor or PIE session opened to watch a behaviour. A compile is
  the only execution evidence a round may produce. When the surface settles, the freeze reviews the
  diff, sweeps the docs and takes one full build; that build is the commit's evidence. The push gate
  is its own operator-triggered session: one build, one run of the core layer plus every prefix the
  range touches, and a report that lists every recorded known red it met (`rem-test-completeness`
  §3c).
- **Fewest cycles, best method.** Take the cheapest route that still yields the evidence: batch
  edits into one compile, script mechanical sweeps, run independent work in parallel, reuse
  evidence on an unchanged tree. Count round trips, not keystrokes.
- **Every round names its slowest step and attacks it.** Merge repeats, cache the artifact or defer
  the step to the freeze or to the push gate; a slow step that runs twice inside one round means the
  order was wrong. The target is more useful rounds per hour, not fewer keystrokes.
- **One writer per resource.** Before dispatching in parallel, name each unit's write set and the
  build/test/git/IDE resource it needs; overlap means serialize, and verification reads a tree
  nobody is writing. Sessions sharing one project lease those resources (`rem-shared-resources`).
- **Nothing defers as a description.** A behaviour with no case gets its case in the round that
  changes it; a noted "we will test this later" is stale before anyone reads it. Two records carry
  what is left (`rem-orchestration`, *Two records*): a case that exists and has never run is one row
  naming why and the tier that runs it next, and a behaviour no headless case can reach is one row of
  the manual-check record. Externally visible behaviour and bug fixes never leave the commit without
  their case (`rem-test-completeness` §4).
- **Write for the operator: plain and short.** Few terms, no coined shorthand ("verification run",
  not "VR"), an unfamiliar term explained once; write in whichever language carries the point best.
  Each claim says what changed, why it matters, what it affects and what comes next; about a
  screenful; detail by pointer to the artifact. Delete a line the operator can neither learn from
  nor act on. Procedure: `rem-orchestration` (*Talking to the user*).
- **Prefer events over polling; `sleep` is the last resort and capped at 15 s.** A background run or an
  external process signals its own completion - wait for that event, or give the blocking call a
  timeout that covers it. Never block on `get_subagent_result(wait: true)` as a wait. Reach for
  `sleep` only when there is no event to wait on at all: then one wait of at most 15 seconds,
  repeated only as many times as the plan states, and never instead of reading the run directory.
