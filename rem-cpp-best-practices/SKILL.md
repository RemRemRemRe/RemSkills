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

Every module's `Build.cs` must include:

```csharp
// Copyright RemRemRemRe. {Year}. All Rights Reserved.

using UnrealBuildTool;

public class MyModule : ModuleRules
{
    public MyModule(ReadOnlyTargetRules target) : base(target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        CppStandard = CppStandardVersion.EngineDefault;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        DefaultBuildSettings = BuildSettingsVersion.Latest;
        ShadowVariableWarningLevel = WarningLevel.Error;
        UnsafeTypeCastWarningLevel = WarningLevel.Warning;
        NonInlinedGenCppWarningLevel = WarningLevel.Warning;
        bUseUnity = false;
        bAllowUETypesInNamespaces = true;

        PublicDependencyModuleNames.AddRange([
            "Core",
            "CoreUObject",
            "Engine",
        ]);
    }
}
```

Key points:
- `CppStandardVersion.EngineDefault` — never override the C++ version
- `ShadowVariableWarningLevel = WarningLevel.Error` — shader variable bugs are real
- `bUseUnity = false` — every `.cpp` compiles independently; IWYU is enforced
- `bAllowUETypesInNamespaces = true` — enables UE types inside custom namespaces
- `IncludeOrderVersion.Latest` — uses the latest engine include dependency rules
- No precompiled header shortcuts — every file includes what it uses

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
| `.inl` for templates | Heavy template implementations go in `FileName.inl` alongside the header |

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

`GENERATED_BODY()` auto-declares `using Super = ...; using ThisClass = ...;`
only for `UCLASS` types via `DECLARE_CLASS`. `USTRUCT` does **not** receive
`Super` — define only `ThisClass` for USTRUCTs. For non-reflected F-classes,
define both on an as-needed basis:

```cpp
USTRUCT()
struct FMyData : public FBase
{
    GENERATED_BODY()

    using ThisClass = FMyData;   // recommended for USTRUCT
    // Super intentionally omitted — not generated by UHT for USTRUCT

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
    UPROPERTY(VisibleAnywhere, Category = "Component")
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

### Code alignment (from Rider .DotSettings)

- `ALIGN_MULTILINE_PARAMETER` = **False** (do not align parameters in columns)
- `ALIGN_MULTIPLE_DECLARATION` = **False** (do not align variable declarations)
- `INT_ALIGN_ENUM_INITIALIZERS` = **True** (align `=` in enum values)
- `INT_ALIGN_BITFIELD_SIZES` = **True** (align `:` in bitfield declarations)
- `CONTINUOUS_LINE_INDENT` = **Double** (continuation lines indented 2× tab)
- `KEEP_EXISTING_ENUM_ARRANGEMENT` = **False** (reformat enums on save)
- `MAX_ENUM_MEMBERS_ON_LINE` = **1** (each enum member on its own line)

---

## 5. `auto` & Type Deduction

Use `auto` whenever it does **not** harm readability. Removing redundant type
information reduces noise and lets readers focus on intent.

### Always decorate

```cpp
auto* Thing = Cast<UWhatCouldThisPossiblyBe>(Object);  // pointer
auto& LAM = GetWorld()->GetLatentActionManager();       // reference
const auto& Components = GetComponents();               // const reference
```

Never bare `auto` for pointer/reference — the decoration signals intent to readers.

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

Only use `= Val` when the value is deliberately non-zero:

```cpp
float MaxSpeed{5000.f};
int32 MaxBounces{3};
```

Avoid `= 0` or `= false` — use `{}` for zero-initialization.
Use `()` for constructor calls where `{}` would pick `initializer_list`.

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

**Do not** add `const` to value-type local variables unless the semantics demand
it (e.g., a threshold that must not be mutated). Adding `const` to value locals
prevents implicit move and adds noise.

```cpp
// AVOID:
const int32 Count = GetCount();
const auto Result = Compute();

// PREFER:
int32 Count = GetCount();
auto Result = Compute();
```

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
UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Component",
          meta = (ExcludeBaseStruct))
TArray<TInstancedStruct<FRemComponentBase>> Components;

// Boolean — only use bitfield when it actually saves memory under alignment
UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Component")
bool bInitialized{false};

// Bitfield only when packing gains real space (multiple flags adjacent):
UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Component")
uint8 bFlagA : 1{false};
UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Component")
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
Category = "Component"           // for component-specific UPROPERTYs
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
| `FString` | `std::string` | Engine standard; required for UPROPERTY |
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

### RemEnsure vs RemCheck — critical distinction

| Macro family | Purpose | Enabled in |
|-------------|---------|------------|
| `RemEnsure*` | Invariants needed in shipping builds | **All builds** (never disabled) |
| `RemCheck*` | Dev/editor-only verification | Editor & Development builds only (may be disabled in shipping; currently active, needs systematic testing to confirm) |

Use `RemEnsure` for conditions whose failure would corrupt player data, break
the game, or must never happen even in a shipped build.

Use `RemCheck` for dev-time validation, editor convenience checks, and
temporary debugging — things safe to strip from the final package.

### Usage

```cpp
// RemEnsureCondition — shipping-safe assertion
RemEnsureCondition(IsValid(Object), /*InvalidHandlingStatement*/,
                   LogCategory, Warning, TEXT("Object is invalid"));

// RemCheckCondition — dev/editor only, may be stripped in shipping
RemCheckCondition(Pointer != nullptr, /*HandlingStatement*/,
                  LogCategory, Error, TEXT("Pointer is null"));

// RemCheckVariable — dev/editor check a pointer/object is valid
RemCheckVariable(Obj, /*HandlingStatement*/,
                 LogCategory, Error, TEXT("Obj"));
```

These auto-default to `LogTemp` category and `ensureAlways` when not specified.

### Custom log categories

```cpp
// Header:
DECLARE_LOG_CATEGORY_EXTERN(LogRem, Log, All);

// Source:
DEFINE_LOG_CATEGORY(LogRem);
```

Then:
```cpp
UE_LOG(LogRem, Warning, TEXT("Value: %d"), SomeValue);
```

### Assertion principles

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
- [ ] Default member values use `{}` uniform init; zero-init where possible (not `= 0`)
- [ ] Inline definitions that must stay in header placed at file bottom; all others in `.cpp`
- [ ] Every `UPROPERTY` and exposed `UFUNCTION` has a `Category`
- [ ] `TObjectPtr<T>` (not raw `T*`) for all UPROPERTY UObject members
- [ ] Bitfields only when they actually save memory under alignment rules
- [ ] `[[nodiscard]]` on every non-void function
- [ ] `nullptr` — never `NULL` or `0`
- [ ] `static_cast<T>()` for explicit type conversions — no C-style or functional-style casts
- [ ] `override` on every virtual function override
- [ ] No `const` on value-type local variables (unless semantically required)
- [ ] No `const` on value-type parameters in declarations (optional in implementation)
- [ ] `Rem::` namespace for free utility functions
- [ ] `REM_API` export macro on public API types/functions; internals left unexported
- [ ] RemEnsure for shipping-safe checks; RemCheck for dev/editor only
- [ ] Build compiles with the module's `CppStandard.EngineDefault` + `ShadowVariableWarningLevel = Error`
- [ ] No debug `UE_LOG` left in

---

## References

- Epic C++ Coding Standard: <https://dev.epicgames.com/documentation/unreal-engine/epic-cplusplus-coding-standard-for-unreal-engine>
- Landelare Conventions (priority over Epic): <https://landelare.github.io/2022/06/23/epic-conventions.html>
- CppCoreGuidelines: <https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines>
- RemCommon plugin (project reference codebase)
- Rider Code Style: solution-level `.sln.DotSettings` and user-level `.uprojectdirs.DotSettings`
- Rider Inspections: exported `.DotSettings` inspection profile
- Original requirements: [references/origin-requirements.md](references/origin-requirements.md)
