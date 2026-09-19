---
name: rem-cpp-best-practices
description: >
  Review checklist for Rem project C++ code — build/compiler settings, file & include
  structure, naming, formatting, auto/type deduction, const correctness, pointers,
  if constexpr, ranges, concepts, UPROPERTY specifiers and metadata completeness,
  numeric precision (float vs double for numeric members and config values), macros,
  STL vs UE types, SOLID & levels of abstraction, elegance proxies,
  comment discipline, logging/assertions (runtime observability rules live in
  `rem-observability-and-profiling`), module/plugin conventions, test modules
  (spec style, DebugGame build), and the pre-commit checklist. Use when reviewing
  completed code before committing, or when writing new Rem module/test code that
  must match RemCommon conventions.
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
| `references/type-mapping.md` | Choosing STL vs UE types; writing UPROPERTY/UFUNCTION specifiers and metadata; UObject pointer types |
| `references/scalar-width.md` | Choosing `float` vs `double` for a numeric member or config value; world-space vs bounded values, precision budget, storage size |
| `references/naming-formatting.md` | Naming and formatting detail: namespace layout, extended examples, member ordering, `ThisClass` alias |
| `references/file-layout.md` | Header/source layout examples and the include rules |
| `references/language-features.md` | `auto`, `const`/`constexpr`, `if constexpr`, concepts — rules with worked examples |
| `references/design.md` | SOLID, zero-overhead table, move semantics |
| `references/modules.md` | Module/plugin skeleton, `.uplugin` fields, export macro |
| `references/dll-boundaries.md` | Exporting a class template's **instantiation** across a module boundary; export-macro placement, C4910 / C2908 / C2766, verifying against the binary's export/import tables |
| `references/macros-logging.md` | Writing `REM_LOG_*` / `RemEnsure*` / `RemCheck*` calls; `REM_DEFINE_*` getter macros; `REM_DEFINE_PRIVATE_MEMBER_ACCESSOR` usage and pitfalls |
| `references/pitfalls.md` | Reviewing code against verified pitfalls: UPROPERTY-able types and preprocessor-block limits, struct-copy transient semantics, assertion-macro includes, weak-pointer operators, actor-constructor limits, test-world driving |
| `references/tests.md` | Writing spec tests, test USTRUCT headers, or build/run commands for the test module; assertion pitfalls, reflection round-trip pitfalls, shared helper gotchas, dependency hygiene |
| `references/rider-diagnostics.md` | Rider false-positive catalogue and the triage rule |
| `references/origin-requirements.md` | Original requirements behind these rules |

## Local overlay

`local/` holds machine-local values - git-ignored symlinks into a private repository that tracks
them, never committed here; they win over `references/` and the rules below, and carry values only
(the model is owned by `rem-public-skill-generalization`). Files read when present:

- `local/project-conventions.md` - project-specific conventions and verified practice

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

        PrivateDependencyModuleNames.AddRange([
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

Engine plugins whose real headers moved into another module must not be listed
in `Build.cs` — **drop the dependency** instead (the `StructUtils` case and the
rule of thumb: `references/modules.md`).

---

## 2. File & Include Structure

Header order: copyright → `#pragma once` → base class header → other dependencies → `generated.h` **before any type declaration** → forward declarations. Source order: copyright → own header first → other dependencies → `UE_INLINE_GENERATED_CPP_BY_NAME` → implementation.

Rules: `#pragma once` always; base class first in `.h`; IWYU (include every header used directly, never rely on transitive includes); empty-line groups; heavy templates go in `.inl` and are **never auto-included from the `.h`** (a `.h` never includes an `.inl`); inline definitions that must stay in the header go at the file bottom.

Layout examples and the full rule table: `references/file-layout.md`.

---

## 3. Naming Conventions

Type prefixes (UHT-enforced): `U` UObject, `A` Actor, `F` plain struct/class, `E` enum, `I` interface, `T` template, `C` concept, `b` boolean.

- PascalCase everywhere; **no abbreviations, full words** (`AbilitySystem`, not `ASC`; `Instance`, not `Inst`). Exceptions: well-known acronyms (`FOV`, `LOD`), the abbreviation that IS the type name, template parameters, and `A`/`B` in single-line Sort/FindBy comparators.
- `Get<Name>()`; `Is<Condition>()` / `Has<Property>()`; output params prefixed `Out`; a getter pair defines both `const` and non-`const` overloads returning `auto&&`.
- Free utility functions live in `Rem::` or a sub-namespace; C++-only utility APIs are namespace free functions, and `U<Domain>Statics` holds only Blueprint-facing `UFUNCTION`s.
- **Survey `RemCommon` before adding a helper or enum** — a duplicate of an existing facility is a review rejection.
- `using ThisClass = ...;` is required for USTRUCTs; `using` declarations count as data and sit right after `GENERATED_BODY()`.

Namespace layout, extended examples and the full naming tables: `references/naming-formatting.md`.

---

## 4. Formatting

Allman braces; 4-space indentation; one statement per line; `Type* Ptr` / `const Type& Ref`; explicit braces on every block; namespace contents not indented; alignment is whatever the Rider `.DotSettings` produces — never hand-align.

**Comments:** `/** */` Doxygen on header declarations, `//` in `.cpp`, never `///`; no `} // namespace` closing comments. Discipline: **the default is no comment** — self-explanatory code is the goal; a fact that needs one usually wants a better name instead, and a comment narrating its own line is deleted. What earns one: **why** a choice was made and which invariant holds, one concept per comment, at its most useful spot; **overview comments** (a file's, type's or section's purpose and reading order) are the exception worth writing. Use real Doxygen keywords (`@warning`, `@note`, `@param`, `@return`, `@tparam`, `@see`, `@todo`), never plain-text lookalikes. A comment next to a declaration can become its **tooltip**: UHT stores a `/** */` doc comment as `ToolTip` metadata — and equally a bare `//` line or a comment inside the specifier list as `Comment` metadata, which the details panel falls back to when no doc comment exists; never park specifier text (`Transient/*, Meta = (...) */`) or preprocessor lines there (data-side symptoms: `rem-ue-localization` `references/pitfalls.md`).

**Member ordering:** data members before function members in every visibility group, each group with its own explicit label; `using` declarations count as data. A data member after any function member (constructors included) is a review rejection.

**Rule of Five/Zero:** declare or delete all five (or `REM_DEFINE_THE_RULE_OF_FIVE`). Use `#pragma region` for section organization.

**Reformat caveat:** the Rider reformatter can split a long `UPROPERTY` `meta` string mid-string → UHT "Unterminated character constant"; re-check long literals after `reformat_file`.

Examples and the sample layout: `references/naming-formatting.md`.

---

## 5. `auto` & Type Deduction

Use `auto` aggressively — readability comes from full-word names, not repeated types. **Decoration is mandatory:** `auto*` pointer, `auto&` mutable reference, `const auto&` const reference, bare `auto` means a copy happened.

Do **not** use `auto` for: lambda parameters in generic positions (the IDE cannot resolve them — write the explicit type), public API return types, integer literals (`auto Index = 0` deduces `int` — write `int32`), or wrapped-pointer returns (`auto*` cannot deduce from `TNotNull`/`TObjectPtr`; use bare `auto`).

`{}` uniform initialization for member defaults (zero-initializing); engine math types (`FVector{}`) do **not** zero — use `ForceInitToZero`; non-zero defaults are not allowed in C++ (configure them in the DataAsset).

Full rules and examples: `references/language-features.md`.

---

## 6. Const Correctness, `[[nodiscard]]`, `constexpr`

`[[nodiscard]]` on every non-void function. `const` everywhere possible — locals, reference locals, pointer-to-const, member functions, non-mutating by-reference parameters; exceptions: values that will be moved (`const` inhibits the move) and value parameters in declarations.

Use the `constexpr` family aggressively for literal types initialized with constant expressions (`constexpr`, not merely `const`); allocating types (`TArray`, `FString`) are not literal and stay `const`. Rider MCP does not return HINT severities — check `const` → `constexpr` opportunities manually.

Examples and the full rule set: `references/language-features.md`.

---

## 7. Pointers & References

UObject pointer type by context: `TObjectPtr<T>` for a `UPROPERTY` member, raw `UObject*` for parameters/returns/locals, `TWeakObjectPtr`/`TSoftObjectPtr`/`TSoftClassPtr` for weak and soft references; a C++-first API takes a raw `I*` interface pointer (never `TScriptInterface`, which is Blueprint-facing).

`Rem::TNotNull<T>` expresses non-null semantics: `*NotNull` on `TNotNull<const T*>` yields the **value** reference, no pointer arithmetic (MSVC selects the deleted `operator bool` — convert to a raw pointer first), and it cannot hold `nullptr` (a walk that terminates on null uses a raw pointer). Never `NULL` or `0`.

Express that contract in the **type**, not by wrapping at the call site: `TNotNull`'s pointer
constructor is implicit (`explicit(!TIsImplicitlyConstructible_V<T, ArgTypes...>)`), so
`return Pointer;` into a `TNotNull<T*>` return type needs no helper and runs the same null check.
`MakeNotNull` is for the cases where *deduction* matters: it keeps the pointee's constness and
unwraps a `TObjectPtr`.

Examples and the full table: `references/language-features.md`.

---

## 8. `if constexpr` Dispatch

Compile-time type branching uses `if constexpr` chains **exclusively** — no SFINAE, no tag dispatch, no `std::enable_if`. Terminate a chain with the `always_false<T>` pattern so an unmatched branch produces a clean `static_assert` message.

Full example: `references/language-features.md`.

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

All concepts live in `Rem::` with a `C` prefix — derivation concepts (`CUObject`, `CAActor`, ...), interface concepts via `requires` expressions, and composite concepts composed from them. Use concepts as template constraints and in `if constexpr` guards.

Definitions and examples: `references/language-features.md`.

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
- Numeric properties with units use `meta = (ForceUnits = "<unit>")`, not `Units`:
  `ForceUnits` pins the display to a fixed unit; `Units` auto-scales to locale
  preference and magnitude (cm as km, bytes as MB), which is unpredictable for
  fixed gameplay values. Engine semantics: `references/type-mapping.md`.
- Bitfields (`uint8 bFlag : 1`) only when packing gains real space under alignment

### Metadata completeness

A reflected property carries the metadata its **consumer** needs. Missing
metadata is a review finding, not a style preference. Rule of thumb: if the
editor cannot show a designer **what the value means, what unit it is in, and
when it is valid**, the metadata is incomplete.

The per-kind lookup table — units, clamps, `EditCondition`/`EditConditionHides`,
`TitleProperty`, `MetaClass`, `TitleProperty`, tooltips — is the single copy in
`references/type-mapping.md`.

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

Getter macro signatures, `REM_DEFINE_PRIVATE_MEMBER_ACCESSOR` usage, Rule of Five,
`REM_DEFINE_GET_SCRIPT_STRUCT_INTERFACE`, `REM_FUNCTION_TO_FUNCTOR_SIMPLE`, and the
`TStructOpsTypeTraits` deleted-copy marker: `references/macros-logging.md`.

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

### Scalar width for numeric members — float vs double

The `FVector`/`FRotator`/`FTransform` family is `double` by construction (the
LWC macro hard-codes it); `FVector3f`/`FRotator3f`/... is a deliberate
narrowing. Ask one question: **does this value describe a place in the world,
or a property of a thing?**

| Value | Width |
|---|---|
| World position; a world-space offset consumed as a position; accumulated world state (position, velocity, force) | `double` — `FVector` |
| Tuning parameter (speed, acceleration, gravity scale, radius, duration), angle, scale, ratio, alpha, weight, probability, normalized direction | `float` is normal, and matches the engine's own movement components |
| Bulk array of positions | `float` only as a re-based local array with one `double` origin (`references/scalar-width.md` §7) |

Never store an **authoritative** world position — or anything that will be added
to one — in an `f` type: the precision is lost at write time and no
consumer-side widening recovers it. Re-basing an array into local space is not
an exception — it stops being a world position. The engine narrows the *tuning
value*, never the *state* (`MaxWalkSpeed` is `float`; `LastUpdateLocation` is
`FVector`). A bounded quantity that never enters the world-space arithmetic graph
— a rate or distance only your own math scales with — is an `f` candidate
whatever its units; three tests decide (`references/scalar-width.md` §3). Convert
narrow → wide once, at the boundary that loads config into runtime state, not
inside a per-tick path. Name the width at the conversion site with the project's
conversion macros (`RemFloatDoubleConversionMacros.h`) rather than an ad-hoc
cast.

Precision tables, the size analysis per storage medium, the engine citations and
the boundary pattern: `references/scalar-width.md`.

### Struct views — type-only vs instance

`FConstStructView::Make(T{})` binds to a temporary that dies at the end of the
full expression, so the returned view is dangling. To express "the type, not an
instance", construct the view with a null memory pointer:

```cpp
return FConstStructView{ T::StaticStruct() };   // type-only (null memory)
// not FConstStructView::Make(T{})              // dangling
```

`FInstancedStructContainer::InsertAt/Append` default-constructs each new item
(`InitializeStruct`) and copies from the source view only when its memory is
non-null. A type-only view yields a properly default-constructed instance; a
dangling view overwrites it with garbage.

### Instanced struct two-arg initialization (verified 2026-08)

`TInstancedStruct` has **no non-template two-argument `InitializeAs`**. The
template `InitializeAs<T>(TArgs&&...)` forwards its arguments to `T`'s
constructor (compile error C2661 "no overloaded function takes N arguments"
when given a script struct + memory pointer). The two-arg initializer that
copies from an existing struct instance is named differently:

```cpp
// AVOID — the template treats the args as T's constructor arguments (C2661):
Foo.InitializeAs(ScriptStruct, Memory);

// PREFER — the non-template copy-initializer:
Foo.InitializeAsScriptStruct(ScriptStruct, Memory);
```

See `CoreUObject/Public/StructUtils/InstancedStruct.h` (`TInstancedStruct`
provides `InitializeAsScriptStruct`; the template `InitializeAs<T>` is for
emplace-construction).

---

## 13. SOLID & Zero-Overhead Abstraction

**Single responsibility:** one thing per type and per function. **Respect levels of abstraction:** a function body reads at one level — mixed-level bodies are the first symptom of a function doing two things. **Interface segregation / dependency inversion:** `UINTERFACE(MinimalAPI)` + `I*` or C++20 concepts (preferred for compile-time dispatch); free functions in `Rem::` where possible.

Zero-overhead rules and move semantics: `references/design.md`.

### Elegance — objective proxies

"Elegant" is not reviewable as stated, so it is checked through proxies a
reviewer can point at. A review may raise **at most three** elegance findings
per change, each naming the concrete alternative — anything beyond that is
taste, not a defect, and must not be reported.

| Proxy | The finding looks like |
|---|---|
| Minimal surface | An exported/public member no caller uses; a `public` that could be `private`; a non-`const` method that never mutates |
| Names reveal intent | A name that describes the mechanism instead of the concept (`ProcessData` for what is really "apply damage") |
| No hidden side effects | A getter that mutates; a constructor that touches the world; a query that allocates unbounded |
| No dead weight | Dead code, commented-out code, unused parameters, unreferenced helpers, `#if 0` blocks |
| No premature abstraction | A base class / interface / template with exactly one implementation and no planned second; a parameter that only ever takes one value |
| Symmetry and consistency | Sibling methods with different shapes; one path throwing and another returning a sentinel; a new helper duplicating one that already exists (survey `RemCommon` first — §3) |
| One reason to change | A header including unrelated subsystems; a function whose name needs "And" |

Deletion is the preferred fix: a proxy that fails because the code is
unnecessary is resolved by removing it, not by adding a layer.

---

## 14. Logging & Assertions

**Scope:** this section owns macro choice, assertions and their signatures.
When and where to log, debug drawing, tooling hooks and profiling tags are
owned by `rem-observability-and-profiling`.

### Macro choice

- `RemEnsureCondition` / `RemEnsureVariable` — runtime-possible states, always
  active; use `RemEnsureVariable` for pointer/object checks (`Rem::IsValid`)
- `RemCheckCondition` / `RemCheckVariable` — the **development-only** family:
  `DISABLE_CHECK_MACRO` derives from `UE_BUILD_SHIPPING`, so guard *and* handling vanish there. A guard
  that must survive is `RemEnsure*`; a purely diagnostic one also gets
  `#if REM_WITH_DEVELOPMENT_ONLY_CODE`. See `references/macros-logging.md` §2c.
- **Never guard a value that is allowed to be invalid with `RemCheck*`** — guard *and*
  handling are stripped with it, so execution continues into the invalid value.
  `REM_NO_ASSERTION` only suppresses the report. For an expected miss prefer
  `RemEnsureCondition(REM_NO_ASSERTION, Cond, return {});` (one line, `LIKELY`-hinted; a no-op
  on MSVC) — or a plain `if` when the body is more than the bail-out.
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

- `check()` — program invariant. A violated check aborts in Debug/Development and is **compiled out in Shipping** (`DO_CHECK` = `USE_CHECKS_IN_SHIPPING`, default 0, so it becomes `CA_ASSUME` = a `sizeof` no-op: zero instructions and the expression is not even evaluated). Never put side effects inside, and never rely on it as a runtime guard.
- **Do not hand-wrap `check` in a development macro** — it is already build-gated; `checkSlow` costs the same outside Debug (`DO_GUARD_SLOW` follows the same pattern) and only marks the check as expensive.
- `ensure()` — recoverable "shouldn't happen"; fires once in non-shipping, returns bool.
- `ensureAlways()` — like ensure but fires every time.
- A state-invariant assert must sit beside the code that maintains that state.
  Writing `RemCheckCondition(<invariant>, return;)` as the *guard* of a state
  transition makes a legitimate transition fail the assert **and** skip the
  transition body; if the flag behind the invariant is never assigned, every
  such call is a guaranteed failure, and it surfaces as unrelated-looking test
  failures far from the assert. Guard state transitions with a plain `if`, and
  assert only for genuinely impossible states (verified 2026-09: a nested
  bind/unbind guard written this way failed 9 automation cases).
- Remove debug prints before committing.

### 14j. Checked accessors and their invalid-value twins

An accessor pair splits by contract:

- **`Get` is the checked primitive** — assertion plus the direct read: no validity
  branch, no recovery path (`TNotNull<T*>` or a reference).
- **`TryGet` reports the invalid value** — guard, then delegate to `Get`, so there is
  one read path and one assertion.
- Never the reverse (`Get` = assert + `TryGet`): the checked path would pay a validity
  branch that Shipping pays too. Same for a forwarding `operator*` / `operator->` —
  one assertion point per family.
- Exception: a lookup whose check *is* the work (`Find` + index) keeps its own
  single-lookup body; delegating would repeat it.
- A violated precondition is the caller's bug: assert it in development, read the
  payload in Shipping, and say so in the `@note`.

Worked shapes and the `REM_NO_ASSERTION` misuse: `references/macros-logging.md`
§2b.

---

## 15. Module & Plugin Conventions

`IModuleInterface` subclass + `IMPLEMENT_MODULE`; `.uplugin` declares the minimum fields; the `REM_API` alias exports precisely what consumers need — keep the exported surface minimal (Windows DLL symbol limit ~65535).

Dependencies: every module declares **each** dependency it uses in its own `Build.cs`; nothing is inherited transitively; default to and stay in `PrivateDependencyModuleNames` — `PublicDependencyModuleNames` is only for dependencies that are part of the public contract.

**A class template crossing the boundary exports its *instantiation*, not the template.** The class template stays undecorated; the owning `.cpp` writes `template class MYMODULE_API TFoo<FBar>;` and every consumer header writes an undecorated `extern template class TFoo<FBar>;`. A `dllexport` on the template itself makes consumers unable to emit their own instantiation (unresolved member symbols) and `extern template` on it is rejected with C4910. Recipe, the ordering constraint (C2908/C2766) and the rule "verify with the binary, never with intent": `references/dll-boundaries.md`.

Skeleton and examples: `references/modules.md`.

---

## 16. Test Modules & Automation Tests

Test code never lives in a runtime module: it goes in a sibling `<ModuleName>Test` module declared `"Type": "UncookedOnly"` (editor/uncooked targets only), files under `Source/<ModuleName>Test/Private/Test/*Foo.spec.cpp`, with a minimal `IMPLEMENT_MODULE(FDefaultModuleImpl, ...)`.

Dependencies flow one way, root → leaves; a base plugin's test module must not depend on plugins built on top of it; third-party libraries stay out of the BDD suites. Specs are BDD style (`DEFINE_SPEC` + `Describe`/`It`, "should ..." names); test USTRUCTs live in `Rem::<Module>::Private` and are never wrapped in `#if WITH_DEV_AUTOMATION_TESTS`; header-only templates must be instantiated by tests. Build and run with the project's actual development configuration (never a default Development editor build).

Placement table, templates and run commands: `references/tests.md`.

---

## 16b. Rider MCP Diagnostics (verified 2026-08)

Run IDE diagnostics on every changed file **before committing**: `get_file_problems` (ERROR/WARNING only) and `lint_files` (all severities). HINT severities never arrive through MCP, so declaration/member ordering is checked manually — and **MCP silence is not proof the file is clean**: in a C project context the "can be made const" family and spell-checker typos are HINT-level and do not arrive at all, while both MCP calls return only unrelated ERRORs. Sweep the whole module's `Source/` when the change touches a plugin, not just the diff files.

Known analysis false positives (Rider reports problems the compiler accepts): UTF-8 `%s` format arguments. Triage rule: an ERROR that looks like a missing include, unresolved alias or failed template substitution **in a file that compiles** is a Rider analysis bug — cross-check with the build before touching the code.

Full catalogue with the real cases: `references/rider-diagnostics.md`.

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
- [ ] Metadata completeness (§10, `references/type-mapping.md`): numeric values carry `ForceUnits`/`ClampMin`/`ClampMax` as applicable; object refs carry `AddFilterUI`/`AllowedClasses`; class refs carry `MetaClass`; wrapper arrays carry `TitleProperty`; mode-dependent values use `EditCondition`, not a comment
- [ ] Designer-facing properties that need explanation carry a `ToolTip` or a `/** */` doc comment (§10)
- [ ] No specifier text or preprocessor line sits in a comment next to a declaration or inside its specifier list (UHT turns it into the tooltip — §4)
- [ ] `TObjectPtr<T>` (not raw `T*`) for all UPROPERTY UObject members; UPROPERTY types are UPROPERTY-able (`TWeakInterfacePtr` is not — keep it non-UPROPERTY); assertion macros include their header; weak pointers use `.IsValid()` — see `references/pitfalls.md`
- [ ] Bitfields only when they actually save memory under alignment rules
- [ ] Scalar width matches the value's role (§12): no authoritative world position or accumulated world state in an `f` type (`FVector3f`/`FRotator3f`/`FTransform3f`); tuning parameters, angles and dimensionless values may use the `f` variant
- [ ] A narrow position array is a re-based local array with one `double` origin per chunk — not a world-position array stored narrow (`references/scalar-width.md` §7)
- [ ] `[[nodiscard]]` on every non-void function
- [ ] `nullptr` — never `NULL` or `0`
- [ ] `static_cast<T>()` for explicit type conversions — no C-style or functional-style casts
- [ ] `override` on every virtual function override
- [ ] `const` on all locals that are not mutated (wrapper locals too: `const auto` keeps `operator->` mutation of the pointed-to object legal)
- [ ] Literal-type locals/statics initialized with constant expressions use the `constexpr` family (`constexpr`/`consteval`/`constinit`); container/allocating types stay `const`
- [ ] `constexpr`-opportunity hints checked manually (Rider MCP does NOT return HINT severities)
- [ ] `get_file_problems` + `lint_files` run on every changed file; WEAK WARNINGs ("can be made const/constexpr") fixed; declaration/member order checked manually (HINTs not exposed)
- [ ] No `const` on value-type parameters in declarations (optional in implementation)
- [ ] `Rem::` namespace for free utility functions
- [ ] `U<Domain>Statics` UCLASS holds only Blueprint-facing `UFUNCTION`s; C++-only API is namespace free functions
- [ ] Flag/behavior parameters use a strong-typed enum, not `bool` (reuse a `Rem::Enum` one if it fits)
- [ ] `RemCommon` surveyed first before adding a new helper/enum (bottom-layer reuse module)
- [ ] `REM_API` export macro on public API types/functions; internals left unexported
- [ ] RemEnsure* for runtime-possible states; RemCheck* for developer-error guards
- [ ] Variables declared at narrowest scope; if-condition-init where possible
- [ ] `FUtf8String` for all string returns/params; `FString` only when engine API requires
- [ ] Format strings use `{}` (no numbered placeholders); no `FString::Printf`
- [ ] Build compiles with the module's `CppStandard.EngineDefault` + `ShadowVariableWarningLevel = Error`
- [ ] Every inline definition in changed headers sits at the file bottom (or in a `.cpp`) — no method/constructor bodies inside class bodies
- [ ] Data members precede function members in every visibility group (no data member after a constructor or method)
- [ ] `Build.cs` dependencies all in `PrivateDependencyModuleNames`; every consumer declares each dependency it uses itself (public headers of a dependency do NOT grant transitive include paths)
- [ ] No debug `REM_LOG_*` or `UE_LOGF` left in
- [ ] Variable/lambda parameter names are full words (no abbreviations, no single letters — `A`/`B` OK only in Sort lambdas)
- [ ] Lambda parameters in generic contexts (transrangers::transform, Sort) use explicit types, not `auto`
- [ ] Integer locals/loop counters use explicit `int32` (`auto X = 0` would deduce `int`)
- [ ] `TArray::Add` for adding existing values; `TArray::Emplace` for in-place construction or explicit ctors
- [ ] Control-flow macros avoided — repetitive `if/else` written explicitly; code deduplication done via templates in `.inl`
- [ ] Private member access via the public API when one exists — plain getters are writable through their non-const overload (a setter is preferred for writes); `REM_DEFINE_PRIVATE_MEMBER_ACCESSOR` only when no public getter exists (`CONST_ONLY` getters are read-only)
- [ ] No structured bindings (`auto [a, b]` — use explicit `Pair.Key` / `Pair.Value`)
- [ ] `TInstancedStruct` two-arg copy-initialization uses `InitializeAsScriptStruct(Struct, Memory)` — never the template `InitializeAs<T>` with (struct, memory) args (C2661)
- [ ] After a Rider `reformat`, long UPROPERTY `meta`/`EditCondition` string literals are still intact (reformat can split them mid-string → UHT "Unterminated character constant")
- [ ] Comments: `/** */` Doxygen on header declarations; `//` in `.cpp` implementations; no `///`
- [ ] Comments minimal — the default is none: nothing narrates the code it sits on, and a fact that needed explaining is carried by a rename, a type or a named constant instead
- [ ] Comments concise, non-repetitive, consistent — explain *why*/*invariants*, never restate the code; one comment per concept; overview comments (file/type/section purpose) are worth writing
- [ ] No `} // namespace Xxx` closing comments — bare `}`
- [ ] Function bodies stay at one level of abstraction — no high-level intent mixed with low-level mechanics
- [ ] Elegance proxies (§13): no dead or commented-out code, no unused parameters, no unreferenced helpers
- [ ] Elegance proxies (§13): no premature abstraction — every base/interface/template has a real second user or a stated plan
- [ ] Elegance proxies (§13): no hidden side effects — getters do not mutate, constructors do not touch the world, queries do not allocate unbounded
- [ ] Elegance findings are capped at three per review, each with a concrete alternative (§13)
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
- Scalar width (float vs double): [references/scalar-width.md](references/scalar-width.md)
- Naming & formatting details: [references/naming-formatting.md](references/naming-formatting.md)
- File & include layout: [references/file-layout.md](references/file-layout.md)
- Language features: [references/language-features.md](references/language-features.md)
- Design & zero-overhead: [references/design.md](references/design.md)
- Module & plugin conventions: [references/modules.md](references/modules.md)
- DLL boundaries & template instantiation: [references/dll-boundaries.md](references/dll-boundaries.md)
- Macro & logging signatures: [references/macros-logging.md](references/macros-logging.md)
- Verified pitfalls: [references/pitfalls.md](references/pitfalls.md)
- Rider diagnostics: [references/rider-diagnostics.md](references/rider-diagnostics.md)
- Test module templates & commands: [references/tests.md](references/tests.md)
