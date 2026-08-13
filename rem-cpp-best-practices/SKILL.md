---
name: rem-cpp-best-practices
description: Review checklist for Rem project C++ code — build/compiler settings, file & include structure, naming, formatting, auto/type deduction, const correctness, pointers, if constexpr, ranges, concepts, UPROPERTY specifiers, macros, STL vs UE types, SOLID, logging/assertions, module/plugin conventions, test modules (spec style, DebugGame build), and the pre-commit checklist. Use when reviewing completed code before committing, or when writing new Rem module/test code that must match RemCommon conventions.
metadata:
  category: meta
  cpp-standard: EngineDefault
  trigger: manual
---

# Rem C++ Best Practices

This skill is a **review tool**, not a code-generation guide. Use it as a
checklist when examining completed code before committing. IDE formatting and
inspections cover mechanical rules automatically; this skill covers the
judgment-call rules that tooling cannot enforce.

Overriding rule: **match RemCommon style first**; Epic conventions where RemCommon is
silent; Landelare recommendations where they conflict with Epic and RemCommon agrees.

Each section below describes a category of checks. Apply the checklist (Section 17)
systematically after writing code, before committing.

## Reference files

The rules below are the contract. Detailed signature tables, boilerplate, and
extended examples live in `references/` — load them when writing that kind of code:

| File | When to load |
|------|--------------|
| `references/type-mapping.md` | Choosing STL vs UE types; writing UPROPERTY/UFUNCTION specifiers; UObject pointer types |
| `references/macros-logging.md` | Writing `REM_LOG_*` / `RemEnsure*` / `RemCheck*` calls; `REM_DEFINE_*` getter macros |
| `references/naming-formatting.md` | Extended naming/formatting examples and the `ThisClass` alias pattern |
| `references/tests.md` | Writing spec tests, test USTRUCT headers, or build/run commands for the test module; assertion pitfalls, reflection round-trip pitfalls, shared helper gotchas, dependency hygiene |
| `references/origin-requirements.md` | Original requirements behind these rules |

---

## 1. Build & Compiler Settings

Every module's `Build.cs` calls `Rem::BuildRule::RemSharedModuleRules::Apply(this)`
which sets all shared project-level compiler flags:

```csharp
// Copyright RemRemRemRe. {Year}. All Rights Reserved.

using UnrealBuildTool;
using Rem.BuildRule;

public class MyModule : ModuleRules
{
    public MyModule(ReadOnlyTargetRules target) : base(target)
    {
        RemSharedModuleRules.Apply(this);

        PublicDependencyModuleNames.AddRange([
            "Core",
            "CoreUObject",
            "Engine",
        ]);
    }
}
```

What `RemSharedModuleRules.Apply` configures:
- `CppStandardVersion.EngineDefault` — never override the C++ version
- `ShadowVariableWarningLevel = WarningLevel.Error` — shader variable bugs are real
- `bUseUnity = false` — every `.cpp` compiles independently; IWYU is enforced
- `bAllowUETypesInNamespaces = true` — enables UE types inside custom namespaces
- `IncludeOrderVersion.Latest` — latest engine include dependency rules
- `UnsafeTypeCastWarningLevel = WarningLevel.Warning`
- `NonInlinedGenCppWarningLevel = WarningLevel.Warning`

### Empty shell modules

Some engine plugins are now empty shells whose real headers moved into the
engine's own modules. **Do not list shell modules in `Build.cs` dependencies** —
their types resolve through the module that absorbed them (verified 2026-08):

- **StructUtils** — merged into `CoreUObject` in the current engine version
  (`CoreUObject/Public/StructUtils/` hosts `InstancedStruct.h`, `StructView.h`,
  `PropertyBag.h`, `InstancedStructContainer.h`, ...). The StructUtils plugin
  module only contains `StructUtilsModule.h`. Listing `"StructUtils"` produces
  the UBT warning `Plugin 'X' does not list plugin 'StructUtils' as a
  dependency`; the correct fix is to **remove the dependency**, not to add the
  plugin listing. Include `StructUtils/...` headers with only `CoreUObject`
  in the dependency list.

Rule of thumb: when a dependency only triggers "does not list plugin ..."
warnings for a module whose headers you can see inside another module you
already depend on, drop the dependency instead of listing the plugin.

---

## 2. File & Include Structure

### Header file layout (exact order)

```cpp
// Copyright RemRemRemRe. {Year}. All Rights Reserved.

#pragma once

// 1. Base class header
#include "Kismet/BlueprintFunctionLibrary.h"

// 2. Other dependencies (categorize at your discretion)
#include "RemNotNull.h"
#include "UObject/Object.h"

// 3. generated.h — MUST be included BEFORE any type declarations.
//    GENERATED_BODY() expands to a macro defined in the generated header; a
//    trailing include leaves it undefined (C4430). UHT emits forward
//    declarations itself, so the include stays outside namespaces.
#include "MyFile.generated.h"

// 4. Forward declarations (after all #includes)
class UObject;
class UWorld;
struct FGameplayTag;
template <typename T> struct TIsUEnumClass;
enum class ESomeEnum : uint8;
```

### Source file layout

```cpp
// Copyright RemRemRemRe. {Year}. All Rights Reserved.

// 1. Own header first
#include "MyFile.h"

// 2. Other dependencies
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"

// 3. Inline generated cpp by name (if needed)
UE_INLINE_GENERATED_CPP_BY_NAME(MyClass)

// 4. Implementation ...
```

### Rules

| Rule | Details |
|------|---------|
| Copyright header | `// Copyright RemRemRemRe. {Year}. All Rights Reserved.` on every file |
| `#pragma once` | Always, right after copyright |
| Base class first | In `.h`, the first `#include` is the base class header |
| `generated.h` before types | Must be included **before** any `UCLASS`/`USTRUCT` declaration (UHT requirement); forward declarations come after all includes |
| Own header first | In `.cpp`, matching header is the first `#include` |
| IWYU | Include every header directly used; do not rely on transitive includes |
| Empty line separators | Separate groups with empty lines for readability |
| `.inl` for templates | Heavy template implementations go in `FileName.inl` alongside the header. The `.h` stays minimal; callers `#include` the `.inl` directly when they need the template. Do NOT auto-include `.inl` from `.h` — it forces heavier transitive dependencies on every consumer of the `.h`. |

Dependency minimization is a HARD constraint: a `.h` never includes `.inl`.
Consumer-facing extension APIs that need `.inl` content live in their own
`FileName.inl` (e.g. `RemScopedStructContainer.inl` holds the container
`FindStructView` overloads); consumers include it explicitly. Shared primitives
used by several `.inl` files go in a dedicated lightweight `.inl`
(`RemStructViewStatics.inl`) — `.h` files still do not include it.

### Declaration / definition separation

Keep headers minimal to reduce reading noise. Inline function
definitions that must live in the header go at the **end of the file**
(after all declarations). Prefer `.cpp` for implementation bodies.

```cpp
// MyType.h
#pragma once

USTRUCT()
struct FMyType
{
    GENERATED_BODY()

    void Initialize();
    void Shutdown();

private:
    int32 SomeHelper() const;
};

// --- inline definitions at file bottom ---
inline int32 FMyType::SomeHelper() const
{
    return 42;
}
```

---

## 3. Naming Conventions

### Type prefixes (UHT-enforced)

| Prefix | Kind | Example |
|--------|------|---------|
| `U` | UObject subclass (non-Actor) | `URemActorComponent` |
| `A` | AActor subclass | `ARemCharacter` |
| `F` | Plain struct or non-UObject class | `FRemFooBase`, `FRemBarContainer` |
| `E` | Enum / enum class | `ERemFooOperator` |
| `I` | Abstract interface class | `IRemCommonModule`, `IRemScriptStructInterface` |
| `T` | Class template | `TRemFooCurve` |
| `C` | Concept (C++20) | `CInstanceOf`, `CUObject`, `CStringable` |
| `b` | Boolean variable / bitfield | `bInitialized`, `bIsDead` |

### Namespace structure

```
Rem::               — root namespace for all free functions
Rem::Math::         — math/lerp/clamp utilities
Rem::Struct::       — struct/view utilities
Rem::Enum::         — enum utilities
Rem::Subsystem::    — subsystem accessors
Rem::Latent::       — latent action helpers
Rem::ScopeExit::    — scope guard utilities
Rem::Animation::    — animation helpers
Rem::Object::       — object utilities
Rem::Private::      — internal implementation details (never in public API)
```

Every free utility function lives in `Rem::` or a sub-namespace.

### Function & member naming

- **PascalCase** everywhere: types, functions, members, locals, parameters
- **No abbreviations, full words** — names are the primary source of type
  information in `auto`-heavy code. `AbilitySystem`, not `ASC`;
  `MovementComponent`, not `MoverComp`. Contractions that squeeze a word
  (dropping interior characters) are also abbreviations and are prohibited:
  `Instance`, not `Inst`; `Seconds`, not `Sec`. Single-letter names (`T`,
  `U`, `A`, `B`) reduce readability and break IDE search. Exceptions only for:
  - Extremely well-known acronyms (`FOV`, `LOD`)
  - The abbreviation IS the type name (e.g., `IO` as a domain concept)
  - Template parameters (where `T` is the convention)
  - Lambda comparator parameters in `Sort` / `FindBy` where the context is
    limited to a single expression line — only there `A`/`B` are acceptable
- **No abbreviations** extends to local variables, function parameters, data
  members — every name must be self-documenting
- **Getter**: `Get<Name>()` — `GetOwner()`, `GetComponentIndex()`
- **Bool check**: `Is<Condition>()` / `Has<Property>()` — `IsInitialized()`, `HasTag()`, `ShouldTick()`
- **Output params**: prefix `Out` — `void GetItems(TArray<FItem>& OutItems)`
- **Non-const getter pair**: define both `const` and non-`const` overloads returning `auto&&`
- **Function objects**: `Rem::Fn::FunctionName` — via `REM_FUNCTION_TO_FUNCTOR_SIMPLE`

### Template parameter naming

- `T` for single generic type
- `BaseStructT`, `TOwner`, `EnumClass` for named constraints
- Concept names are PascalCase inside `Rem::` — `CInstanceOf<T>`, `CUObject<T>`

### `using ThisClass` alias

`GENERATED_BODY()` auto-declares:
- `UCLASS`: both `using Super = ...;` and `using ThisClass = ...;`
- `USTRUCT`: only `using Super = ...;` — no `ThisClass`

Define `using ThisClass = FMyType;` manually for USTRUCTs where needed.
For non-reflected F-classes, define both on an as-needed basis:

```cpp
USTRUCT()
struct FMyData : public FBase
{
    GENERATED_BODY()

    using ThisClass = FMyData;   // USTRUCT gets Super from UHT, add ThisClass manually
    // Super already declared by GENERATED_BODY

    float Speed{};
    void Apply();
};

// Non-reflected class:
class FMyHelper : public FBase
{
    using ThisClass = FMyHelper;  // as needed
    using Super = FBase;          // as needed
};
```

`using` declarations are treated as **data** in the member ordering rule —
they appear immediately after `GENERATED_BODY()`, before `UPROPERTY` data
members and before any function declarations.

Extended examples: `references/naming-formatting.md`.

---

## 4. Formatting

- **Allman braces** — opening brace on its own line for every construct (functions, classes, if, for, while, namespace)
- **Spaces** for indentation, 4-character width
- **One statement per line**
- **Pointer/reference spacing**: `Type* Ptr` / `const Type& Ref` — `*` and `&` bind to the type (right-hand)
- **Explicit braces** on all blocks — even single-statement branches

### Comment formats — `/** */` for declarations, `//` for implementations

- **`/**` Doxygen-style comments** — on public declarations in headers (types, functions, variables).
  IDE shows these on hover; Doxygen/doc generators parse them.
- **`//` line comments** — in `.cpp` implementations, inline inside function bodies,
  and for brief one-line notes.
- **`///` triple-slash** — not used. Prefer `/** */` for declarations.
- **No namespace closing comments** — `} // namespace Rem` is unnecessary; modern IDEs
  show the enclosing scope on hover / breadcrumb. Close with bare `}`.

### Member ordering

Within a type declaration, data members come before function members.
Data is the most critical information for understanding a class's role — it must
be immediately visible. Each group has its own explicit visibility label:

```cpp
struct FExample
{
    GENERATED_BODY()

public:
    UPROPERTY(EditAnywhere, Category = "Rem")
    float Speed{};

protected:
    UPROPERTY(VisibleAnywhere, Category = "Rem|Component")
    TObjectPtr<UObject> Owner{};

private:
    uint8 bCached : 1{false};

public:
    void GetSpeed() const;
    void SetSpeed(float InSpeed);

protected:
    void InternalUpdate();

private:
    void RecalculateCache();
};
```

Functions with the same visibility are grouped together after the data members
of that visibility. Repeat `public:`/`protected:`/`private:` as needed to express
the grouping.

### Rule of Five / Rule of Zero

Explicitly declare or delete all five:

```cpp
// Non-copyable, non-movable container:
FMyType()                                    = default;
FMyType(const FMyType&)                      = delete;
FMyType(FMyType&&) noexcept                  = delete;
FMyType& operator=(const FMyType&)           = delete;
FMyType& operator=(FMyType&&) noexcept       = delete;
~FMyType() noexcept                          = default;

// Or use the macro:
REM_DEFINE_THE_RULE_OF_FIVE(FMyType)
```

### Section organization

Use `#pragma region` / `#pragma endregion` with descriptive names:

```cpp
#pragma region Rule Of Five
// ...
#pragma endregion Rule Of Five
```

For USTRUCT/UCLASS, section order: GENERATED_BODY → public → protected → private.

### Code alignment

Alignment is handled entirely by the Rider `.DotSettings` — see the solution-level
code style file. The project enables `INT_ALIGN_EQ`, `INT_ALIGN_COMMENTS`,
`INT_ALIGN_DECLARATION_NAMES`, and `INT_ALIGN_DESIGNATED_INITIALIZERS` — so
assignment groups, trailing comments, and designated initializers ARE aligned.
Format with Rider and keep what it produces; never hand-align beyond that.
Each enum member stays on its own line.

Namespace contents are NOT indented (`NAMESPACE_INDENTATION = None` in the
project `.DotSettings`); see `references/naming-formatting.md` for the sample.

---

## 5. `auto` & Type Deduction

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

## 6. Const Correctness, `[[nodiscard]]`, `constexpr`

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

## 7. Pointers & References

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

Full examples incl. `const` UObject pointers: `references/type-mapping.md`.

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

## 8. `if constexpr` Dispatch

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

## 8b. Ranges & Functional Pipelines

Prefer ranges/functional composition over raw `for` loops. Use `Rem::Ranges` and
`transrangers` for data pipelines. See `rem-ranges-transrangers` skill for full API
reference.

### Avoid raw loops — compose with ranges

```cpp
// AVOID — raw for loop:
for (const auto* Section : Sections) { if (IsTrigger(Section)) { Process(Section); } }

// PREFER — functional pipeline:
Rem::Ranges::ForEach(
    transrangers::transform(ProcessSection,
        transrangers::filter(IsTrigger,
            Rem::Ranges::ConstArrayView(Sections))));
```

### Reduce duplication with templates in `.inl` files

When switching over enums creates repetitive code blocks, extract the common
logic into a template in a `.inl` file alongside the header:

```cpp
// MyFile.inl — template helper, included by the .cpp only:
template <ERemFooType TimerType>
FInstancedStruct MakeTimerHelper(const FRemFooConfig& Config, float Delay, int32 Loops)
{
    if constexpr (TimerType == ERemFooType::DelayInTime)
    {
        return MakeDelayInTime(Config, Delay, Loops);
    }
    else
    {
        return MakeDelayInFrame(Config, Delay, Loops);
    }
}

// MyFile.cpp — caller:
auto Result = MakeTimerHelper<Config.TimerType>(Config, Delay, Loops);
```

Keep `.inl` files minimal — they should contain only the template logic, not
heavier transitive includes. The `.h` stays clean; callers of the template
`#include` the `.inl` directly.

---

## 9. C++20 Concepts

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

## 10. UPROPERTY & UFUNCTION Specifiers

### Key rules

- Always set a `Category` on every reflected member — `"Rem"` or `"Rem|SubCategory"`
- Put `meta = (...)` last in the specifier list
- `UINTERFACE(MinimalAPI)` for pure interface classes
- `USTRUCT(BlueprintType)` for structs exposed to Blueprint
- `UCLASS(Blueprintable)` for classes that can be Blueprint-subclassed
- `GENERATED_BODY()` as first member of every reflected type
- Module `*_API` macro on every exported class: `class REMCOMMON_API UMyClass`
- Object references get `meta = (AddFilterUI = true)`; wrapper arrays get
  `TitleProperty`; instanced struct collections get `meta = (ExcludeBaseStruct)`
- Bitfields (`uint8 bFlag : 1`) only when packing gains real space under alignment

Full UPROPERTY/UFUNCTION patterns: `references/type-mapping.md`.

---

## 11. Macro Patterns

### When to use macros

Macros should be used for **mechanical code generation** that cannot be expressed in
standard C++ — getter generation, Rule-of-Five boilerplate, reflection helpers, and
functor adaptors. These macros eliminate repetitive hand-written code that would
otherwise drift out of sync.

Do NOT use macros for:
- **Control flow** (`if/else`, `return`, loops) — macros obscure the actual logic and
  break IDE navigation, debugging, and static analysis
- **Reducing line count** — a macro that wraps a 3-line `if/else` is harder to read and
  maintain than writing the 3 lines explicitly
- **Type name concatenation** (`##`) — fragile, breaks IDE refactoring, errors produce
  cryptic messages about generated type names

If a code block is repetitive, extract it into a **function** or **template**.
Templates go in `.inl` files alongside the header. Only reach for a macro when
`REM_DEFINE_*` is the established project convention and there is no C++ equivalent.

Getter macro signatures, Rule of Five, `REM_DEFINE_GET_SCRIPT_STRUCT_INTERFACE`,
`REM_FUNCTION_TO_FUNCTOR_SIMPLE`, and the `TStructOpsTypeTraits` deleted-copy
marker: `references/macros-logging.md`.

---

## 12. STL vs UE Types — When to Use Which

### Rules of thumb

- **Prefer STL** for: atomics (`std::atomic<T>`), `<type_traits>`, `std::numeric_limits<T>`, `using` aliases
- **Prefer UE** for: `TArray`, `TMap`, `TSet`, `FString` (legacy) / `FUtf8String` (default), `FName`, `FText`, `TFunctionRef`
- **Never use**: `NULL`/`0` pointers, `typedef`, C-style varargs, `GENERATED_UCLASS_BODY`/`GENERATED_USTRUCT_BODY`, raw `new`/`delete` (use `FMemory::Malloc`/`Free`)
- `TArray::Add` for existing values; `TArray::Emplace` for in-place construction or explicit ctors
- `FUtf8String` is the primary string type; `FString` only when the engine API demands it
- No structured bindings (`auto [a, b]`); float literals stay typed (`1.0f` not `1.0`)

Complete tables (judgment calls, string priority, Add vs Emplace):
`references/type-mapping.md`.

---

## 13. SOLID & Zero-Overhead Abstraction

### Single Responsibility

Each class/struct does one thing. Each function does one thing. If a struct
has `UPROPERTY` data and logic, the logic is in a separate non-reflected base
or a free function in `Rem::`.

### Interface Segregation / Dependency Inversion

- Define abstract interfaces via `UINTERFACE(MinimalAPI)` + `I*` class
- Or via C++20 concepts (preferred for compile-time dispatch)
- Free functions in `Rem::` namespaces over member functions where possible

### Zero-Overhead

| Principle | Guideline |
|-----------|-----------|
| No virtual unless polymorphic dispatch is required | `virtual` has vtable cost |
| `if constexpr` > runtime polymorphism | Compile-time branch is zero-cost |
| Templates pay only for instantiations | No runtime dispatch overhead |
| `constexpr` compute at compile time | Zero runtime cost |
| Pass trivial types by value | `int32`, `float`, `FVector` |
| Pass non-trivial types by `const&` | `FString`, `TArray` |
| Move from rvalues | `void SetName(FString Name) { Name = MoveTemp(Name); }` |

### Move semantics

```cpp
// Sink parameter pattern:
void SetName(FString Name)
{
    Name_ = MoveTemp(Name);
}

// Move out of return:
TArray<FItem> Items = GetItems();   // RVO or move, no copy

// Move in generic code:
template <typename T>
void Store(T&& Value)
{
    Data = std::forward<T>(Value);   // perfect-forwarding
}
```

---

## 14. Logging & Assertions

### Macro choice

- `RemEnsureCondition` / `RemEnsureVariable` — runtime-possible states, always
  active; use `RemEnsureVariable` for pointer/object checks (`Rem::IsValid`)
- `RemCheckCondition` / `RemCheckVariable` — developer-error guards, stripped
  when `DISABLE_CHECK_MACRO` is defined
- `REM_LOG_ROLE` / `REM_LOG_FUNCTION` / `REM_LOG_ROLE_FUNCTION` (+ `_COND`/`_CVAR`
  variants, `REM_SCOPED_LOG`) — log with `{}` placeholders, explicit category,
  no default category
- `REM_ENSURE` / `REM_ENSURE_ALWAYS` (+ `_MESSAGE`) — thin wrappers around
  engine `ensure*` with ALS-style lightweight mode
- `RemEnsure*`/`RemCheck*` do not take messages — pair with a `REM_LOG_*` call

All signatures, config macros (`REM_LET_IT_CRASH`, `NO_LOGGING`, ...), and usage
examples: `references/macros-logging.md`.

### 14f. Variable scoped minimization

> **Note:** This rule exists because AI-generated code frequently leaves variables
> in scope after their last use, enabling accidental misuse.

Declare variables in the narrowest possible scope. Prefer
initialization-inside-`if`-condition when the variable is only needed within the
guarded block. This prevents accidental use of stale values, reduces cognitive
load, and lets the compiler optimize away the variable earlier:

```cpp
// PREFER — variable scoped to the if-body:
if (auto* Component = Actor->FindComponentByClass<UMyComponent>())
{
    Component->DoWork();   // Component only exists here
}

// AVOID — variable outlives its useful scope:
auto* Component = Actor->FindComponentByClass<UMyComponent>();
if (Component)
{
    Component->DoWork();
}
// Component still in scope here — can be misused
```

### 14g. Flat execution blocks — avoid rocket code

> **Note:** This rule exists because AI-generated code frequently produces deeply
> nested `if` chains (the "rocket" anti-pattern) that obscure the main logic.

Deeply nested `if` chains obscure the main logic.
Use `std::invoke([&]{ ... })` to create a scoped execution block where
`RemEnsure*`/`RemCheck*` with `return` bail out cleanly. The main logic stays at
one indentation level:

```cpp
// Rocket code (AVOID):
if (auto* A = GetA())
{
    if (auto* B = A->GetB())
    {
        if (auto* C = B->GetC())
        {
            // actual logic  —  4 levels deep
        }
    }
}

// Flat block (PREFER):
std::invoke([&]
{
    auto* A = GetA();
    RemCheckVariable(A, return;);
    auto* B = A->GetB();
    RemCheckVariable(B, return;);
    auto* C = B->GetC();
    RemCheckVariable(C, return;);
    // actual logic  —  flat, no nesting
});
```

`std::invoke` immediately executes the lambda. `return` inside the lambda exits
the lambda, not the enclosing function — use it to bail out on failed
preconditions. Capture `[&]` for full access to the enclosing scope.

### 14i. Assertion principles

- `check()` — program invariant; fatal in all builds. Never put side effects inside.
- `ensure()` — recoverable "shouldn't happen"; fires once in non-shipping, returns bool.
- `ensureAlways()` — like ensure but fires every time.
- Remove debug prints before committing.

---

## 15. Module & Plugin Conventions

### Module interface

```cpp
#pragma once
#include "Modules/ModuleInterface.h"

class IMyModule : public IModuleInterface
{
public:
    static IMyModule& Get();
    static bool IsAvailable();
};
```

### Module implementation

```cpp
#include "MyModule.h"
#include "Modules/ModuleManager.h"

IMPLEMENT_MODULE(FMyModule, MyModule);

class FMyModule : public IMyModule
{
    virtual void StartupModule() override;
    virtual void ShutdownModule() override;
};

void FMyModule::StartupModule()
{
    IMyModule::StartupModule();
}

void FMyModule::ShutdownModule()
{
    IMyModule::ShutdownModule();
}
```

### API export macro

Export precisely only the types and functions that external consumers need.
Minimize the exported surface — keep implementation details internal to avoid
hitting the platform DLL export limit (typically 65535 symbols on Windows).
Use the `REM_API` shortcut pattern:

```cpp
// At the top of a header, define the alias:
#define REM_API MYMODULE_API

// Export only public API:
REM_API DECLARE_LOG_CATEGORY_EXTERN(LogMyModule, Log, All);
class REM_API UMyClass : public UObject { ... };
struct REM_API FMyStruct { ... };
REM_API void MyPublicFunction();

// Internal/private helpers — no export:
class FMyInternalHelper { ... };

// At the end of the file (or after the last export):
#undef REM_API
```

The `MYMODULE_API` macro is auto-generated by UBT from the module name. The
`REM_API` alias keeps declarations clean and consistent.

### `.uplugin` minimal fields

```json
{
    "FriendlyName": "MyPlugin",
    "Modules": [{ "Name": "MyPlugin", "Type": "Runtime", "LoadingPhase": "Default" }]
}
```

---

## 16. Test Modules & Automation Tests

### Module placement

Test code never lives in a runtime module — it goes in a dedicated test module
sibling to the module under test:

| Concern | Convention |
|---------|-----------|
| Module | `<Plugin>/Source/<ModuleName>Test` (e.g. `RemCommon` → `RemCommonTest`) |
| `.uplugin` type | `"Type": "UncookedOnly"` — compiled only into editor/uncooked targets, never into packaged builds |
| Test files | `Source/<ModuleName>Test/Private/Test/`, named `*Foo.spec.cpp` |
| Module impl | Minimal `IMPLEMENT_MODULE(FDefaultModuleImpl, <ModuleName>Test)`; a module without `IMPLEMENT_MODULE` loads but fails to initialize ("could not be initialized successfully") |
| Dependencies | The runtime module under test + Core/CoreUObject/Engine; `RemSharedModuleRules.Apply(this)` |

### Dependency direction (one-way, root to leaves)

Test module dependencies follow the runtime layering — dependencies flow from
the root/base toward the leaves, never upward:

- **Base layer** (`RemCommon`, third-party wrappers like `fmt` / `strong_alias`)
  sit at the root. A base plugin's test module must NOT depend on plugins that
  build on top of it (e.g. `RemCommonTest` must not depend on `RemRanges`,
  `RemStrongAliasTest` must not depend on `RemCommon`).
- **Test-to-test dependencies** are allowed (all `UncookedOnly`), but keep the
  same direction: a leaf plugin's test may reuse a base plugin's test fixtures,
  never the reverse.
- **Third-party libraries stay out of the BDD suites** — they ship their own
  tests. BDD specs test the Rem wrapper/integration, not the library itself.
- **Empty shell modules** (see §1 — e.g. `StructUtils` merged into CoreUObject)
  are not listed as dependencies at all.

### BDD spec style

All tests are written in BDD style: `DEFINE_SPEC` + `Describe`/`It` blocks with
behavior-describing `It` names ("should ..."). This is the project convention for
every test suite — it groups related scenarios under a shared context, reads as
behavior instead of implementation, and failure output shows the full
Describe/It hierarchy for fast localization. `IMPLEMENT_SIMPLE_AUTOMATION_TEST`
is reserved for one-off smoke checks only.

### Test USTRUCTs live in a namespace

Test-only USTRUCTs are declared inside `Rem::<Module>::Private` (requires
`bAllowUETypesInNamespaces = true`, set by `RemSharedModuleRules::Apply`); they
must not pollute the global scope. `generated.h` must be included BEFORE the
type declarations (a trailing include leaves `GENERATED_BODY()` undefined —
C4430); UHT emits the matching forward declaration inside the namespace.

UHT restrictions (verified on UE 5.8):

- `USTRUCT` / `UPROPERTY` must NOT be wrapped in `#if WITH_DEV_AUTOMATION_TESTS`
  (only `WITH_EDITORONLY_DATA` is allowed). Leave the structs unguarded; the spec
  `.cpp` is guarded, so non-test builds carry no test code.
- Namespace USTRUCTs are fully processed by UHT: `StaticStruct()`, reflection
  copy, and destruction all work (`InitializeStruct`/`CopyScriptStruct`/
  `DestroyStruct` run as usual).
- Test USTRUCTs referenced from the spec need a `using` declaration or qualified
  names (they are no longer in the global scope).

### Template headers need instantiation

A header-only template with no in-repo consumer compiles nothing — errors
(wrong `auto` deduction, MSVC overload quirks with `TNotNull` arithmetic,
missing includes) stay latent until first instantiation. Every template header
shipped in the repo must be instantiated by tests; this is the primary purpose
of the test module.

### Build & run configuration

Build and test commands must use the configuration the project actually develops
with — never default to a Development editor build. This project's development
configuration is **DebugGame Editor**; check `<project>/Source/*.Target.cs` or
team convention when in doubt. Editor binaries encode their configuration in
the file name (`UnrealEditor-Cmd.exe` = Development, `UnrealEditor-Win64-DebugGame-Cmd.exe`
= DebugGame) — always run the binary that matches the configuration you built.

Spec templates, test struct header templates, module boilerplate, and full
build/run commands: `references/tests.md`.

---

## 17. Pre-Commit Checklist

Before committing any C++ file:

- [ ] Copyright header present with current year
- [ ] `#pragma once` right after copyright
- [ ] Base class header first; generated.h included before any type declarations (not at file bottom)
- [ ] Includes separated by empty lines in logical groups; IWYU — no transitive dependencies
- [ ] `GENERATED_BODY()` as first member of every UCLASS/USTRUCT
- [ ] `using ThisClass = ...;` declared for USTRUCTs; `Super`/`ThisClass` as-needed for non-reflected classes
- [ ] Data members before function members, each with explicit visibility label
- [ ] Member default values use `{}` uniform init; zero-init where possible (not `= 0`/`= false`/`= nullptr`)
- [ ] Inline definitions that must stay in header placed at file bottom; all others in `.cpp`
- [ ] Every `UPROPERTY` and exposed `UFUNCTION` has a `Category`
- [ ] `TObjectPtr<T>` (not raw `T*`) for all UPROPERTY UObject members
- [ ] Bitfields only when they actually save memory under alignment rules
- [ ] `[[nodiscard]]` on every non-void function
- [ ] `nullptr` — never `NULL` or `0`
- [ ] `static_cast<T>()` for explicit type conversions — no C-style or functional-style casts
- [ ] `override` on every virtual function override
- [ ] `const` on all locals that are not mutated (wrapper locals too: `const auto` keeps `operator->` mutation of the pointed-to object legal)
- [ ] Literal-type locals/statics initialized with constant expressions use the `constexpr` family (`constexpr`/`consteval`/`constinit`); container/allocating types stay `const`
- [ ] `constexpr`-opportunity hints checked manually (Rider MCP does NOT return HINT severities)
- [ ] No `const` on value-type parameters in declarations (optional in implementation)
- [ ] `Rem::` namespace for free utility functions
- [ ] `REM_API` export macro on public API types/functions; internals left unexported
- [ ] RemEnsure* for runtime-possible states; RemCheck* for developer-error guards
- [ ] Variables declared at narrowest scope; if-condition-init where possible
- [ ] `FUtf8String` for all string returns/params; `FString` only when engine API requires
- [ ] Format strings use `{}` (no numbered placeholders); no `FString::Printf`
- [ ] Build compiles with the module's `CppStandard.EngineDefault` + `ShadowVariableWarningLevel = Error`
- [ ] No debug `REM_LOG_*` or `UE_LOGF` left in
- [ ] Variable/lambda parameter names are full words (no abbreviations, no single letters — `A`/`B` OK only in Sort lambdas)
- [ ] Lambda parameters in generic contexts (transrangers::transform, Sort) use explicit types, not `auto`
- [ ] Integer locals/loop counters use explicit `int32` (`auto X = 0` would deduce `int`)
- [ ] `TArray::Add` for adding existing values; `TArray::Emplace` for in-place construction or explicit ctors
- [ ] Control-flow macros avoided — repetitive `if/else` written explicitly; code deduplication done via templates in `.inl`
- [ ] No structured bindings (`auto [a, b]` — use explicit `Pair.Key` / `Pair.Value`)
- [ ] Comments: `/** */` Doxygen on header declarations; `//` in `.cpp` implementations; no `///`
- [ ] No `} // namespace Xxx` closing comments — bare `}`
- [ ] Tests live in a dedicated `<ModuleName>Test` module (`"Type": "UncookedOnly"`), never in the runtime module
- [ ] Test module dependencies follow one-way direction (root → leaves); no base plugin's test depends on a leaf plugin; third-party libs stay out of BDD
- [ ] No empty shell modules (e.g. `StructUtils`) in `Build.cs` — their headers resolve through CoreUObject
- [ ] Test cases use BDD spec style (`DEFINE_SPEC` + `Describe`/`It`, "should ..." names)
- [ ] Test USTRUCTs in `Rem::<Module>::Private` namespace; `generated.h` included before the type declarations
- [ ] No `USTRUCT`/`UPROPERTY` inside `#if WITH_DEV_AUTOMATION_TESTS` blocks
- [ ] Header-only templates are instantiated by tests (no latent compile errors)
- [ ] Test module has `IMPLEMENT_MODULE(FDefaultModuleImpl, ...)`
- [ ] Build/test commands use the project's actual configuration (DebugGame Editor), never a default Development build; run the binary matching the built configuration

---

## 18. Skill Maintenance Guidelines

See [rem-write-better-skill](../rem-write-better-skill/SKILL.md) for the shared
skill-writing conventions used across all RemSkills.

---

## References

- Epic C++ Coding Standard: <https://dev.epicgames.com/documentation/unreal-engine/epic-cplusplus-coding-standard-for-unreal-engine>
- Landelare Conventions (priority over Epic): <https://landelare.github.io/2022/06/23/epic-conventions.html>
- CppCoreGuidelines: <https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines>
- RemCommon plugin (project reference codebase)
- Rider Code Style: solution-level `.sln.DotSettings` and user-level `.uprojectdirs.DotSettings`
- Rider Inspections: exported `.DotSettings` inspection profile
- Original requirements: [references/origin-requirements.md](references/origin-requirements.md)
- Type mapping & reflection specifiers: [references/type-mapping.md](references/type-mapping.md)
- Macro & logging signatures: [references/macros-logging.md](references/macros-logging.md)
- Naming & formatting details: [references/naming-formatting.md](references/naming-formatting.md)
- Test module templates & commands: [references/tests.md](references/tests.md)
