# Test scope

Owned by `rem-commit-workflow`; read when the change set's scope is decided, before the run.

Scope is a two-stage decision, and both stages leave evidence: **enumerate candidates
from the module graph, then prune by symbol**.

Stage 1 — candidates, from the module dependency graph (`tools/scope.py`):

```
python <skill-dir>/tools/scope.py --root <plugin-root> [--root <source-root>] --diff [REV]
```

- The graph is the same shape as a plugin-dependency viewer, one level down: the unit is the
  **module**, an edge is a `Build.cs` dependency, and the leaves are the automation prefixes read
  out of `DEFINE_SPEC`. Never derive a prefix from a module name — one test module can host several
  prefixes, and a prefix need not repeat its module's name.
- Reach follows UBT's own propagation: a module sees the change when it — or a module on its
  public-dependency path — lists the changed module. Every candidate is printed with the path that
  reached it, so the reason is auditable instead of assumed.
- It also prints the prefixes that **cannot** reach the change. That negative half is the point of
  running it: it is what lets the scope stay narrow without guessing, and it is the evidence a
  narrowed scope is reviewed against.
- Exit code 2 means the inventory could not be built (wrong `--root`, no `Build.cs`, no changed
  file mapped). An empty candidate set is never "nothing to run".

Stage 2 — prune by symbol, then decide:

- The discriminator is **which tests exercise the changed behaviour**, not which module the
  change lives in. An additive change that only its own test consumes (a new header, type or
  function) → the module prefix. A change to an existing shared header, an exported symbol or a
  macro → the module prefix **plus the prefix of every module whose specs call the changed API** —
  search the changed names (IDE text search / find usages, never a disk scanner:
  `rem-no-disk-scanning`), map every hit to its module, and keep a candidate only while a spec file
  of that prefix appears in the hits.
- Map a hit to the prefix **declared in that spec file** (its `DEFINE_SPEC` name), never to the
  module name: one test module can host several prefixes (a `*Test` module may declare both
  `X.Struct` and `X.Common`). Pruning by module name drops the prefix that does not look like it —
  and with it the case that would have covered the change. `tools/scope.py --spec <file>` prints the
  prefix of a given spec file (plus the ready-made filter line), so the mapping is not done by eye.
- **Record the pruning**: one line per dropped candidate saying why it cannot reach the change. A
  candidate dropped without a reason is how a scope silently turns too narrow; the graph's
  unreachable list is the ready-made version of that line.
- The graph proves reachability, never usage. What it adds over a text search is the consumers a
  search cannot see: a virtual override, a delegate binding, a template instantiation, a
  macro-expanded path, or consumption through an intermediate API.
- The load-time argument is a **link** argument, not a coverage one. A signature change does not
  widen the scope — every run loads every test module, so a dependent left behind by a
  symbol-mangling change fails loudly at load time whatever the filter is (a stale dependent DLL
  shows up as `Failed to load ... GetLastError=127`), and the full build covers cross-module
  compilation either way. That says nothing about whether a spec behind the renamed symbol ran:
  narrow on coverage evidence, never on "the linker would have caught it".
- Reserve the full project prefix for a genuinely project-wide blast radius: a behaviour change in
  shared runtime code, a serialized/ABI-visible shape, or a config/macro other modules read at
  runtime.
- A change that **cannot** alter behaviour needs **no test run at all** - a pure code rename, a
  comment-only or formatting change. A documentation/comment-only edit that cannot change compiled
  tokens needs **no build** either; keep the build when it touches a header whose doc comment becomes
  tooltip/metadata (UHT/UBT processes it - that is data, not prose) or any compiled token. For a
  rename the evidence is the build plus a search showing zero stale references to the old name, and
  the review carries the two conditions a compiler does not check: every reference moved in the same
  change, and the new name does **not** already exist in those scopes (a collision silently
  re-resolves overloads, overrides or concept satisfaction).
- The exemption does not apply when the *name is data*: a reflected or serialized name (a
  `UPROPERTY`/`UFUNCTION` name, a class name assets reference), a config key, a cvar, a stat id.
  Renaming those is a behaviour change - run the scope that can reach them.
- Why the scope matters: a failure outside the change's blast radius is noise — it can block
  a clean commit and trains the reader to ignore the check.
