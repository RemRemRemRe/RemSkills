---
name: rem-test-completeness
description: >
  Decide whether a change set's automation tests are complete before the push gate
  runs the suite, and guide writing the missing cases. Covers change-to-case
  mapping (diff ->
  changed behavior -> one spec case per behavior), the five-point completeness
  criteria, regression-first for bug fixes, mutation spot checks on core logic,
  and reuse of the layered review from rem-bdd-test-tree. Use when a test
  session asks whether a change's tests are complete, when writing tests for a
  change, or when judging whether existing tests cover a change.
metadata:
  category: meta
  trigger: manual
---

# Test Completeness

This skill decides whether the tests for a change set are complete enough to
count — and, if not, what to write. It is the methodology behind the push gate
in `rem-commit-workflow`. It does not build or run anything (that is the gate's
job) and it does not generate review indexes (that is `rem-bdd-test-tree`).

## When to Use

| Situation | Action |
|-----------|--------|
| The push gate asks whether this change's tests are complete | Run the five-point criteria (see below) |
| Tests are missing for a change | Change-to-case mapping, then write in spec style per `rem-cpp-best-practices` §16 |
| Reviewing whether existing tests cover a change | Five-point criteria + layered review L1/L2 (`rem-bdd-test-tree`) |

Do NOT use for: running tests or builds (`rem-commit-workflow`), generating
test trees (`rem-bdd-test-tree`), spec style / module placement / build commands
(`rem-cpp-best-practices/references/tests.md` §16).

**When this check runs.** In the round that writes the cases, and again at the push gate that runs
them; the sequence is owned by `rem-orchestration`. Iteration writes the cases with the code and runs
nothing, records intent in `<run-dir>/test-intent.md`, and keeps every never-executed case in the
plugin's unrun record (`<cwd>/.agents/test-debt/`, `rem-orchestration` *Two records*). A bug fix
proves its regression case by reverting the fix (§2) wherever that red is visible without a run;
otherwise it says so in the unrun record and marks the case `red not proven`.

Write cases for a settled surface only: while the interface is still being shaped, the case waits -
a case written against a moving interface gets rewritten, not reused.

## The Check Contract

Called by the push gate before its single build + run, **once per
change set** (not per split commit):

```
Change set ready
├─ affects behavior? ── No ──► skip, state the reason
└─ Yes
   ├─ 1. Inventory changed behaviors (diff -> public API / behavior)
   ├─ 2. Map each behavior to a spec case (references/case-mapping-template.md)
   ├─ 3. Judge the five-point criteria
   ├─ 4. Write missing cases (BDD spec style, see §5)
   └─ 5. Re-check criteria -> the check passes, then the session builds
```

Tests must be complete **before** the build: the build and the test run happen
once, not iterated after late test fixes.

## 1. Change-to-Case Mapping

Go through the diff and list every item whose **behavior** changed:

| Diff item | Counts as a behavior change |
|-----------|----------------------------|
| Public API semantics changed (return values, edge cases, defaults, error paths) | Yes |
| New public API added | Yes |
| Bug fixed | Yes |
| State machine / gating / lifecycle logic touched | Yes |
| Rename with no semantic change, formatting, docs, config values | No — covered by compile or review |

For each behavior change decide: covered by an existing case (which one?),
needs a new case, or needs an existing case updated. Fill the mapping table —
template and worked example: `references/case-mapping-template.md`.

A behavior is only covered if a case that exercises it **runs**. Which prefixes
must carry those cases is the scope question, owned by `rem-commit-workflow`
§Test scope: enumerate the candidate prefixes (`rem-commit-workflow/tools/scope.py`)
and prune them by searching the changed names. A behavior whose only spec sits
in a prefix outside the run's scope is not covered, however green the run is.

## 2. Regression-First for Bug Fixes

A fixed bug gets a regression case **bound to the fix**:

- When writing the fix: write/identify the failing case first (red), apply the
  fix, case goes green.
- When the fix already exists (verify-before-commit): spot-check core logic by
  temporarily reverting the fix — the regression case must fail. Full revert
  checks are optional; one representative check per core fix is enough.

## 3. The Five-Point Completeness Criteria

1. **Executed coverage** — every changed behavior / public API has ≥1 spec case
   that actually reaches the changed code path. A case existing under a similar
   name is not enough; it must exercise the change.
2. **Regression binding** — every fixed bug has a regression case bound to the
   fix (§2).
3. **No placeholder assertions** — no `TestTrue(TEXT("..."), true)`-style
   assertions; assert a real condition (pitfall list:
   `rem-cpp-best-practices/references/tests.md` §5).
4. **No structural gaps** — layered review L1/L2 (`rem-bdd-test-tree`) clean.
5. **Core-logic mutation spot check** — flip a condition or assertion in the
   code under test (or in the case); the suite must go red. Staying green means
   the case does not exercise the path.

Optional evidence: UE code-coverage data. Supporting evidence only — never a
check (UE coverage support is limited).

### Judgment notes

- **Runner vs. tree counts** — judge "one case per behavior" from the tree's
  `It` count (`rem-bdd-test-tree`), not the runner's total (why the counts
  differ: `rem-cpp-best-practices/references/tests.md` §4).
- **Boilerplate categories** — skip deep review of them, not the tests
  themselves (category list and rationale: `rem-bdd-test-tree`).
- **Order of writing is free** — the check reads completeness, not chronology.
  TDD (red-green-refactor) is optional and recommended for new features.

## 3b. Self-Validating Cases

Authoring rules that keep a case able to fail. A case that cannot go red is not
evidence, however green it looks (the review side asks the same question per
case).

- **An assertion nobody can falsify is not a test.** For every case ask: which
  one-line regression makes this line fail? No answer means the case measures
  nothing — rewrite the assertion or drop the case.
- **A measuring instrument proves itself first.** Before asserting "zero
  reports", produce one report inside the same scope and assert "exactly one";
  only then assert the zero. A broken counter turns every zero-assertion into a
  false green — the baseline is what proves the counter counts. Instance (verified
  2026-09): two cases asserting "no callback fires" stayed green after the
  listener-registration line this very change was about had been deleted (the
  count was 0 either way); driving one same-parameter callback through an external
  removal path first (assert exactly one) and then through the path under test
  (assert still one) made both mutants — registration deleted, removal broken — go
  red.
- **A reworded message must fail loudly.** A counter that filters by message
  text keys on a string that occurs **once** in the tree, so a rename breaks the
  case instead of silently matching nothing. A filter string shared with
  production code turns a rename into a silent pass.
- **A case owns its keys.** When a case registers into a shared registry, do not
  reuse a key a production registration holds for the whole process — that
  registration injects its own report into the case's scope. Use a test-owned
  key, and record any dependency on a production entry declining.
- **Check a helper's own test before using the helper.** A `contains`-style
  assertion passes on a broken implementation; if the helper's own test is that
  weak, strengthen it in the same change, then use it.
- **Assert the behaviour, not the content's composition** (verified 2026-11). A case that pins "the
  selected row carries exactly one handler" goes red the moment content adds a second one, though
  nothing in the code changed - and the fix is always to widen the expectation, which trains everyone
  to loosen assertions. Assert what the case is about (the row was selected, the handler it needs is
  there and configured), and leave counts to the content owner's own check.
- **A Verbose expectation cannot be pinned with `AddExpectedMessage`** (verified 2026-11, this
  engine): the matcher counts only Warning/Error records, so an expectation of a Verbose line fails
  forever while the line is in fact logged. Assert the observable effect instead - the query ran 8
  times, the counter stayed at 0 - rather than the line that announces it.
- **An expected-error matcher is a regular expression, and `Occurrences = 0`
  means "at least one"** (verified 2026-10). `AddExpectedError` takes a pattern,
  so a condition text carrying `(` or `&&` never matches — use
  `AddExpectedErrorPlain` with the call-site condition text to pin an ensure.
  `Occurrences` counts a minimum: `0` fails the case when nothing matches, so it
  cannot express "any number of these".

### Assertions that pass for the wrong reason (verified 2026-10)

Five shapes seen in one review; each reads green and measures nothing:

- **The production predicate as the oracle** — asserting a round trip by calling
  the production `ShouldReconcile` / `Matches` on the result. Assert the fields
  explicitly; keep the predicate as an extra.
- **A latch or guard earlier than the branch under test** — a second event
  returns at the latch, so the guard after it never runs. Drive the branch on a
  fresh object, or reset the latch.
- **A fixture that filters away the only subject** — a same-team victim is
  dropped by the hostile filter, so the "zero victims" event passes as if it
  were the positive path. Assert the positive (damage, victim count) as well.
- **A control that cannot discriminate the gate** — an empty tag matches no
  handler anyway; the case stays green with the `IsValid` guard deleted. Use a
  value that would match if the gate were absent, plus the positive control.
- **A re-run that starts in the terminal state** — "no second event" is
  guaranteed if the state already says stopped. Assert the first transition's
  values, or re-run from a state that could fire.

## 3c. Layers, and what "full" means

A case's layer is decided by what it costs to run and by who reads what it asserts - not by how
important it feels. Both questions get an answer:

- **core** - cheap (no authored asset, no config, no level, no RHI/audio/player) **and** a contract two
  parties must agree on: another module, a content author, or a network peer. The test is one sentence:
  *if this changed silently, who would be wrong without an error?* Cannot name the other party? Then it
  is not core.
- **module** - cheap, but it pins the owning module's own behaviour or wiring. It runs when that module
  is touched.
- **content** - it reads an asset, an `.ini` entry or a level, or it pins what an authored field means.
  It runs when the module or the content changes.
- **heavy** - it needs a non-default environment (RHI, audio device, local player, dedicated server,
  cook, several clients, stress). It runs only in a session that has that environment. Do not write a
  heavy case before the harness for it exists; a case nobody can execute is worse than a written
  procedure.

Boundaries that keep coming up: an exported symbol with no nameable caller is **module** (the signature
is the compiler's job); a **silence** assertion ("nothing is sent") is **core**, because the other
party parses the absence exactly as it parses the presence; **tag timing** is a contract (the
presentation layer reacts to which tag exists when) while **internal counters** are not; a field a
designer fills in (`EditAnywhere`) carries a contract with that designer.

**"Full" names four different runs**, not one:

| tier | runs | when |
|---|---|---|
| round | nothing - a compile is the round's evidence | every round |
| commit | the build | every commit |
| push gate | core, plus every prefix the range touches | before a push |
| release | every case | before a release, and on a schedule |

The push gate is the normal one. A layer that runs only when someone remembers rots, so the release
tier needs a schedule rather than an intention. Which spec is in which layer - and the prefix string
the gate runs - are project data (`rem-orchestration/local/test-layers.md`), never this skill.

**One spec declares one layer.** The automation filter is per spec and the engine asserts exactly one
filter bit, so a spec that mixes layers is split and a case whose layer changed moves to that layer's
spec. Never put `EAutomationTestFlags::SmokeFilter` on a spec: the editor runs every smoke test at
startup, a spec enqueues a latent command, and the framework's assertion kills **every editor start**.
Use `EngineFilter` for the core layer and `ProductFilter` for the rest.

## 4. Skip Conditions, Unrun Cases and Manual Checks

The check is mandatory only for **behavior-affecting** changes (logic in
`New` / `Changed` / `Fixed` / `Improvement` commits). Skip with a stated reason
when the change is:

- A pure refactor with no semantic change (behavior preserved),
- Docs, formatting, naming, or config-only,
- Already covered by existing cases (name the cases).

**Two classes may not leave the commit without their case:** externally visible behaviour (serialized
or ABI-visible shapes, save data, network or API contracts) and bug fixes (their regression case).
Both are written in the commit's own round.

Everything else is written in the round too - nothing defers by description. What can remain unproven
is a case that never executed: it becomes one row in the plugin's *unrun cases* record
(`rem-orchestration`, *Two records*) naming why and which tier runs it next. A behaviour no headless
case can reach goes to the *manual checks* record with the procedure that checks it.

**A push needs a green run at the push gate for its range** - the core layer plus the prefixes the
range touches (§3c) - and the run must list every recorded known red it met. An older full run is not
evidence for a newer tree.

## 5. Test Style & Placement (single-ownership pointers)

| Concern | Owner |
|---------|-------|
| BDD spec style, test module placement, dependency direction | `rem-cpp-best-practices` §16 |
| Spec/test-struct/module templates, build & run commands, pitfall catalog | `rem-cpp-best-practices/references/tests.md` |
| Test tree generation + layered review | `rem-bdd-test-tree` |
| Which prefixes can reach a change (candidate scope before pruning) | `rem-commit-workflow` §Test scope + `rem-commit-workflow/tools/scope.py` |
| Building & running the suite headless | `rem-commit-workflow` |

Rules live in exactly one skill; this skill references, never restates them
(`rem-write-better-skill` §11).

## Checklist

Before declaring a change set complete:

- [ ] Change set inventoried: every changed/new behavior and fixed bug listed
- [ ] Mapping table filled (`references/case-mapping-template.md`)
- [ ] Criterion 1: every behavior has a case that actually executes it
- [ ] Criterion 2: every bug fix has a bound regression case (revert spot-check on core logic)
- [ ] Criterion 3: no placeholder assertions
- [ ] Criterion 4: layered review L1/L2 clean (`rem-bdd-test-tree`)
- [ ] Criterion 5: mutation spot check goes red on core logic
- [ ] Cases are self-validating: falsifiable assertion, a baseline before any zero assertion, a case-owned registry key, and an adequate test for any helper used (§3b)
- [ ] Every case that has never executed is one row in the unrun record, with the tier that runs it next
- [ ] Missing cases written in BDD spec style (`rem-cpp-best-practices/references/tests.md` §16)

## Cross-references

- `rem-commit-workflow` — the push gate that calls this skill; owns the scope (`§Test scope`) that decides whether a case runs at all
- `rem-bdd-test-tree` — test tree generation + layered review
- `rem-cpp-best-practices/references/tests.md` — §16 spec conventions; templates & pitfalls
- `rem-write-better-skill` — skill-writing conventions
