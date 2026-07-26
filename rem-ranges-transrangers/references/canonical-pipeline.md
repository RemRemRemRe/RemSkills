# Canonical Pipeline Pattern

Detail moved out of `SKILL.md` so the rules stay scannable.

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
