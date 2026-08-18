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
(`rem-cpp-best-practices` §16 and its `references/tests.md`).

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
   `rem-cpp-best-practices` `references/tests.md` §5).
4. **No structural gaps** — layered review L1/L2 (`rem-bdd-test-tree`) clean:
   L1 structure (every semantic branch present), L2 cross-reference against the
   API inventory — hunt for what is **not** tested.
5. **Core-logic mutation spot check** — flip a condition or assertion in the
   code under test (or in the case); the suite must go red. Staying green means
   the case does not exercise the path.

Optional evidence: UE code-coverage data. Supporting evidence only — never a
gate (UE coverage support is limited).

### Judgment notes

- **Runner vs. tree counts** — the automation runner counts `Describe` nodes as
  test entries; judge "one case per behavior" from the tree's `It` count
  (`rem-bdd-test-tree`), not the runner's total.
- **Boilerplate categories** — default-value checks, reflection round-trips,
  and constant checks are guaranteed by pattern; skip deep review of them,
  not the tests themselves.
- **Order of writing is free** — the gate checks completeness, not chronology.
  TDD (red-green-refactor) is optional and recommended for new features.

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
| Spec/test-struct/module templates, build & run commands, pitfall catalog | `rem-cpp-best-practices` `references/tests.md` |
| Test tree generation + layered review | `rem-bdd-test-tree` |
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
- [ ] Skip used? Reason stated
- [ ] Missing cases written in BDD spec style (`rem-cpp-best-practices` §16, `references/tests.md`)

## Cross-references

- `rem-commit-workflow` — the gate that calls this skill
- `rem-bdd-test-tree` — test tree generation + layered review
- `rem-cpp-best-practices` — §16 spec conventions; `references/tests.md` templates & pitfalls
- `rem-write-better-skill` — skill-writing conventions
