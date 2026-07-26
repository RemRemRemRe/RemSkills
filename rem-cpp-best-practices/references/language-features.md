# Language Features

Detail moved out of `SKILL.md` so the rules stay scannable.

Use `auto` aggressively — everywhere, unless the explicit type is essential for
correctness (e.g., template argument deduction guide, or a type that `auto`
would incorrectly deduce). Readability comes from good variable names
(full words, no abbreviations), not from repeating type names the compiler
already knows.

### Decoration is mandatory

Every `auto` declaration must have the correct decoration to communicate
its value category to the reader:

```cpp
auto* Ptr = GetComponent();               // pointer — * is mandatory
auto& Ref = GetComponent();               // mutable reference
const auto& ConstRef = GetComponents();   // const reference

auto Value = Compute();                   // bare = value type, a COPY happened
auto Count = ComputeCount();               // value type
constexpr auto Threshold = 0.0001f;       // compile-time value
```

Never bare `auto` for pointer or reference — it slices away the indirection
and produces a copy. The decoration `*` / `&` communicates at a glance whether
you're working on the original or a local copy.

Bare `auto` (no `*`, no `&`) is a value type — a copy occurred. This is
acceptable and often intentional; the variable name should make the semantics
clear.

### When NOT to use `auto`

`auto` is inappropriate in these cases:

**Lambda parameters in generic positions** — when the lambda is passed to a
template function (e.g., `transrangers::transform`, `Sort`, `FindByPredicate`),
the IDE cannot resolve `auto` parameters because the lambda is a template
itself — the type is deduced at the call site, not at the definition. Use the
explicit type instead:

```cpp
// AVOID — IDE cannot navigate from (auto* Item):
Rem::Ranges::ForEach(transrangers::transform(
    [&](auto* Item) { ... },  // what type is Item? IDE can't tell
    ...));

// PREFER — explicit type, IDE-resolvable:
Rem::Ranges::ForEach(transrangers::transform(
    [&](UMyClass* const Item) { ... },
    ...));

// Sort lambda — same issue:
Items.Sort([](const FMyStruct& A, const FMyStruct& B) { return A.Value < B.Value; });
```

**`auto` return type deduction in public API** — the caller cannot see the
return type without reading the implementation. Use explicit return types
for public functions.

**Integer literals deduce `int`** — `auto Index = 0` deduces `int`, not the
project-standard `int32`. Loop counters and integer locals therefore use the
explicit `int32` — this is the "a type that `auto` would incorrectly deduce"
exception, not an auto-hostile case:

```cpp
for (int32 Index = 0; Index < 5; ++Index)  // NOT auto Index = 0 (deduces int)
int32 Count{};                              // NOT auto Count = 0
```

Float literals are fine: `auto Value = 0.5f` deduces `float`, which is the
project type. Note: no runtime difference exists on UE platforms (`int32` IS
`int` there) — the rule is a type contract: it locks the type against
`auto` deduction drift (`0u` → unsigned, `0LL` → int64) and matches the
`int32` UE APIs (`TArray::Num()`, index access) without conversions.

**Wrapped-pointer returns (`TNotNull`, `TObjectPtr`, ...)** — `auto*` cannot
deduce from a wrapper class; the compiler errors (C3535) instead of converting:

```cpp
// AVOID — C3535: cannot deduce 'auto*' from 'TNotNull<FFoo*>' / 'TObjectPtr<FFoo>':
auto* Pointer = Allocate(...);       // Allocate() returns TNotNull<uint8*>

// PREFER — bare auto keeps the wrapper (its operator-> is transparent):
auto Pointer = Allocate(...);

// Or an explicit raw pointer type when the wrapper must be dropped
// (e.g. a chain walk that terminates on nullptr — TNotNull cannot hold it):
FFoo* Chunk = Tail;
while (Chunk != nullptr) { ... }
```

### Good uses of `auto`

```cpp
const auto* Obj = CastChecked<UMyClass>(Source);            // type obvious from CastChecked
const auto ChannelData = Obj->Channel.GetData();            // return type clear from context
const auto& Items = Container->GetAllItems();               // reference to container
for (const auto* Item : Items) { ... }                     // element type known from Items
const auto Start = Range.GetLowerBoundValue();              // FInt32 is clear
```

### Return type deduction

Use trailing return type for template-heavy functions:

```cpp
template <std::derived_from<FRemFooBase> T>
auto FindComponent() -> T*;

// Or auto with trailing:
template <std::derived_from<FRemFooBase> T>
decltype(auto) GetDefaultRef();
```

For simple cases, return type on the same line is fine.

### `return {}` for default values

```cpp
return {};   // returns default-constructed T
return false;
return nullptr;
return FString{};
```

### `{}` vs `()` initialization

Always use uniform initialization `{}` for default member values. Prefer
zero-initialization — `float Value{};` zeros the memory rather than leaving it
indeterminate. An empty `{}` on any type ensures zero-fill:

```cpp
float Value{};                      // → 0.0f, zero-initialized
TObjectPtr<UObject> Owner{};        // → nullptr
bool bFlag{};                       // → false
int32 Count{};                      // → 0
FVector Location{};                 // → (0,0,0)
uint8 bStopped : 1{};              // → false
```

**Why zero-initialization `{}` over default-construction `()`:**

Default-construction (`FVector()`) may leave members uninitialized depending on the
type's constructor. Zero-initialization `{}` guarantees every byte is zero,
eliminating uninitialized-read UB and making behavior deterministic across all
builds (debug, development, shipping). For POD types, `{}` is a compile-time
zero-fill; for USTRUCTs, `{}` value-initializes which zeroes trivially-constructible
members.

**Critical exception — Unreal math types:** `FVector{}`, `TVector<T>{}`, `TRotator{}`,
`FQuat{}`, and similar engine math types do **NOT** zero-initialize by default
(the engine skips it for performance). Use `ForceInitToZero` to explicitly zero them:

```cpp
FVector Location{ForceInitToZero};               // zeroed
TVector<double> Coords{ForceInitToZero};          // zeroed
TRotator Orientation{ForceInitToZero};            // zeroed

// AVOID — NOT zero-initialized in UE:
FVector Location{};    // garbage/indeterminate
```

Non-zero defaults are not allowed in C++. Every member initializes to zero:

```cpp
float Speed{};           // zero — default: stationary
float GravityScale{};    // zero — designer configures via DataAsset at runtime
float BounceFriction{};  // zero
float Bounciness{};      // zero
```

Non-zero values are edited in the DataAsset or Blueprint editor — never
hardcoded as C++ defaults.

Avoid `= 0`, `= false`, or `= nullptr` for member variables — use `{}` for
zero-initialization everywhere. Use `()` for constructor calls where `{}`
would pick `initializer_list`.

**Exception:** Default parameters in overriding virtual functions must match the
base class signature. If the base uses `int32 Tolerance = 0`, the override must
also use `= 0` — `{}` is a syntax error in default parameter position.

---

Const correctness is a first-class concern — every variable, parameter, and
member function declaration must make its mutability contract explicit.
Apply `const` everywhere except where mutation is intended; `const` on
interfaces enables the compiler to catch accidental writes and
communicates intent to readers.

### `[[nodiscard]]` on every non-void function

```cpp
[[nodiscard]] bool IsValid() const;
[[nodiscard]] FString ToString() const;
[[nodiscard]] constexpr float Clamp01(float Value);
```

### `constexpr` everywhere possible

Compute at compile time when feasible. Use the `constexpr` family of
keywords (`constexpr` / `consteval` / `constinit`) as aggressively as the
current standard allows — the project builds with
`CppStandardVersion.EngineDefault` (C++20):

```cpp
constexpr float EvaluateExactDamper(const float DeltaTime, const float HalfLife)
{
    return 1.0f - FMath::Exp(-DeltaTime * FMath::Loge2 / HalfLife);
}

constexpr auto SomeThreshold = 0.0001f;
constexpr FStringView BoolText(const bool bVal)
{
    return bVal ? TEXTVIEW("True") : TEXTVIEW("False");
}
```

Variables of literal types (USTRUCTs with only scalar members, enums,
pointers, strong aliases) that are initialized with constant expressions
must be `constexpr`, not merely `const`:

```cpp
constexpr FRemAlphaBlend Blend{};          // USTRUCT with scalar members
```

Types that allocate (TArray, FString, containers with heap state) are NOT
literal — keep those `const`. When in doubt, `constexpr` + a build will tell.

> **Rider note:** `get_file_problems` only surfaces ERROR/WARNING severities;
> hint-level suggestions such as "Variable can be made constexpr" are NOT
> returned by the MCP tools. Reviewers must check `const` → `constexpr`
> opportunities manually (verified 2026-08).


### `const` on locals

Add `const` everywhere possible — it catches accidental mutation, documents intent,
and enables compiler optimizations:

```cpp
const int32 Count = GetCount();
const auto Result = Compute();
const auto* Ptr = GetComponent();
const auto& Ref = GetRef();
```

Non-`const` locals are the exception, reserved for:
- Variables that must be mutated
- Variables that will be **moved** — `const` inhibits the move constructor,
  forcing an unintended copy: `const auto Result = std::move(Source); // copies, not moves`

Always use `const` on:
- Reference locals (`const auto& Ref = GetRef();`)
- Pointer-to-const (`const UObject* Obj = GetObj();`)
- `const` member functions
- Non-mutating parameters passed by reference: `void Foo(const FString& Name);`

### `const` on value parameters in declarations

Omitting `const` on value parameters in declarations (headers) keeps the
call-site API clean — the caller doesn't care how the implementation treats
its copy. In the implementation (`.cpp`), adding `const` is optional if it
helps correctness:

```cpp
// Header — no const on value param:
void Process(int32 Value, FString Name);

// Implementation — const optional:
void Process(const int32 Value, const FString Name)
{
    // Value and Name are local copies; const prevents accidental mutation
}
```

### `const auto&` for range-for

```cpp
for (const auto& Component : Components)
{
    Component.Tick(DeltaTime);
}
```

---

Compile-time type branching uses `if constexpr` chains exclusively. No SFINAE,
no tag dispatch, no `std::enable_if`.

```cpp
template <typename T>
bool IsValid(const T& Object)
{
    using RawType = std::remove_cvref_t<T>;

    if constexpr (std::is_pointer_v<RawType>)
    {
        if (Object != nullptr)
        {
            using Type = std::remove_pointer_t<RawType>;
            if constexpr (std::derived_from<Type, UObject>)
            {
                return Rem::IsValid(*Object);
            }
            else
            {
                return true;
            }
        }
        return false;
    }
    else if constexpr (CNotNull<RawType>)
    {
        return Rem::IsValid(*Object);
    }
    else if constexpr (std::derived_from<RawType, UObject>)
    {
        return ::IsValidChecked(&Object);
    }
    else if constexpr (TIsTObjectPtr<RawType>::Value)
    {
        return ::IsValid(Object.Get());
    }
    else
    {
        static_assert(always_false<T>::value, "T is unsupported for IsValid");
        return false;
    }
}
```

### The `always_false<T>` pattern

Place in the `else` branch of `if constexpr` chains to produce a clean
`static_assert` message when no branch matches:

```cpp
template <typename>
struct always_false : std::false_type
{
};
```

---

All concepts are defined in the `Rem::` namespace with a `C` prefix.

### Derivation concepts (most common)

```cpp
namespace Rem
{
template <class T>
concept CUObject = std::derived_from<T, UObject>;

template <class T>
concept CAActor = std::derived_from<T, AActor>;

template <class T>
concept CAPlayerController = std::derived_from<T, APlayerController>;
}
```

### Interface concepts (requires expression)

```cpp
template <class T>
concept CHasGetWorld = requires(UWorld* World, const T Object)
{
    World = Object.GetWorld();
};

template <class T>
concept CHasIsValid = requires(bool Result, const T Object)
{
    Result = Object.IsValid();
};
```

### Composite concepts

```cpp
template <class T>
concept CStringable =
    std::is_same_v<bool, std::remove_cvref_t<T>>
    || CHasToString<T>
    || CHasGetName<T>
    || CUEnum<T>
    || CCanLexToString<T>;
```

### Concept usage

```cpp
// As template constraint:
template <CUObject T>
decltype(auto) GetDefaultRef()
{
    return *::GetDefault<T>();
}

// With std::derived_from:
template <std::derived_from<FRemFooBase> T>
auto FindComponent();

// In if constexpr guard:
if constexpr (CHasGetWorld<T>) { ... }
```

---

### UObject pointers

| Context | Type to use |
|---------|-------------|
| `UPROPERTY` member | `TObjectPtr<UObject>` |
| Function parameter | `UObject*` (raw pointer) |
| Function return | `UObject*` (raw pointer) |
| Local variable | `auto* Ptr = ...` |
| Weak reference (UPROPERTY) | `TWeakObjectPtr<UObject>` |
| Soft reference (UPROPERTY) | `TSoftObjectPtr<UObject>` |
| Soft class reference (UPROPERTY) | `TSoftClassPtr<UObject>` |
| Interface parameter (C++ API) | `IRemInterface*` (raw pointer) |
| Interface parameter (Blueprint API) | `TScriptInterface<IRemInterface>` |

`TScriptInterface` is the Blueprint-facing wrapper — a C++-only API takes a
raw `IRemInterface*` (or the concrete `UObject*` that implicitly upcasts); do
not leak `TScriptInterface` into C++-first signatures. Full examples incl.
`const` UObject pointers: `references/type-mapping.md`.

### `TNotNull` for non-null semantics

Wrap raw pointers when null is logically impossible:

```cpp
Rem::TNotNull<FRemBarContainer*> OwnerInstance;

// Dereference transparently:
OwnerInstance->Initialize();
auto& Ref = *OwnerInstance;
```

**Pointer type semantics:** When `T` is itself a pointer type (e.g. `TNotNull<const FMyStruct*>`),
`operator*()` returns a **reference to the pointed-to value**, not a reference to the stored
pointer. That is, `*NotNull` on `TNotNull<const FMyStruct*>` yields `const FMyStruct&` — a single
`*` reaches the value, not the stored pointer. Compare immediately with `==`, hash with
`GetTypeHash(*NotNull)`.

```cpp
TNotNull<const FMyStruct*> NotNull{&SomeStruct};
*NotNull               // → const FMyStruct&   (value reference)
*NotNull == *Other     // → value comparison
GetTypeHash(*NotNull)   // → hash of the value
```

**No pointer arithmetic on `TNotNull`** — `TNotNull` deletes `operator bool`
(see `Core/Public/Misc/NotNull.h`), which pollutes built-in operator resolution
on MSVC: `Wrapped + N` / `Wrapped - N` can select the deleted `bool` conversion
and fail to compile. Convert to the raw pointer first, then do arithmetic:

```cpp
// AVOID — MSVC: deleted 'operator bool' referenced, expression breaks:
auto* End = Chunk->Metadata + Chunk->MetadataNum;

// PREFER — raw pointer first, arithmetic on the raw pointer:
FFoo* Metadata = Chunk->Metadata;
auto* End = Metadata + Chunk->MetadataNum;
```

**`TNotNull` cannot represent `nullptr`** — a loop or walk that terminates on a
null link must use a raw pointer variable (`FChunk* Chunk = Tail;` + `Chunk =
Chunk->Prev;`), not a `TNotNull`. Assigning `nullptr` into a `TNotNull`
triggers `UE::Core::Private::ReportNotNullPtr()` (fatal in non-shipping builds).

### Never `NULL` or `0`

Only `nullptr` for null pointer constants. `NULL` is an integer in C++.

### Type casting — `static_cast` only

Always use `static_cast` for explicit type conversions. C-style `(Type)expr` and
functional-style `Type(expr)` bypass the compiler's type-checking and silently
reinterpret even unrelated types. `static_cast` catches errors at compile time:

```cpp
// Downcast from abstract base to concrete — compiler verifies the types are related
const auto& Auth = static_cast<const FMyState&>(AuthorityState);

// Fundamental-type conversion — intent is explicit
Out.Appendf("Count: %d", static_cast<int32>(bFlag));

// Pointer downcast — preferred over C-style (UMyType*)Ptr
auto* Widget = static_cast<UMyWidget*>(BaseWidget);
```

Do not use C-style casts. For `UObject`-based downcasts where runtime type checking
is required, use `Cast<T>()` (which internally uses `static_cast` after IsA check).

---
