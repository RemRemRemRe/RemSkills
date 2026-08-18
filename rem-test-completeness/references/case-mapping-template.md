# Change-to-Case Mapping Template

Fill one row per changed/new behavior or fixed bug while reviewing the diff
(`rem-test-completeness` §1). "Action" is one of `new` / `update` / `none`
(`none` only when an existing case already exercises the behavior — name it in
"Existing case"). "Case anchor" is the `It` name or `<file:line>` you can point
a reviewer at.

| # | Diff item | Behavior / public API | Existing case? | Action | Case anchor |
|---|-----------|----------------------|----------------|--------|-------------|
| 1 |           |                       | yes / no       | new / update / none |           |

## Worked Example (placeholder types)

Context: `Rem::Foo::TBar` is a runtime container; the change set adds an
`Emplace` overload with a value category and fixes an off-by-one in `RemoveIf`.

| # | Diff item | Behavior / public API | Existing case? | Action | Case anchor |
|---|-----------|----------------------|----------------|--------|-------------|
| 1 | `TBar::Emplace` new rvalue overload | Emplace in-place constructs from rvalue | no | new | `Rem.Foo.TBar.Emplace` / `It("in-place constructs from an rvalue")` |
| 2 | `TBar::RemoveIf` predicate loop bound | RemoveIf removes every matching element (off-by-one fix) | yes — `RemoveIf` removes first match only | update | `It("removes all matching elements, not just the first")` |
| 3 | `TBar::Num` returns `int32` (was `int16`) | `Num` return type widened | yes — existing `Num` smoke case | none | `It("returns the element count")` |

Notes from the review:

- Row 1 is the only genuinely new behavior → one new spec case.
- Row 2 is a bug fix → regression case bound to the fix; spot-check by
  temporarily reverting the loop bound (the case must fail).
- Row 3 changed no observable behavior → existing case already executes the
  path; mapped, not re-written.

Result: the change set passes criteria 1–5 only after row 1 and row 2 cases
exist and pass; row 3 is a named no-op.
