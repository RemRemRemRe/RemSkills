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

## Includes

```cpp
#include "transrangers.hpp"         // transrangers::all, filter, transform, concat, zip, take, ranger_join
#include "RemRangesStatics.inl"     // Rem::Ranges::ForEach, ToArray, ArrayView, TakeN, FirstElement, NthElement
#include "RemRangesMacro.h"         // REM_RANGES_FOREACH — C1060 workaround
#include "RemStd.inl"               // RemStd::bind_back — partial application
#include "RemCastFn.h"              // Rem::Cast<T> — cast functor for transrangers::transform (avoids Cast overload ambiguity)
```

## API Reference

### `Rem::Ranges` — Consume a ranger (get data out)

| Function | Returns | Description |
|---|---|---|
| `ForEach(Ranger)` | `void` | Fires the pipeline but always exhausts the range. Use when side-effects are the goal. **No early exit** — consumption function always returns cursor deref value, not a stop signal. |
| `ToArray(Ranger)` | `TArray<ValueType>` | Materializes the ranger into a TArray. **Requires `ranger_element_t` to be a non-reference type** — use the two-arg overload `ToArray(OutArray, Ranger)` for rangers whose elements are references (e.g. after `ranger_join`). |
| `ToArray(OutArray, Ranger)` | `void` | Materializes into an existing TArray. |
| `TakeN<Count>(Ranger)` | `TArray<ValueType>` | Takes exactly `Count` elements, returns as TArray. Supports early exit via `take<Count>`. |
| `FirstElement(Ranger)` | `ValueType` | Returns the first element (calls `NthElement<0>`). **Supports early exit** — uses `take<1>` internally, so pipeline stops at first match. Returns a default-constructed value if no elements exist (e.g., `nullptr` for pointers). |
| `NthElement<N>(Ranger)` | `ValueType` | Returns the Nth element (0-indexed). **Supports early exit** via `take<N+1>`. |
| `ArrayView(TArray)` | ranger | Wraps a TArray as a ranger (non-const). |
| `ConstArrayView(TArray)` | ranger | Wraps a TArray as a ranger (const-safe). Prefer this for read-only pipelines. |

### `transrangers` — Build a ranger (lazy pipeline)

| Function | Returns | Description |
|---|---|---|
| `all(range)` | ranger | Entry point: creates a ranger from any range with `begin()`/`end()`. lvalue version captures by reference; rvalue version owns data via `all_copy`. |
| `filter(pred, ranger)` | ranger | Lazy filter. Predicate: `bool(const Element&)`. |
| `transform(fn, ranger)` | ranger | Lazy map. `fn: Element → NewType`. Note: function comes **first**, ranger comes **second**. |
| `concat(r1, r2, ...)` | ranger | Concatenates 2+ rangers end-to-end. |
| `take(N, ranger)` | ranger | Takes at most N elements. |
| `take<N>(ranger)` | ranger | Takes at most N elements (compile-time count). |
| `ranger_join(ranger)` | ranger | Flattens a ranger-of-ranges into a flat ranger via `all_adaption`. Use when each element is itself a range (TArray, etc.). |
| `zip(r1, r2, ...)` | ranger | Pairs elements into `std::tuple<...>`. |

### `RemStd::bind_back` — Partial Application

```cpp
template <typename F, typename... BoundArgs>
constexpr auto bind_back(F&& f, BoundArgs&&... args);
```

Binds arguments to the **back** of the parameter list. Returns a callable where:
- `call(call_args...)` invokes `f(call_args..., bound_args...)`

**Critical rule**: the element parameter (the one `transrangers::transform` passes) **must be the first parameter** of the function. Bound context parameters go after:

```cpp
// CORRECT: element first, context params after
bool Match(int32 Context, TInstancedStruct<FFoo>& Arg);
//        ^-- WRONG: Context would be passed as the element by transform
// Fix: reorder params
bool Match(TInstancedStruct<FFoo>& Arg, int32 Context);
auto Matcher = RemStd::bind_back(Match, Context);  // Matcher(Arg) calls Match(Arg, Context)
```

`TInstancedStruct` is from UE StructUtils (see `StructUtils/InstancedStruct.h`).

**Use case**: when a mapper function takes extra context parameters beyond the element:

```cpp
FBar Transform(const UFoo*, int32 Context);
// bind_back creates a unary function for transrangers::transform:
auto Mapper = RemStd::bind_back(Transform, Context);
// Mapper(Section) calls Transform(Section, Context)
```

## Canonical Pipeline Pattern

### Flat pipeline (filter → transform → consume)

```cpp
// 1. Source
auto Source = Rem::Ranges::ConstArrayView(SomeArray);

// 2. Build pipeline (right-to-left: inner first)
auto Pipeline = transrangers::transform(FinalMapper,
                    transrangers::filter(Predicate,
                        Source));

// 3. Consume
TArray<ResultType> Results = Rem::Ranges::ToArray(Pipeline);
```

### FlatMap pipeline (ranger_join)

When each element maps to a sub-range that needs flattening, use `ranger_join(transform(...))`.
The mapper **must return a raw range** (`const TArray<T>&`, `TArrayView<T>`, etc.) — NOT a ranger:

```cpp
// Correct: mapper returns raw range reference
// UMovieSceneTrack, UMovieSceneSection are UE MovieScene API types (see MovieSceneTrack.h, MovieSceneSection.h)
auto GetSections = [](const UMovieSceneTrack* Track) -> const TArray<UMovieSceneSection*>&
{
    return Track->GetAllSections();   // raw TArray ref — ranger_join wraps it with all()
};

auto AllSections = transrangers::ranger_join(
    transrangers::transform(GetSections,
        transrangers::filter(Predicate,
            Rem::Ranges::ArrayView(Tracks))));

// Then continue the filter/transform pipeline:
auto Results = Rem::Ranges::ToArray(
    transrangers::transform(Mapper,
        transrangers::filter(AnotherPredicate, AllSections)));
```

### Multi-source collection (eager fallback)

When data comes from two+ sources (e.g., master tracks + binding tracks), avoid nesting `ranger_join(transform(..., ranger_join(...)))`. Instead, eagerly pre-collect into a TArray and wrap:

```cpp
// UMovieScene, UMovieSceneSection are UE MovieScene API types (see MovieScene.h, MovieSceneSection.h)
auto CollectAllSections(UMovieScene* MovieScene)
{
    TArray<UMovieSceneSection*> Result;
    auto AppendSections = [&](const auto& Tracks)
    {
        for (const auto* Track : Tracks)
            if (Predicate(Track))
                Result.Append(Track->GetAllSections());
    };
    AppendSections(MovieScene->GetTracks());
    for (const auto& Binding : MovieScene->GetBindings())
    AppendSections(Binding.GetTracks());

    return transrangers::all(MoveTemp(Result));  // lazy from here on
}
```

### Find First with Early Exit

Use `ranger_join` for flattening, then `transform` → `filter` → `FirstElement`. The `take<1>` inside `FirstElement` ensures the pipeline stops at the first match.

`Rem::Fn::IsValid` is a functor that returns `true` for non-null pointers (equivalent to checking `ptr != nullptr` or `::IsValid(ptr)` for UObjects):

```cpp
// Mapper returns raw range reference (NOT a ranger) for ranger_join
auto GetSubArray = [](OuterType& Outer) -> TArray<InnerType>&
{
    return Outer.InnerArray;
};

return Rem::Ranges::FirstElement(
    transrangers::filter(Rem::Fn::IsValid,
        transrangers::transform(MapToPointer,
            transrangers::ranger_join(
                transrangers::transform(GetSubArray,
                    Rem::Ranges::ArrayView(OuterArray))))));
```

If the pipeline is too deep for DebugGame (C1060), pre-collect the flattened elements eagerly and continue:

```cpp
TArray<InnerType> AllElements;
for (auto& Outer : OuterArray)
{
    AllElements.Append(Outer.InnerArray);
}

return Rem::Ranges::FirstElement(
    transrangers::filter(Rem::Fn::IsValid,
        transrangers::transform(MapToPointer,
            transrangers::all(AllElements))));
```

### Extract Mapper with bind_back

When a `transform` mapper needs context data (member variables, local state), extract it as a named function and use `bind_back` instead of an inline lambda:

```cpp
// ── Before: lambda captures local/this context
auto fn = [&](TInstancedStruct<FFoo>& Arg) -> FBaz*
{
    auto* Inner = Arg.GetMutablePtr<FBar>();
    RemCheckVariable(Inner, return nullptr);
    if (!SomePredicate(Inner, SomeContext))
        return nullptr;
    return Inner->SomePtr;
};

// ── After: named function + bind_back
namespace
{
[[nodiscard]] FBaz* ExtractPtr(
    TInstancedStruct<FFoo>& Arg,  // element first (for transform)
    int32 Context)                 // context after (for bind_back)
{
    auto* Inner = Arg.GetMutablePtr<FBar>();
    RemCheckVariable(Inner, return nullptr);
    if (!SomePredicate(Inner, Context))
        return nullptr;
    return Inner->SomePtr;
}
}

// Usage:
transrangers::transform(RemStd::bind_back(ExtractPtr, Context), ranger)
```

`TInstancedStruct` is from UE StructUtils (see `StructUtils/InstancedStruct.h`).

Benefits: reduces template bloat (lambda type disappears from `transform`'s template instantiation), improves readability, and makes the mapper reusable/testable.

### Type Filter with transform(Cast<T>) + filter(IsValid)

Instead of writing a predicate that does `IsA<T>()` or `Cast<T>() != nullptr`, use a two-step pipeline: `transform(Cast<T>)` maps elements to `T*` (nullptr on type mismatch), then `filter(Rem::Fn::IsValid)` drops nullptrs. Use `Rem::Cast<T>` from `RemCastFn.h` (a functor struct that avoids `Cast` overload ambiguity):

```cpp
#include "RemCastFn.h"

// Pipeline: replaces filter(IsA<TargetType>) logic
transrangers::filter(Rem::Fn::IsValid,
    transrangers::transform(Rem::CastTo<UFoo>, AllSections))
// → ranger iterates UFoo* (already cast, valid)
```

`Rem::Cast<T>` is an `inline constexpr TCast<T>` variable template. Works for all `Cast` argument types (raw pointers, `TObjectPtr`, `TWeakObjectPtr`, etc.) — the `operator()` uses `decltype(auto)` forwarding.

### Functor Struct for Overloaded / Ambiguous Templates

When a **template function has multiple overloads** (e.g., UE's `Cast<T>`), passing `<T>` as a callable to `transrangers::transform` fails because the compiler can't select which overload without knowing argument types.

**Symptoms**: `C2664: cannot convert argument` or `C3169: cannot deduce type for 'auto'`.

**Solution**: `RemCastFn.h` provides `Rem::Cast<T>` — an `inline constexpr` variable template wrapping a functor struct:

```cpp
#include "RemCastFn.h"

// Rem::Cast<T> is an inline constexpr TCast<T> instance
// UMovieSceneEventTrack is a UE MovieScene API type (see MovieSceneEventTrack.h)
transrangers::transform(Rem::CastTo<UMovieSceneEventTrack>, ...);  // ✅

// Core implementation (in RemCastFn.h):
template <typename To>
struct TCast
{
    template <typename From>
    [[nodiscard]] constexpr decltype(auto) operator()(From&& Ptr) const
    {
        return Cast<To>(std::forward<From>(Ptr));
    }
};

template <typename To>
inline constexpr TCast<To> CastTo{};
```

**Why this works**: `Rem::CastTo<UMovieSceneEventTrack>` is a **concrete type** (one instantiation, no overloads). `transrangers::transform` stores a copy. When `(*pf)(*p)` is called, the compiler deduces `From` from `*p`'s type, then instantiates `operator()<From>(From&&)` — at which point `Cast<To>(From&&)` has both template args known and the correct overload is selected.

**Contrast with single-definition templates** (e.g., `Lib::Fn<T>`, `Rem::Fn::IsValid`): these have exactly one template definition with no overloads, so the compiler can resolve them without argument types. They work directly in `transform`. Overloaded templates (like UE's `Cast<T>` with raw-pointer, `TObjectPtr`, `TWeakObjectPtr` overloads) require the functor struct pattern.

### join (identity_adaption) — FlatMap with Ranger-Returning Mapper

When the mapper for flattening returns a **ranger** (not a raw `TArray`), use `transrangers::join` with the default `identity_adaption`. This avoids materializing intermediate arrays.

**However**, `transrangers::join` with mapper-returned temporary rangers has proven fragile (lifetime / compiler issues). **Prefer `ranger_join`** — have the mapper return a raw `TArray` by value instead. The extra per-element allocation is negligible for typical counts:

```cpp
// Mapper returns TArray<FBar> by value (raw range, compatible with ranger_join)
[[nodiscard]] TArray<FBar> MapToResults(const UFoo* Item, int32 Offset)
{
    TArray<FBar> Result;
    for (int32 Index = 0; Index < Item->Count(); ++Index)
        Result.Emplace(Item->GetValue(Index) + Offset);
    return Result;
}

// ranger_join flattens: transform yields TArray<FBar>, all_adaption wraps each as a ranger
auto AllResults = transrangers::ranger_join(
    transrangers::transform(RemStd::bind_back(MapToResults, Offset),
        typedRanger));
```

**Contrast**: `ranger_join` uses `all_adaption` which wraps each element with `transrangers::all()` — the element must be a raw range (TArray, TArrayView, etc.) with `begin()`/`end()`. `join` with `identity_adaption` expects each element to already be a ranger.

### zip + transform — Paired / Indexed Iteration

When you have parallel arrays (e.g., times + values), use `transrangers::zip` to pair elements, then `transform` to combine:

```cpp
// zip pairs ArrayA[i] with ArrayB[i] into std::tuple<A, B>, transform combines them
transrangers::transform(
    [](const auto& Pair) {
        const auto& [A, B] = Pair;
        return FBar{A + B};
    },
    transrangers::zip(
        transrangers::all(ArrayA),
        transrangers::all(ArrayB)));
```

**Note**: `zip` creates a `std::tuple` of references to each element. Use `const auto&` with structured bindings for zero-copy access.

### C1060-Safe Side-Effect Pipeline — ForEach + transform

When C1060 prevents `ranger_join` + `ToArray` (depth 4), use `Ranges::ForEach(transrangers::transform(side_effect, filter(...)))` — the lambda does `Append()` / `Add()` and returns `true` to continue. Pipeline stays at depth 2, no intermediate arrays:

```cpp
// DON'T — depth 4, C1060 in DebugGame
Results = Ranges::ToArray(
    transrangers::ranger_join(               // depth 4
        transrangers::transform(MakeResults,   // depth 3
            transrangers::filter(IsValid,      // depth 2
                transrangers::transform(Cast, AllItems)))));  // depth 1

// DO — depth 2, side-effect lambda, no intermediate arrays
TArray<FBar> Results;
Ranges::ForEach(
    transrangers::transform(
        [&](const UFoo* Item) -> bool
        {
            Results.Append(MapToResults(MakeNotNull(Item), Offset));
            return true;
        },
        transrangers::filter(Rem::Fn::IsValid,       // depth 2
            transrangers::transform(Rem::CastTo<UFoo>,  // depth 1
                AllItems))));
```

**Key points**:
- Lambda returns `bool` (`true` to continue) — `transform`'s cursor dereferences to `bool`, `ForEach` consumes it
- Intermediate array eliminated entirely
- `MapToResults` uses `TNotNull` for null-safety (type is already guaranteed by `filter(IsValid)`)
- Depth stays at 2 — well within C1060 safety

### C1060 Workaround (Heap Exhaustion)

Deeply nested transrangers templates can cause MSVC `C1060: compiler is out of heap space`.

**Safe depth**: a single `ranger_join(transform(filter(ArrayView)))` (depth ~2) compiles fine in DebugGame. Adding another `ranger_join` layer (e.g., for binding tracks) triggers C1060.

### Fix strategies (in order of preference)

1. **Eager pre-collection** — for multi-source data gathering, pre-collect into a TArray with a simple for-loop, then continue the pipeline with `transrangers::all(MoveTemp(Result))`. See "Multi-source collection" above.

2. **`REM_RANGES_FOREACH`** — replaces `Rem::Ranges::ForEach` at the consumption step when the pipeline is already built:
   ```cpp
   // Instead of: Rem::Ranges::ForEach(Pipeline);
   REM_RANGES_FOREACH(Pipeline);
   ```

3. **Reduce pipeline depth** — break a deep pipeline into multiple intermediate materializations (`ToArray` each sub-pipeline, then feed the result into the next).

### Common C1060 triggers
- `ranger_join` inside `ranger_join` (double flattening) — guaranteed C1060 in DebugGame
- `transform` → `filter` → `transform` → `ranger_join` chains exceeding 3 nested template levels in DebugGame
- Lambda returning a lambda (generic callable capturing another generic callable)

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

## Reference

- [official readme of transrangers](https://raw.githubusercontent.com/joaquintides/transrangers/refs/heads/master/README.md)

---

Based on [rem-write-better-skill](../rem-write-better-skill/SKILL.md) conventions. Last verified: 2026-07.
