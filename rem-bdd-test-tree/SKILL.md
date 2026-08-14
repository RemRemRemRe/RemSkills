---
name: rem-bdd-test-tree
description: >
  Generates a hierarchical BDD test case tree (mind-map style index) from UE
  automation spec files (DEFINE_SPEC / Describe / It) for test review. Use when
  the user wants to review a large test suite, needs a test case index, or asks
  for a test case tree / mind map of the specs.
metadata:
  category: meta
  trigger: manual
---

# BDD Test Case Tree Generator

Generates a hierarchical test case tree from UE BDD automation specs
(`DEFINE_SPEC` + `Describe`/`It`). The tree is a review index: every leaf
carries a `[file:line]` anchor so reviewers jump straight from the tree into
the spec source.

The generator is `tools/gen_test_tree.py` (self-contained, stdlib only, runs
with any Python 3).

## When to Use

| Situation | Action |
|-----------|--------|
| User wants to review a large test suite | Generate the tree, then do the layered review (see below) |
| User asks for a test case index / mind map / tree | Generate the tree |
| Test modules were added or renamed | Regenerate the tree |

Do NOT use for: running tests, fixing test failures, writing new tests.

## Usage

```bash
python <skill-dir>/tools/gen_test_tree.py [--root <scan-dir> ...] [--output <path>]
```

| Parameter | Default | Meaning |
|-----------|---------|---------|
| `--root` | `Plugins` and `Source` under the current directory | Directories scanned recursively for `*.spec.cpp` (repeatable; `Intermediate`, `Binaries`, `ThirdParty` are always skipped) |
| `--output` | `<project-root>/Intermediate/Test/` with a unique filename | Explicit output file path. When omitted, the file is named `test_tree_<UTC timestamp>_<random>.md` under `Intermediate/Test` |

Rules:

- Run the script **from the project root** so relative scan roots resolve.
- The default output directory is created when missing.
- Unique filenames avoid clobbering earlier generations: `<UTC timestamp>` +
  a short random suffix. Pass `--output` when a stable path is wanted
  (e.g. for a review document).
- The generator only reads files; it never modifies the project.

## What the Tree Contains

```markdown
## <Module>  (N cases)

### <SpecName>  (n cases)  `<relative/path/to/spec.cpp>`

- <Describe branch>
  - <It case name>  `<relative/path:line>`
```

Parsing notes:

- `DEFINE_SPEC` names are grouped by their top two dot-segments
  (e.g. `<Root>.<Module>`).
- Nesting is derived from indentation — specs must keep the
  `Describe`/`It` bodies indented (standard UE/Rider formatting).
- Multi-line `It(TEXT("..."))` names are supported.
- The static `It` count differs from the automation runner's test count:
  the runner also counts `Describe` nodes as test entries
  (verified 2026-08, UE 5.8 runner).

## Layered Review Workflow (why the tree exists)

Reviewing hundreds of cases one by one does not scale. Layer it:

| Layer | What to look at | Cost |
|-------|-----------------|------|
| L1 structure | The tree only: does every semantic branch exist under each Describe? Missing or duplicated branches jump out. | minutes |
| L2 gaps | Cross-reference the tree against the public API inventory — hunt for what is NOT tested, not for what is. | minutes |
| L3 deep read (~20%) | Only core semantic branches (state machines, gating logic, lifecycle, generators). | hours |
| L4 skim | Remaining cases: verify each has real assertions, not placeholders. | minutes |
| L5 spot check | Random sample of N cases read end to end; optionally mutation-test the code under test. | on demand |

Boilerplate categories (default-value checks, reflection round-trips,
constant checks) can be skipped wholesale — their quality is guaranteed by
pattern, not by reading.

## Checklist

Before generating or handing over a tree:

- [ ] Script runs from the project root; scan roots resolve
- [ ] Output lands in `Intermediate/Test/` by default, or the caller passed `--output` explicitly
- [ ] Generated filename is unique (timestamp + random suffix) unless `--output` was given
- [ ] Tree leaves carry `[file:line]` anchors that open the exact spec line
- [ ] The tree header notes it is auto-generated and how to regenerate it
- [ ] Review follows the layered workflow (L1 structure first, L3 only for core branches)
