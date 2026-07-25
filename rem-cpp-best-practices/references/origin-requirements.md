# Origin Requirements — rem-cpp-best-practices Skill

This file records the original design requirements and source material used to create
`SKILL.md`. Use this when regenerating or upgrading the skill to ensure consistency
with the original intent.

**Invocation model**: This is a **manual, explicit-invoke** skill (`trigger: manual`).
It is designed for pre-commit review, not for code generation. Rider handles
formatting and mechanical inspections automatically during coding.

## Source of truth

The coding patterns documented in this skill are derived from the following sources,
listed in priority order:

1. **RemCommon plugin** — the project's reference codebase. When SKILL.md says
   "RemCommon style", this is the reference.

2. **Landelare conventions** (<https://landelare.github.io/2022/06/23/epic-conventions.html>)
   — where Landelare recommendations conflict with Epic's official standard, Landelare
   takes priority unless RemCommon code disagrees.

3. **Epic C++ Coding Standard** (<https://dev.epicgames.com/documentation/unreal-engine/epic-cplusplus-coding-standard-for-unreal-engine>)
   — the baseline for all Unreal Engine C++. Followed unless overridden by Landelare
   or RemCommon.

4. **CppCoreGuidelines** (<https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines>)
   — general C++ best practices that inform zero-overhead, const correctness, etc.

5. **SOLID principles** — Single Responsibility, Open/Closed, Liskov Substitution,
   Interface Segregation, Dependency Inversion.

## Rider / IDE configuration files

- Code Style: solution-level `.sln.DotSettings` (project formatting rules)
- Code Style: user-level `.uprojectdirs.DotSettings` (personal defaults)
- Code Inspections: exported `.DotSettings` inspection profile
- Code Style XML: exported code style XML
- Code Insight: exported code insight XML

Key inspection settings extracted:
- `CppParameterMayBeConst` → SUGGESTION
- `CppUEBlueprintCallableFunctionUnused` → HINT
- `CppUEBlueprintImplementableEventNotImplemented` → HINT
- `CppUseFamiliarTemplateSyntaxForGenericLambdas` → DO_NOT_SHOW
- `CppUseStructuredBinding` → DO_NOT_SHOW

Key formatting settings extracted:
- Indent style: Spaces, 4-width
- Function declaration style: TrailingReturnType
- Auto common case: WhenTypeIsEvident
- Uniform initialization in NSDMIs: True
- Namespace indentation: Inner

## Build configuration (from `Rem::BuildRule::RemSharedModuleRules`)

All shared build flags are centralized in `Rem::BuildRule::RemSharedModuleRules::Apply`
(defined in `RemCommon.Build.cs`). Every module calls this single method:

```csharp
using Rem.BuildRule;
// ...
RemSharedModuleRules.Apply(this);
```

What `Apply` configures:
```csharp
target.CppStandard = CppStandardVersion.EngineDefault;
target.IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
target.DefaultBuildSettings = BuildSettingsVersion.Latest;
target.CppCompileWarningSettings.ShadowVariableWarningLevel = WarningLevel.Error;
target.CppCompileWarningSettings.UnsafeTypeCastWarningLevel = WarningLevel.Warning;
target.CppCompileWarningSettings.NonInlinedGenCppWarningLevel = WarningLevel.Warning;
target.bUseUnity = false;
target.bAllowUETypesInNamespaces = true;
```

## Design decisions & rationale

### Why `auto` is liberal, not restrictive

Landelare argues that `auto` prevents implicit float→double conversions (proven
during UE4→UE5 LWC porting) and catches type mismatches. RemCommon code consistently
uses `auto*` and `auto&` with explicit decoration. The Rider setting `WhenTypeIsEvident`
confirms this project-level choice.

### Why no `const` on value locals

Landelare: "const locals add noise and prevent move optimization." RemCommon code
does not use `const` on value-type locals (e.g., `int32 Count`, `auto Result`).
References and pointers-to-const still use `const`.

### Why no structured bindings

Asked the user: "Does IDE/debugger support for structured bindings work?" Answer:
No, variables show as unviewable in VS/Rider debugger. Therefore, structured
bindings are not used in this project.

### Why float literals stay typed

`1.0f` for float, `1.0` for double. Landelare suggested `0`/`1` to work for both,
but implicit double→float conversion has overhead. Match the destination type.

### Why STL for `<type_traits>` and `std::atomic`

Epic has officially deprecated `TEnableIf`, `TIsSame`, etc. in favor of `<type_traits>`.
`std::atomic` is the officially-preferred atomic per Epic documentation.

### Why UE types for containers, `TFunctionRef`

These are required for UPROPERTY reflection, engine interaction, and GAS/latent
action compatibility. No STL alternative works with the reflection system.

### Why `FUtf8String` over `FString`

`FUtf8String` (UTF-8) is the primary string type for all new code. `FString` (wide,
`TCHAR`) is legacy. Both work as UPROPERTY. Reasons:
- UTF-8 is more compact (1 byte per ASCII char vs 2), reducing memory and cache pressure
- `Rem::Format` delegates to `fmt::format_to` which natively targets UTF-8 builders
- The `fmt` library's `fmt::formatter` specialization bridges all UE types to UTF-8 via `Rem::ToString`
- Engine APIs that still require `FString` are converted to `FUtf8String` immediately after the call

### Why `if constexpr` chains over SFINAE

RemCommon code uses `if constexpr` + concepts almost exclusively. This is C++17+
and provides clearer error messages, especially with `always_false<T>`.

### Naming prefix conventions

- `U`/`A`/`F`/`E`/`I`/`T` from Epic standard (UHT enforced)
- `C` prefix for concepts — follows RemCommon convention (e.g., `CUObject`, `CStringable`)
- `b` prefix for booleans — Epic standard, and it enables UE naming-based tooling
- `Rem` namespace prefix — project convention for all free utilities

### Why `REM_API` alias for the export macro

Each module's `*_API` macro (e.g., `REMSOMETHING_API`) is auto-generated by UBT,
but the name varies per module. The `#define REM_API <MODULE>_API` pattern keeps
declarations clean: every file writes `REM_API` instead of the module-specific name.
This mirrors the pattern in `RemCommonLog.h`:

```cpp
#define REM_API REMCOMMON_API
REM_API DECLARE_LOG_CATEGORY_EXTERN(LogRemCommon, Log, All);
#undef REM_API
```

### Why minimum viable export, not "export everything"

Windows DLLs have a hard limit of 65535 exported symbols per module. Exporting
unnecessary internal symbols risks hitting this limit and bloats the DLL interface.
Only types and functions consumed by other modules should be exported. Internal
implementation details (helper classes, private free functions) stay unexported.

### Why spaces over tabs for indentation

Spaces (4-width) provide consistent rendering across all editors, diffs, and code
review tools. No tab-width disagreement between team members.

### Why data members before function members

Placing data before functions in type declarations gives readers immediate context
about what state the type holds before showing how it operates on that state.
Each visibility group (public/protected/private) spans both data and functions.

### Why `auto` whenever readability is not harmed

Redundant type information adds noise. When the type is obvious from context
(`Cast<T>()`, `NewObject<T>()`, structured code), `auto` removes noise and lets
the reader focus on intent. Use explicit decoration `auto*`, `auto&`, `const auto&`
to signal pointer/reference semantics.

### Why no `const` on value parameters in declarations

Adding `const` to value parameters in headers is a call-site irrelevant detail —
the caller passes by value and the callee owns a copy. Omitting `const` in the
declaration (header) keeps the API clean. Adding `const` in the implementation
(`.cpp`) is optional for correctness inside the function body.

### Why bitfields only when they save space

Under alignment rules, a lone `uint8 bFlag : 1` may not save any memory if the
compiler pads to the next alignment boundary anyway. Only use bitfields when
multiple flags are packed together into the same byte and actually reduce the
struct size.

### Why RemEnsureCondition / RemEnsureVariable (assertion macros)

Two orthogonal concerns are separated: what to validate (condition vs variable)
and how to assert (ensure vs check vs crash). The macros use `REM_MULTI_MACRO`
to accept 1/2/3 arguments:

```
RemEnsureCondition(ensureAlways, bInitialized, return;)   // 3 args: macro + condition + handling
RemEnsureCondition(bInitialized)                           // 1 arg:  condition only (defaults to ensureAlways)
RemEnsureVariable(MoverComp, return;)                      // 2 args: variable + handling (uses Rem::IsValid)
RemEnsureVariable(check, MoverComp, return;)               // 3 args: macro + variable + handling
```

- The first optional arg selects the assertion macro (`ensure`, `ensureAlways`, `check`, `verify`)
- The last optional arg is the invalid-handling statement (typically `return;`)
- `RemEnsureVariable` validates via `Rem::IsValid(Pointer)`; `RemEnsureCondition` takes a raw bool expression
- `RemCheck*` is currently an alias for `RemEnsure*` (gated by `DISABLE_CHECK_MACRO`)
- `REM_LET_IT_CRASH` strips handling statements so failures are fatal

### Why `Rem::Format` with `fmt::format_to` instead of `FString::Format` / `FString::Printf`

`fmt` is a high-performance, widely-used C++ formatting library. Reasons:
- Compile-time format string validation (catches argument count/type mismatches)
- Zero-allocation `fmt::format_to` into `TStringBuilderBase<CharType>`
- `{}` placeholder syntax (no numbers needed — `fmt` infers argument order)
- Generic `fmt::formatter` specialization bridges all `CStringable` types through `Rem::ToString`
- Future-proof: `fmt` is the basis for C++20 `std::format`

### Why `Category = "Rem"` / `"Rem|..."` exclusively

All UPROPERTY/UFUNCTION categories use the `"Rem"` root, optionally with a
sub-category via `"Rem|SubName"`. Bare categories like `"Component"` are not
allowed — they scatter editor entries across the Details panel. The root
ensures all project types group together under one expandable section.

### Include order rationale

Base class header first (technical requirement), then generated.h last (UHT
requirement), forward declarations after all #includes. Empty-line separation
between groups improves readability without adding boilerplate.

## Inspiration sources

- <https://github.com/Jeffallan/claude-skills/tree/main/skills/cpp-pro> — modern C++
  skill structure and reference organization
- <https://github.com/ElCapor/cpp-pro> — alternative cpp-pro skill (README not found,
  but the concept was noted)

## Regeneration notes

When regenerating this skill:
1. Re-read RemCommon source code for any style evolution
2. Check if Landelare blog has updates
3. Re-export Rider settings if they changed
4. Verify CppStandard version in engine (could change with new UE versions)
5. Check if debugger support for structured bindings has improved (re-evaluate)
6. Review if new C++23 features should be adopted
7. Verify `RemSharedModuleRules.Apply` still covers all required build flags
8. Check if `FUtf8String` / `FAnsiString` usage patterns changed (currently: UTF-8 primary, ANSI unused)
9. Review `fmt` library version and any API changes in format string conventions
10. Verify assertion macro signatures in `RemAssertionMacros.h` still match the 1/2/3-arg overload pattern
