---
name: rem-ranges-transrangers
description: >
  Write functional pipeline code using Rem::Ranges, transrangers, and RemStd::bind_back.
  Covers creating rangers from arrays, filtering, transforming, consuming (ForEach, ToArray,
  FirstElement), grouping, and the C1060 workaround (REM_RANGES_FOREACH). Use whenever the
  user writes or reads transrangers-based pipeline code in the Rem project.
  Last verified: 2026-07.
metadata:
  category: meta
  trigger: manual
---

# Rem Ranges / Transrangers — Functional Pipeline Usage

## Architecture

```
transrangers.hpp (3rd-party)    ← core lazy-evaluation ranger primitives
    ↓
RemRangesStatics.inl             ← UE-friendly wrappers (ForEach, ToArray, ArrayView, etc.)
    ↓
RemStd.inl                       ← bind_back for partial application
    ↓
Application code                 ← chains filter / transform / concat via Rem::Ranges / transrangers
```

---

## Core Concepts

### Push-Based (vs `std::ranges` Pull-Based)

`std::ranges` is **pull-based**: an outer loop pulls values from the view pipeline and feeds them to the consumer. End-of-range checks happen at every level.

Transrangers is **push-based**: control flow is **internalized** inside the ranger. The ranger drives iteration by pushing cursors to a **consumption function** (`dst`). This eliminates redundant end-of-range checks and enables aggressive compiler optimization (frequently producing identical assembly to handwritten loops).

### Cursor Passing (Not Value Passing)

Rangers pass **cursors** (lightweight iterator-like objects with a dereference operation) to the consumption function, not raw values. This enables operations like `unique` that need access to previous elements.

### Consumption Function Contract

```cpp
rgr(dst);
```

- `rgr(dst)` feeds cursors to `dst` one by one.
- `dst(p)` returning `true` → **continue** iterating.
- `dst(p)` returning `false` → **stop** immediately (early exit).
- `rgr(dst)` returns `true` if the range was fully consumed, `false` if `dst` stopped early (there *may* be remaining elements).

### Early Exit is Built-In

Because the entire pipeline respects the consumption function's return value, early exit propagates through all layers:

```
FirstElement  →  take<1> returns false after 1st element consumed
  ↓
filter        →  pred true → dst(p) returns false → filter returns false
  ↓
transform     →  rgr returns false → transform returns false
  ↓
ranger_join   →  sub-ranger returns false → join returns false
  ↓
source        →  source ranger stops iterating
```

**`FirstElement` achieves early exit via `take<1>`**: once the first matching element is consumed, `take<1>`'s inner lambda returns `false`, which stops the filter from searching further, which stops the source ranger entirely. This means `FirstElement(filter(...))` only traverses until the first match — it does NOT scan the entire range.

**`filter` plays a key role in the exit chain**: when the predicate passes (e.g., a validity check returns true for a non-null pointer), `filter` calls `dst(p)` which leads up to `take<1>`. When `take<1>`'s consumption is satisfied, the `false` return propagates back through `filter`, which itself returns `false` to its source, stopping all iteration. However, when the predicate fails (e.g., `nullptr`), `filter` internally returns `true` (continue), so skipped elements do NOT trigger early exit — they are simply passed over.

**`ForEach` does NOT provide early exit**: `ForEach`'s consumption function always returns `true` (`return *Cursor;` with potentially non-bool cursor types), so it always exhausts the range. Use `FirstElement` or call the ranger directly with a custom consumption function when early exit is needed.

### Direct Ranger Invocation (Custom Early Exit)

When you need fine-grained early exit, invoke the ranger directly with a consumption function that returns `false` to stop:

```cpp
FBaz* Result = nullptr;
Ranger([&](auto p) {
    if (MatchesCondition(*p)) {
        Result = GetPointer(*p);
        return false; // STOP — found what we need
    }
    return true; // continue searching
});
return Result;
```

---

## Includes

```cpp
#include "transrangers.hpp"         // transrangers::all, filter, transform, concat, zip, take, ranger_join
#include "RemRangesStatics.inl"     // Rem::Ranges::ForEach, ToArray, ArrayView, TakeN, FirstElement, NthElement
#include "RemRangesMacro.h"         // REM_RANGES_FOREACH — C1060 workaround
#include "RemStd.inl"               // RemStd::bind_back — partial application
#include "RemCastFn.h"              // Rem::Cast<T> — cast functor for transrangers::transform (avoids Cast overload ambiguity)
```

---

## API Reference

The entry points, ranger factories and terminal operations, with signatures. Full tables: `references/api.md`.

---

## Canonical Pipeline Pattern

Build pipelines by composing `transrangers::filter` / `transform` / `take` / `join` and consuming with a `Rem::Ranges` terminal (`ForEach`, `ToArray`, `FirstElement`). Use `RemStd::bind_back` to adapt callables, and `REM_RANGES_FOREACH` where the C1060 workaround applies.

The worked patterns — every composition shape with its full code — are in `references/canonical-pipeline.md`.

---

## Anti-Patterns

| Don't | Do | Why |
|---|---|---|
| Mapper returns `Ranges::ArrayView(...)` in a `ranger_join` pipeline | Mapper returns raw `const TArray<T>&` | `ranger_join` calls `all()` on the element — if it's already a ranger, you get nested `all_copy<all_copy<...>>` which has no `begin()` |
| `ranger_join(transform(..., ranger_join(transform(...))))` — double flattening | Eagerly pre-collect into TArray, then `transrangers::all(MoveTemp(...))` | C1060 heap exhaustion in DebugGame |
| Raw for-each loops in pipeline consumer code | `Rem::Ranges::ForEach` or `REM_RANGES_FOREACH` or `ToArray` | Loses functional composition |
| `transrangers::all(TMap)` | Convert TMap to TArray of key-value pairs first | TMap not supported as a transrangers range |
| Lambda-heavy mapper logic inline in `transform()` | Extract as named function, use `RemStd::bind_back` for partial application | Improves readability, reduces template bloat. Exception: single-statement lambdas that call `Emplace` / `Add` are acceptable in C1060-safe side-effect pipelines. |
| Lambda just to access a member: `[](T& x) -> MemberType& { return x.Member; }` | `std::mem_fn(&T::Member)` | Standard library utility: creates callable from pointer-to-data-member. Eliminates 3-line boilerplate lambdas. Include `<functional>`. |
| Single-arg `Ranges::ToArray(Ranger)` with reference element type | Two-arg `Ranges::ToArray(OutArray, Ranger)` | `ranger_join` yields `ranger_element_t = T&`. `TArray<T&>` is illegal. Two-arg version uses `OutArray`'s already-correct type. |
| Overloaded template function as `transform` callable (e.g., `Cast<T>`) | `Rem::Cast<T>` from `RemCastFn.h` (functor struct + variable template) | Function template overload resolution fails without concrete argument types. Functor struct defers deduction to call site. |
| Mapper returns ranger (e.g. `Ranges::ArrayView(...)`) in a `ranger_join` | Mapper returns raw range by value (`TArray`) or by reference (`const TArray&`) | `ranger_join` uses `all_adaption` which wraps elements with `transrangers::all()` — not designed for nested rangers. See "join (identity_adaption)" for the rare case where mapper returns a ranger. |

### `std::mem_fn` — Member Access Without Lambdas

Replace trivial "return `x.Member`" or "return `x->Method()`" lambdas with `std::mem_fn`:

```cpp
#include <functional>

// Data member access:
// Before: 3-line lambda
auto GetSubArray = [](OuterType& Outer) -> TArray<InnerType>&
{
    return Outer.InnerArray;
};
// After:
auto GetSubArray = std::mem_fn(&OuterType::InnerArray);

// Member function access:
// Before: 3-line lambda
// UMovieSceneTrack is a UE MovieScene API type (see MovieSceneTrack.h)
auto GetAllSections = [](const UMovieSceneTrack* Track) -> const TArray<UMovieSceneSection*>&
{
    return Track->GetAllSections();
};
// After:
auto GetAllSections = std::mem_fn(&UMovieSceneTrack::GetAllSections);

// Or inline directly:
transrangers::transform(std::mem_fn(&FBaz::SomeMember),
    Rem::Ranges::ArrayView(Container->SomeData))
```

`std::mem_fn(ptr_to_member)` returns a callable `fn` such that `fn(obj)` accesses `obj.*ptr_to_member`. Works for both data members and member functions. Compatible with `transrangers::transform` since it uses `fn(*cursor)` call syntax.

**Caveat**: if the member function has overloads (e.g., const + non-const `GetAllSections`), `&Class::Method` is ambiguous. Use a lambda or explicit `static_cast` in that case.

---

## Checklist

Before committing code that uses transrangers pipelines:

- [ ] Source data wrapped via `Rem::Ranges::ArrayView` / `ConstArrayView` or `transrangers::all()`
- [ ] Pipeline composed right-to-left: inner transforms/filters first
- [ ] `transrangers::transform(fn, ranger)` — `fn` is first argument (not last)
- [ ] `ranger_join` mapper returns a raw range (`const TArray<T>&`, `TArrayView<T>`, or `TArray<T>` by value), not a ranger
- [ ] For reference-element rangers (e.g. after `ranger_join`), use two-arg `ToArray(OutArray, Ranger)` — not single-arg `ToArray(Ranger)`
- [ ] Functions declared as named functions with `RemStd::bind_back` for context binding (avoids inline lambda template bloat)
- [ ] `bind_back` parameter order: element parameter first, bound context parameters after
- [ ] Consumed via `Rem::Ranges::ToArray` / `ForEach` / `FirstElement`
- [ ] Use `FirstElement` / `NthElement` when early exit is desired (not `ForEach`, which always exhausts)
- [ ] No `transrangers::all(TMap)` — convert to key-value pair array first
- [ ] No double `ranger_join(ranger_join(...))` — eager pre-collect instead (C1060 risk)
- [ ] Overloaded template callables (e.g. `Cast<T>`) wrapped via `Rem::Cast<T>` from `RemCastFn.h`
- [ ] Trivial "return x.Member" lambdas replaced with `std::mem_fn` (include `<functional>`)
- [ ] If C1060: use `REM_RANGES_FOREACH` or eagerly pre-collect or reduce pipeline depth
- [ ] Lambda in `transform` for C1060-safe side-effect pipelines returns `bool` (not `void`)

---

## Reference

- [official readme of transrangers](https://raw.githubusercontent.com/joaquintides/transrangers/refs/heads/master/README.md)
- [API tables](references/api.md) — entry points, ranger factories, terminal operations
- [Canonical pipeline patterns](references/canonical-pipeline.md) — every composition shape with full code

---

Based on [rem-write-better-skill](../rem-write-better-skill/SKILL.md) conventions. Last verified: 2026-07.
