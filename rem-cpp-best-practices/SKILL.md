---
name: rem-cpp-best-practices
description: Pre-commit C++ code review checklist. Use this skill explicitly — load it
  when reviewing completed code before committing, to verify conformance with project
  conventions (build config, include order, naming, formatting, const correctness,
  auto usage, if-constexpr dispatch, C++20 concepts, UPROPERTY/UFUNCTION specifiers,
  macro patterns, STL vs UE types, API export, SOLID zero-overhead, logging assertions).
  This skill is NOT intended for code generation — Rider/IDE tooling handles
  formatting and inspection automatically during writing.
metadata:
  engine-version: "5.7"
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

Each section below describes a category of checks. Apply the checklist (Section 16)
systematically after writing code, before committing.

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

// 3. generated.h — MUST be the last #include
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
| `generated.h` last | Must be the last `#include` in `.h` (UHT requirement); forward declarations come after it |
| Own header first | In `.cpp`, matching header is the first `#include` |
| IWYU | Include every header directly used; do not rely on transitive includes |
| Empty line separators | Separate groups with empty lines for readability |
| `.inl` for templates | Heavy template implementations go in `FileName.inl` alongside the header. The `.h` stays minimal; callers `#include` the `.inl` directly when they need the template. Do NOT auto-include `.inl` from `.h` — it forces heavier transitive dependencies on every consumer of the `.h`. |

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
| `F` | Plain struct or non-UObject class | `FRemComponentBase`, `FRemComponentContainer` |
| `E` | Enum / enum class | `ERemComparisonOperator` |
| `I` | Abstract interface class | `IRemCommonModule`, `IRemScriptStructInterface` |
| `T` | Class template | `TRemLerpCurve` |
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
- **No abbreviations** in variable names — `AbilitySystem`, not `ASC`; `MovementComponent`, not `MoverComp`. Exceptions only for extremely well-known acronyms (`FOV`, `LOD`) or when the abbreviation is the type name itself
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

---

## 4. Formatting

### Braces & indentation

```cpp
struct FExample
{
    GENERATED_BODY()

    void DoThing()
    {
        if (Condition)
        {
            Statement();
        }
    }
};
```

- **Allman braces** — opening brace on its own line for every construct (functions, classes, if, for, while, namespace)
- **Spaces** for indentation, 4-character width
- **One statement per line**
- **Pointer/reference spacing**: `Type* Ptr` / `const Type& Ref` — `*` and `&` bind to the type (right-hand)
- **Explicit braces** on all blocks — even single-statement branches

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

### Namespace indentation

Namespace contents are indented (Inner style):

```cpp
namespace Rem
{
template <class T>
concept CSomeConcept = requires(T Object) { Object.Foo(); };
}
```

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
code style file. Manual alignment (column-aligning parameters or declarations) is
disabled; each enum member stays on its own line.

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
auto Counter{0};                          // value type
constexpr auto Threshold = 0.0001f;       // compile-time value
```

Never bare `auto` for pointer or reference — it slices away the indirection
and produces a copy. The decoration `*` / `&` communicates at a glance whether
you're working on the original or a local copy.

Bare `auto` (no `*`, no `&`) is a value type — a copy occurred. This is
acceptable and often intentional; the variable name should make the semantics
clear.

### Return type deduction

Use trailing return type for template-heavy functions:

```cpp
template <std::derived_from<FRemComponentBase> T>
auto FindComponent() -> T*;

// Or auto with trailing:
template <std::derived_from<FRemComponentBase> T>
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

Compute at compile time when feasible:

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

```cpp
// Correct:
UPROPERTY(EditAnywhere, Category = "Rem")
TObjectPtr<UObject> Owner{};

void SetOwner(UObject* NewOwner);

// Also correct — raw pointer for non-UPROPERTY locals/params:
auto* World = GEngine->GetWorld();
if (const auto* Player = Cast<APlayerController>(Controller))
{
    // ...
}
```

### `TNotNull` for non-null semantics

Wrap raw pointers when null is logically impossible:

```cpp
Rem::TNotNull<FRemComponentContainer*> OwnerInstance;

// Dereference transparently:
OwnerInstance->Initialize();
auto& Ref = *OwnerInstance;
```

### Never `NULL` or `0`

Only `nullptr` for null pointer constants. `NULL` is an integer in C++.

### `const` UObject pointer

```cpp
TObjectPtr<const UObject> ConstObj{};  // UPROPERTY
const UObject* ConstPtr = ...;         // non-UPROPERTY
```

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
template <std::derived_from<FRemComponentBase> T>
auto FindComponent();

// In if constexpr guard:
if constexpr (CHasGetWorld<T>) { ... }
```

---

## 10. UPROPERTY & UFUNCTION Specifiers

### UPROPERTY patterns

```cpp
// Object reference — always AddFilterUI
UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rem",
          meta = (AddFilterUI = true))
TObjectPtr<UObject> Object{};

// Array of wrappers — TitleProperty for display
UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rem",
          meta = (AddFilterUI = true, TitleProperty = Object))
TArray<FRemObjectWrapper> Objects;

// Instanced struct collection — ExcludeBaseStruct
UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Rem|Component",
          meta = (ExcludeBaseStruct))
TArray<TInstancedStruct<FRemComponentBase>> Components;

// Boolean — only use bitfield when it actually saves memory under alignment
UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Rem|Component")
bool bInitialized{false};

// Bitfield only when packing gains real space (multiple flags adjacent):
UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Rem|Component")
uint8 bFlagA : 1{false};
UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Rem|Component")
uint8 bFlagB : 1{false};

// Numeric with constraints
UPROPERTY(EditAnywhere, Category = "Rem", meta = (ClampMin = "0", Units = "s"))
float Value{};

// Editor-only data
#if WITH_EDITORONLY_DATA
UPROPERTY(EditAnywhere, Category = "Rem")
FGameplayTag OptionalCategory;
#endif

// Const object reference
UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rem",
          meta = (AddFilterUI = true))
TObjectPtr<const UObject> ConstObject{};
```

### Category convention

Always `"Rem"` or `"Rem|SubCategory"`:

```cpp
Category = "Rem"
Category = "Rem|Object"
Category = "Rem|Component"
```

### UFUNCTION patterns

```cpp
UFUNCTION(BlueprintPure, Category = "Rem|Object",
          meta = (DeterminesOutputType = "ObjectClass"))
static UObject* GetObject(const TSoftObjectPtr<UObject>& SoftObjectPtr,
                          UClass* ObjectClass);

UFUNCTION(BlueprintCallable, Category = "Rem",
          Meta = (DevelopmentOnly, CompactNodeTitle = "Do Nothing"))
static void DoNothing();
```

### Key rules

- Always set a `Category` on every reflected member
- Put `meta = (...)` last in the specifier list
- `UINTERFACE(MinimalAPI)` for pure interface classes
- `USTRUCT(BlueprintType)` for structs exposed to Blueprint
- `UCLASS(Blueprintable)` for classes that can be Blueprint-subclassed
- `GENERATED_BODY()` as first member of every reflected type
- Module `*_API` macro on every exported class: `class REMCOMMON_API UMyClass`

---

## 11. Macro Patterns

### Getter macros (preferred over manual getters)

```cpp
// Full getter — returns reference, const + non-const:
REM_DEFINE_GETTERS_RETURN_REFERENCE(/*NamePredicate*/, /*NameSuffix*/, ReturnExpression)

// Value getter — returns by value, const only:
REM_DEFINE_GETTERS_RETURN_VALUE(/*NamePredicate*/, /*NameSuffix*/, ReturnExpression)

// Simple reference getter (predicate == suffix):
REM_DEFINE_GETTERS_RETURN_REFERENCE_SIMPLE(Name)

// Const-only reference getter:
REM_DEFINE_CONST_ONLY_GETTERS_RETURN_REFERENCE(NamePredicate, ReturnExpression)

// Template variant:
REM_DEFINE_TEMPLATE_GETTER_RETURN_VALUE(Concept, NamePredicate, NameSuffix, ReturnExpression)
```

Usage example:
```cpp
USTRUCT()
struct FRemFloatWrapper
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, Category = "Rem")
    float Number{};

    REM_DEFINE_GETTERS_RETURN_REFERENCE(/*no predicate*/, /*no suffix*/, Number)
};
// Generates: GetNumber() const and GetNumber() (non-const), both return auto&&
```

### Rule of Five

```cpp
REM_DEFINE_THE_RULE_OF_FIVE(Type)  // declares all 5 as = default
```

### Script struct interface

```cpp
REM_DEFINE_GET_SCRIPT_STRUCT_INTERFACE  // generates GetScriptStruct() override
```

### Functor from function

```cpp
REM_FUNCTION_TO_FUNCTOR_SIMPLE(IsValid)  // creates Rem::Fn::IsValid
```

### Deleted-copy marker on USTRUCT required by engine

```cpp
template <>
struct TStructOpsTypeTraits<FMyStruct> : TStructOpsTypeTraitsBase2<FMyStruct>
{
    enum { WithCopy = false };
};
```

---

## 12. STL vs UE Types — When to Use Which

### Always prefer STL

| STL Type | Instead of UE Type | Reason |
|----------|--------------------|--------|
| `std::atomic<T>` | `TAtomic<T>` | Officially preferred by Epic |
| `<type_traits>` (`std::is_*`, `std::remove_cvref_t`, etc.) | `TIsSame`, `TEnableIf`, etc. | Epic has deprecated their equivalents |
| `std::numeric_limits<T>` | UE numeric limits | STL receives more testing |
| `using Alias = Type;` | `typedef Type Alias;` | Modern syntax, supports template aliases |

### Always prefer UE types

| UE Type | Instead of STL | Reason |
|---------|----------------|--------|
| `TArray<T>` | `std::vector<T>` | Required for UPROPERTY; UE allocators |
| `TMap<K,V>`, `TSet<T>` | `std::map`, `std::unordered_map`, `std::set` | Required for UPROPERTY |
| `FString` | `std::string` | Engine legacy wide-string; `FUtf8String` works as UPROPERTY and should be used instead |
| `FName`, `FText` | — | No STL equivalent |
| `TFunctionRef<F>` | `std::function<F>` | UE native; GAS/latent action compatibility |

### Judgment calls

| Situation | Choice |
|-----------|--------|
| `TTuple<Ts...>` vs `std::tuple<Ts...>` | Either; `std::tuple` has more features, `TTuple` has `FArchive` support |
| `TVariant<Ts...>` vs `std::variant<Ts...>` | Either; same tradeoff as tuple |
| `<algorithm>` vs `Algo::` | Prefer `<algorithm>` for performance (`std::sort` > `Algo::Sort`); use `Algo` when iterators don't suffice |
| `TUniquePtr<T>` vs `std::unique_ptr<T>` | Either; `TUniquePtr` had UE4 bugs (fixed in UE5) |
| `TSharedPtr` / `TSharedRef` | Keep UE; thread-safe by default; make non-thread-safe for game thread only |
| `Forward<T>` vs `std::forward<T>` | Equivalent; `std::forward` uses `static_cast` (cleaner) |
| `MoveTemp` vs `std::move` | `MoveTemp` (`MoveTempIfPossible` = `std::move`); `MoveTemp` `static_assert`s moveability |

### Never use

- `NULL` or `0` for pointers — always `nullptr`
- `typedef` — always `using`
- C-style varargs `...` — use variadic templates
- Legacy `GENERATED_UCLASS_BODY` / `GENERATED_USTRUCT_BODY` — always `GENERATED_BODY()`
- Raw `new` / `delete` for struct allocations — use `FMemory::Malloc` / `FMemory::Free`

### String type priority

`FUtf8String` is the **primary** string type for all new code. `FString` (a.k.a.
`FWideString`) is legacy — use only when the engine API demands it. `FAnsiString`
is not used in this project.

| String type | When to use |
|-------------|-------------|
| `FUtf8String` | Default for all return values, parameters, and storage |
| `FUtf8StringView` | Pass-by-value; read-only slices without allocation |
| `TUtf8StringBuilder<N>` | Build strings incrementally (N=256 for typical messages) |
| `TStringBuilderBase<UTF8CHAR>&` | Output parameter for builder-based `ToString(Builder, Value)` |
| `FString` / `FWideString` | Legacy — only when the UE API requires it; convert to `FUtf8String` ASAP |
| `FStringView` | Legacy — only when the UE API requires it |
| `FAnsiString` | Not used — prefer `FUtf8String` for ANSI-range content |

All string-building flows go through `Rem::Format` which wraps `fmt::format_to`
directly into a `TStringBuilderBase<CharType>`. Format strings use `{}`
placeholders (no numbers needed — `fmt` infers argument order).

```cpp
// Return FUtf8String by default:
[[nodiscard]] FUtf8String ToString() const;

// Builder-based output (zero allocation):
void ToString(TStringBuilderBase<UTF8CHAR>& Builder) const;

// Formatting with {} placeholders:
Rem::Format("Value: {}, Delta: {}", Value, DeltaTime);
```

### No structured bindings

Do not use structured bindings (`auto [a, b] = ...`). Debugger support
(VS / Rider) remains incomplete — variables show as unviewable.

### Float literals stay typed

```cpp
float Value = 1.0f;    // NOT 1.0 (would be double)
double Value = 1.0;    // NOT 1.0f (would be float)
int32 Value = 1;       // fine
```

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

### 14a. Assertion macros — `RemEnsureCondition` / `RemEnsureVariable`

Two primary families, separated by what they validate:

| Macro | Validates | Equivalent to |
|-------|-----------|---------------|
| `RemEnsureCondition(...)` | An arbitrary boolean expression | `if (!LIKELY(Condition)) { ensureAlways(...); Handling; }` |
| `RemEnsureVariable(...)` | A pointer/object via `Rem::IsValid()` | `RemEnsureCondition(..., Rem::IsValid(Pointer), ...)` |

Both accept 1, 2, or 3 arguments via `REM_MULTI_MACRO` overload resolution.
The first optional argument is the **assertion macro** to fire on failure
(defaults to `ensureAlways`). The last optional argument is the **invalid
handling statement** — arbitrary statements executed when the condition is
false (typically `return;`, `return {};`, or a brace-enclosed block).

**Signatures and usage:**

```cpp
// 1 arg: condition only — fires ensureAlways, no handling
RemEnsureCondition(bInitialized);

// 2 args: condition + handling statement (defaults to ensureAlways)
RemEnsureCondition(MoverComp != nullptr, return;);

// 3 args: custom assertion macro + condition + handling
RemEnsureCondition(ensure, MoverComp != nullptr, return;);

// Same overloads for variable validation (uses Rem::IsValid internally):
RemEnsureVariable(MoverComp);                         // ensureAlways, no handling
RemEnsureVariable(MoverComp, return;);                 // ensureAlways + handling
RemEnsureVariable(check, MoverComp, return;);          // check() + handling
```

The assertion macro itself (`ensure`, `ensureAlways`, `check`, `verify`, etc.)
handles messaging — `RemEnsure*` macros do **not** accept log category,
verbosity, or message parameters. Use a `REM_LOG_*` call alongside when a
message is needed:

```cpp
RemEnsureVariable(MoverComp, return;);
REM_LOG_ROLE_FUNCTION(GetOwner(), LogRemMover, Warning, "Component not found");
```

The invalid handling statement is wrapped by `REM_INVALID_HANDLING_STATEMENT`
which strips it when `REM_LET_IT_CRASH` is defined — use this for final builds
that should crash instead of silently returning.

**Branch prediction:** `RemEnsureCondition` internally uses `LIKELY` /
`UNLIKELY` — the failure path is cold and the check has near-zero overhead
on the hot path. `RemEnsureVariable` delegates to `RemEnsureCondition`.

### 14b. `RemCheckCondition` / `RemCheckVariable`

Currently **aliases** for `RemEnsure*` when `DISABLE_CHECK_MACRO` is `false`
(the default). They share identical signatures and behavior.

The intended semantic distinction:
- `RemCheck*` — developer-error checks, intended to be stripped in shipping
  (gated by `DISABLE_CHECK_MACRO` in the future)
- `RemEnsure*` — runtime-possible states, always active

| Setting | Effect |
|---------|--------|
| `DISABLE_CHECK_MACRO = false` (default) | `RemCheck*` is identical to `RemEnsure*` |
| `DISABLE_CHECK_MACRO = true` | `RemCheck*` compiles to nothing |

**Usage:**

```cpp
RemCheckCondition(bInitialized);
RemCheckVariable(Pointer, return;);
RemCheckVariable(check, CriticalPtr, return;);
```

### 14c. Config macros

| Macro | Effect |
|-------|--------|
| `REM_LET_IT_CRASH` | Strips all invalid handling statements — failures become fatal |
| `REM_DISABLE_ASSERTION` | Disables the assertion self-test (`REM_ASSER_CONDITION_EVALUATED`) |
| `DISABLE_CHECK_MACRO` | Strips `RemCheck*` macros entirely |
| `NO_LOGGING` | Strips all `REM_LOG_*` macros (see 14d) |
| `REM_NO_ASSERTION` | Readability placeholder — no diagnostic, no handling |
| `REM_NO_HANDLING` | Readability placeholder — diagnostic only, no handling |
| `REM_NO_ASSERTION_OR_HANDLING(Condition)` | Readability: assert only, no handling, explicit condition |

### 14d. Log macros — `REM_LOG_ROLE` / `REM_LOG_FUNCTION` / `REM_LOG_ROLE_FUNCTION`

Three base families, distinguished by what decorator is prepended/appended to
the log message:

| Macro | Decorator |
|-------|-----------|
| `REM_LOG_ROLE(Object, Category, Verbosity, Format, ...)` | Net role name (Server/Client/etc.) prepended |
| `REM_LOG_FUNCTION(Category, Verbosity, Format, ...)` | `__FUNCTION__:line` appended |
| `REM_LOG_ROLE_FUNCTION(Object, Category, Verbosity, Format, ...)` | Both: role prepended, function appended |

Each family has two additional variants:

| Suffix | First extra parameter | Behavior |
|--------|-----------------------|----------|
| `_COND` | `Condition` | Logs only when condition is true (branch annotated `UNLIKELY`) |
| `_CVAR` | `ConsoleVariableName` | Logs only when the named CVar is true; `REM_ENSURE`s that the CVar exists |

Plus one scope-based macro:

| Macro | Behavior |
|-------|----------|
| `REM_SCOPED_LOG(Object, Category, Verbosity, LogStart, LogEnd)` | Logs `LogStart` on scope entry, `LogEnd` on scope exit (via `ON_SCOPE_EXIT`) |

When `NO_LOGGING` is defined, all `REM_LOG_*` macros compile to nothing.

**Format string:** Uses `{}` placeholder syntax (no numbers — `fmt` infers argument
order). `Rem::Format` delegates to `fmt::format_to` which writes into a
`TUtf8StringBuilder<256>`. Output goes through `UE_LOGF` with the `%hs` narrow-string
format specifier. Always specify the category explicitly — there is no default.

**Usage:**

```cpp
REM_LOG_ROLE(GetOwner(), LogRemMover, Warning,
    "Value: {}, Delta: {}", Value, DeltaTime);

REM_LOG_FUNCTION(LogRemMover, Verbose,
    "Tick at {}", GetWorld()->GetTimeSeconds());

REM_LOG_ROLE_FUNCTION(GetOwner(), LogRemMover, Error,
    "Fatal state in {}", GetNameSafe(this));

// Conditional — logs only when bVerbose is true:
REM_LOG_FUNCTION_COND(bVerbose, LogRemMover, Verbose,
    "Extra detail: {}", Detail);

// CVar-gated — logs only when "Rem.Mover.Debug" console variable is true:
REM_LOG_FUNCTION_CVAR(TEXT("Rem.Mover.Debug"), LogRemMover, Warning,
    "Debug info: {}", Info);
```

### 14e. Raw ensure wrappers — `REM_ENSURE` / `REM_ENSURE_ALWAYS`

Thin wrappers around Unreal's built-in assertion macros that switch between
lightweight and standard implementations based on build configuration:

| Macro | Wraps | Lightweight mode |
|-------|-------|-----------------|
| `REM_ENSURE(Expr)` | `ensure(Expr)` | ALS-style (no callstack) |
| `REM_ENSURE_ALWAYS(Expr)` | `ensureAlways(Expr)` | ALS-style (no callstack) |
| `REM_ENSURE_MESSAGE(Expr, Fmt, ...)` | `ensureMsgf(Expr, Fmt, ...)` | ALS-style |
| `REM_ENSURE_ALWAYS_MESSAGE(Expr, Fmt, ...)` | `ensureAlwaysMsgf(Expr, Fmt, ...)` | ALS-style |

Lightweight mode is active when `REM_WITH_DEVELOPMENT_ONLY_CODE` is true (i.e. in
editor/development builds). In non-development builds, these fall back to the
standard Unreal `ensure*` macros which include callstack capture and report
submission.

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

### 14h. Custom log categories

```cpp
// Header:
DECLARE_LOG_CATEGORY_EXTERN(LogRem, Log, All);

// Source:
DEFINE_LOG_CATEGORY(LogRem);
```

Then:
```cpp
UE_LOGF(LogRem, Warning, TEXT("Value: %d"), SomeValue);
```

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

## 16. Pre-Commit Checklist

Before committing any C++ file:

- [ ] Copyright header present with current year
- [ ] `#pragma once` right after copyright
- [ ] Base class header then generated.h as the **last `#include`**; forward declarations after `generated.h`
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
- [ ] `const` on all locals that are not mutated
- [ ] No `const` on value-type parameters in declarations (optional in implementation)
- [ ] `Rem::` namespace for free utility functions
- [ ] `REM_API` export macro on public API types/functions; internals left unexported
- [ ] RemEnsure* for runtime-possible states; RemCheck* for developer-error guards
- [ ] Variables declared at narrowest scope; if-condition-init where possible
- [ ] `FUtf8String` for all string returns/params; `FString` only when engine API requires
- [ ] Format strings use `{}` (no numbered placeholders); no `FString::Printf`
- [ ] Build compiles with the module's `CppStandard.EngineDefault` + `ShadowVariableWarningLevel = Error`
- [ ] No debug `REM_LOG_*` or `UE_LOGF` left in

---

## References

- Epic C++ Coding Standard: <https://dev.epicgames.com/documentation/unreal-engine/epic-cplusplus-coding-standard-for-unreal-engine>
- Landelare Conventions (priority over Epic): <https://landelare.github.io/2022/06/23/epic-conventions.html>
- CppCoreGuidelines: <https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines>
- RemCommon plugin (project reference codebase)
- Rider Code Style: solution-level `.sln.DotSettings` and user-level `.uprojectdirs.DotSettings`
- Rider Inspections: exported `.DotSettings` inspection profile
- Original requirements: [references/origin-requirements.md](references/origin-requirements.md)
