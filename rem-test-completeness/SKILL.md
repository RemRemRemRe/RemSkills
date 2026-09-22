---
name: rem-test-completeness
description: >
  Decide whether a change set's automation tests are complete before committing,
  and guide writing the missing cases. Covers change-to-case mapping (diff ->
  changed behavior -> one spec case per behavior), the five-point completeness
  criteria, regression-first for bug fixes, mutation spot checks on core logic,
  and reuse of the layered review from rem-bdd-test-tree. Use when a commit
  gate asks whether a change's tests are complete, when writing tests for a
  change, or when judging whether existing tests cover a change.
metadata:
  category: meta
  trigger: manual
---

# Test Completeness

This skill decides whether the tests for a change set are complete enough to
commit — and, if not, what to write. It is the methodology behind the
**test completeness gate** in `rem-commit-workflow`. It does not build or run
anything (that is the commit workflow's job) and it does not generate review
indexes (that is `rem-bdd-test-tree`).

## When to Use

| Situation | Action |
|-----------|--------|
| The commit gate asks whether this change's tests are complete | Run the five-point criteria (see below) |
| Tests are missing for a change | Change-to-case mapping, then write in spec style per `rem-cpp-best-practices` §16 |
| Reviewing whether existing tests cover a change | Five-point criteria + layered review L1/L2 (`rem-bdd-test-tree`) |

Do NOT use for: running tests or builds (`rem-commit-workflow`), generating
test trees (`rem-bdd-test-tree`), spec style / module placement / build commands
(`rem-cpp-best-practices/references/tests.md` §16).

**Iteration vs. freeze.** The sequence is owned by `rem-orchestration`; this gate
runs once, at the freeze point. Iteration records intent lines
(`<run-dir>/test-intent.md`) instead of specs; a bug fix proves its regression case
by reverting the fix (§2).

## The Gate Contract

Called by `rem-commit-workflow` between commit hygiene and build, **once per
change set** (not per split commit):

```
Change set ready
├─ affects behavior? ── No ──► skip, state the reason
└─ Yes
   ├─ 1. Inventory changed behaviors (diff -> public API / behavior)
   ├─ 2. Map each behavior to a spec case (references/case-mapping-template.md)
   ├─ 3. Judge the five-point criteria
   ├─ 4. Write missing cases (BDD spec style, see §5)
   └─ 5. Re-check criteria -> gate passes, then build
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
gate (UE coverage support is limited).

### Judgment notes

- **Runner vs. tree counts** — judge "one case per behavior" from the tree's
  `It` count (`rem-bdd-test-tree`), not the runner's total (why the counts
  differ: `rem-cpp-best-practices/references/tests.md` §4).
- **Boilerplate categories** — skip deep review of them, not the tests
  themselves (category list and rationale: `rem-bdd-test-tree`).
- **Order of writing is free** — the gate checks completeness, not chronology.
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

## 4. Skip Conditions (explicit exceptions)

The gate is mandatory only for **behavior-affecting** changes (logic in
`New` / `Changed` / `Fixed` / `Improvement` commits). Skip with a stated reason
when the change is:

- A pure refactor with no semantic change (behavior preserved),
- Docs, formatting, naming, or config-only,
- Already covered by existing cases (name the cases).

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
- [ ] Skip used? Reason stated
- [ ] Missing cases written in BDD spec style (`rem-cpp-best-practices/references/tests.md` §16)

## Cross-references

- `rem-commit-workflow` — the gate that calls this skill; owns the scope (`§Test scope`) that decides whether a case runs at all
- `rem-bdd-test-tree` — test tree generation + layered review
- `rem-cpp-best-practices/references/tests.md` — §16 spec conventions; templates & pitfalls
- `rem-write-better-skill` — skill-writing conventions
