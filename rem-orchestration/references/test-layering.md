# Layering an existing test suite

Turning a flat suite into the layers of `rem-test-completeness` §3c is a repeatable pass:
**classify, apply, measure**. It has been run by hand on two real plugins (2026-11-14, ~280 and
~360 cases); the numbers below are from those runs. Project values - which spec is in which layer,
the core prefix string, the run commands - belong to the project's local overlay, never here.

## 1. Classify — read-only, parallel, no runs

- Split the plugin's specs into 3-4 families of roughly 80-120 cases each, by module area. One
  read-only session per family, in parallel; none builds, none runs.
- Every case gets exactly one line:
  `<layer> | <case> | <injury or -> | <the production symbol whose revert reddens it> | <the two parties, core only>`.
- **A `core` row must name both parties** (another module, a content author, a network peer). A
  classifier that cannot name one writes `module`.
- Ask for at most 8 lines of "could not decide" at the end. That list is the real output: a long
  one means a tie-break is missing, not that more agents are needed.
- Expect to correct the first pass. Recurring mistakes:
  - a fixture that builds a world, calls `BeginPlay` or flushes rendering is **cheap** - not
    content, not heavy; only RHI, audio, a local player, a server, a cook or several clients are;
  - every other `module` / `core` verdict gets checked against the layer tie-breaks, which live in
    `rem-test-completeness` §3c (*Boundaries*) - not restated here.

## 2. Apply — one writing session

- **Flags:** exactly one filter bit per spec (the engine static-asserts it). Core gets
  `EngineFilter`, the rest `ProductFilter` with a layer priority. `SmokeFilter` on a spec and
  `RunFilter Engine` as a selector are both unusable - why, and the symptom each produces, is
  `rem-commit-workflow` §*The push gate*.
- **Whole spec or split?** A spec is one layer. When the core cases are the majority, flag the
  whole spec core and let the module minority ride (they are cheap). Split only when the core
  minority is significant, because a split renames every moved case and every rename breaks a
  reference somewhere.
- **Drops and merges:** one pass applies the classifiers' verdicts. Every merge checks that the
  survivor really asserts the merged observable; survivors grow, and **the grown assertions have
  never run** - the measurement run is where they first execute.
- A spec left with zero cases is deleted, not kept as a placeholder.
- **Generate the rename map** from the before/after case names (`git show HEAD:<file>` against the
  tree). A hand-written map loses rows; a generated one is a diff.

## 3. Measure — one build, two runs

- Build once, then run the module's **all prefixes** for correctness and the core prefix string
  alone for the timing. A module's cases can sit under several prefixes; count them from the spec
  names, not from the module name (a module-scope filter that misses one prefix silently runs less).
- Record startup and execution separately. Startup dominated the core run in both plugins (37 of
  70 s, and 22 of 30 s); that ratio is why the core layer is a push gate and not a commit gate.
- Reconcile: the `It`/`LatentIt` sum of the core specs must equal the runner's `Found N` (`Describe`
  contributes no entry, so count only the cases — the mechanism is in `rem-cpp-best-practices/references/tests.md`). A mismatch is a mis-flagged spec or a deleted one that still has cases.
- A spec name must not be a **dot-prefix** of a different-layer spec's name (`X` versus `X.Content`);
  the runner appends a dot to `StartsWith:`, so `X` versus `XArray` is harmless, `X` versus
  `X.Content` is not.

## Output

- One section per plugin in the project's layer table: spec, layer, counts, and one row per case
  with its `red` symbol. That row is what turns "which cases does this diff touch" into a lookup
  instead of a search.
- The core prefix string, generated from the core spec list, never hand-edited.
- Rename-map rows for every dropped, merged or moved case.

## Cost, measured

| plugin | cases before → after | core | core run |
|---|---|---|---|
| A | 280 → 253 | 176 | 70 s (37 startup + 33 execution) |
| B | 356 → 318 | 147 | 30 s (22 startup + 8 execution) |

Roughly one read-only pass per 100 cases, one writing pass per plugin, one build and two runs to
verify. The pruning yield is modest - about 7% dropped and 5% merged - and it comes as a side
effect of the classification rather than being its purpose.
