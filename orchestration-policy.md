# Orchestration policy (main session)

Hard rules, always in force. The procedure behind them - delegation, the write-code / freeze /
push-gate cadence, run directories, waiting - is the `rem-orchestration` skill.

- **Disk scanning is banned** (`rem-no-disk-scanning`): search only through the project's MCP server; if
  it is unavailable, stop and tell the user - never substitute a scanner.
- **Delegate execution, keep decisions.** Briefs are self-contained, run in the background unless this
  turn needs the result, and always carry an explicit `subagent_type`; the main session owns the
  decisions and the ledger. `max_turns` is a per-call kill switch, not a profile setting.
- **Nothing scratch in the repository**: the OS temp dir for scratch, the run directory for a run's own
  output.
- **A round writes code and cases, then compiles - nothing else runs.** No suite, no single spec, no
  editor or PIE session; the compile is a round's only execution evidence. The freeze takes the one full
  build the commit cites, the push gate the one suite run (`rem-test-completeness` §3c).
- **A submodule commit stays in its submodule until the pin is needed**: the `m` the parent shows is the
  expected state, and the bump is one parent commit at the push gate - unless a cross-repository change
  needs the new commit for its caller half (`rem-orchestration`, *Commits across a submodule boundary*).
- **Fewest cycles, best method**: batch edits into one compile, script mechanical sweeps, parallelize
  independent work, reuse evidence on an unchanged tree. Count round trips, not keystrokes.
- **Every round names its slowest step and attacks it** - merge, cache or defer it; a slow step run twice
  in one round means the order was wrong.
- **One writer per resource**: name each unit's write set and the build/test/git/IDE lease before
  dispatching; overlap serializes, and verification reads a tree nobody writes
  (`rem-shared-resources`).
- **Nothing defers as a description**: a behaviour with no case gets one in the round that changes it,
  and what remains lives in the two records (`rem-orchestration`, *Two records*) - an unrun case, a
  manual check. Externally visible behaviour and bug fixes never leave the commit without their case.
- **Write for the operator, plain and short**: what changed, why it matters, what it affects, what comes
  next; about a screenful; detail by pointer to the artifact. Delete a line the operator can neither
  learn from nor act on.
- **Prefer events over polling; `sleep` is capped at 15 s** and never replaces reading the run directory.
- **A silent unit is checked** about ten minutes in, then every ten minutes: name the slow step from its
  run directory and child-session timestamps before blaming the model. Committing, folding un-pushed
  commits and staging by exact path are a script here, not a delegated unit.
