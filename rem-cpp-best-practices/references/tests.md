# Test Module Reference

Complete boilerplate and commands for the dedicated test module. Rules and
placement conventions live in the main SKILL.md (§16); this file holds the
templates.

---

## 1. Spec file template

BDD style is the project convention: `DEFINE_SPEC` + `Describe`/`It` with
behavior-describing `It` names ("should ..."). Failure output shows the full
Describe/It hierarchy. `IMPLEMENT_SIMPLE_AUTOMATION_TEST` is only for one-off
smoke checks.

```cpp
// Foo.spec.cpp
#include "Test/FooTestStructs.h"

#include "Misc/AutomationTest.h"
#include "Foo.h"

#if WITH_DEV_AUTOMATION_TESTS

DEFINE_SPEC(FFooTest, "Rem.<Module>.Foo",
    EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::ProductFilter);

void FFooTest::Define()
{
    Describe(TEXT("Emplace"), [this]
    {
        It(TEXT("in-place constructs and reads back"), [this]
        {
            TestTrue(TEXT("..."), Condition);
            TestEqual(TEXT("..."), Actual, Expected);
            TestNotNull(TEXT("..."), Pointer);
        });
    });
}

#endif // WITH_DEV_AUTOMATION_TESTS
```

Types from the test structs header (namespace `Rem::<Module>::Private`) need
`using` declarations at the top of the spec:

```cpp
using Rem::Foo::Private::FTestFoo;
using Rem::Foo::TContainerUnderTest;
```

## 2. Test USTRUCTs header template

```cpp
#pragma once

#include "CoreMinimal.h"

// generated.h MUST be included BEFORE the type declarations: GENERATED_BODY()
// expands to a macro defined here; a trailing include leaves it undefined (C4430).
// UHT emits a matching forward declaration inside the namespace, so the include
// stays outside it.
#include "FooTestStructs.generated.h"

namespace Rem::Foo::Private
{
USTRUCT()
struct FTestFoo
{
    GENERATED_BODY()

    UPROPERTY()
    int32 Value{};
};
}
```

UHT restrictions (verified on UE 5.8):

- `USTRUCT` / `UPROPERTY` must NOT be wrapped in `#if WITH_DEV_AUTOMATION_TESTS`
  (only `WITH_EDITORONLY_DATA` is allowed). Leave the structs unguarded; the spec
  `.cpp` is guarded, so non-test builds carry no test code.
- Namespace USTRUCTs are fully processed by UHT: `StaticStruct()`, reflection
  copy, and destruction all work (`InitializeStruct`/`CopyScriptStruct`/
  `DestroyStruct` run as usual).

### Tracking constructions/destructions

To assert exactly-once destruction, give a test USTRUCT a counter in its
ctor/dtor (plain struct in the same namespace, static `int32`):

- The default ctor must write a **non-zero** member value on purpose: a
  zero-initialized struct gets flagged `STRUCT_ZeroConstructor` by the engine
  and `InitializeStruct` memzeros instead of calling the ctor, breaking the
  counter symmetry.
- Copy/move ctors increment, the destructor decrements; `Emplace` (placement
  new) and `Add` (`InitializeStruct` + `CopyScriptStruct`) both stay balanced.

## 3. Module boilerplate

`Source/<ModuleName>Test/Private/RemCommonTestModule.cpp` — the only required
implementation file:

```cpp
// Copyright RemRemRemRe. {Year}. All Rights Reserved.

#include "Modules/ModuleManager.h"

// The test module only hosts automation tests; it needs no startup/shutdown logic.
IMPLEMENT_MODULE(FDefaultModuleImpl, <ModuleName>Test);
```

`<ModuleName>Test.Build.cs`:

```csharp
// Copyright RemRemRemRe. {Year}. All Rights Reserved.

using UnrealBuildTool;
using Rem.BuildRule;

public class <ModuleName>Test : ModuleRules
{
	public <ModuleName>Test(ReadOnlyTargetRules target) : base(target)
	{
		RemSharedModuleRules.Apply(this);

		PrivateDependencyModuleNames.AddRange(
			[
				"Core",
				"CoreUObject",
				"Engine",

				"<ModuleName>",
			]
		);
	}
}
```

`.uplugin` registration — the test module is `UncookedOnly`, so it compiles
only into editor/uncooked targets and never enters packaged builds:

```json
{
    "Name": "<ModuleName>Test",
    "Type": "UncookedOnly",
    "LoadingPhase": "Default"
}
```

## 4. Build & run commands

Use the configuration the project actually develops with — never default to a
Development editor build. This project's development configuration is
**DebugGame Editor**; check `<project>/Source/*.Target.cs` or team convention
when in doubt.

```
<engine>/Build/BatchFiles/Build.bat <ProjectName>Editor Win64 DebugGame -Project=<project>.uproject -WaitMutex
```

Editor binaries encode their configuration in the file name — always run the
binary that matches the configuration you built:

| Configuration | Binary |
|---------------|--------|
| Development | `UnrealEditor-Cmd.exe` (no suffix) |
| Debug | `UnrealEditor-Win64-Debug-Cmd.exe` |
| DebugGame | `UnrealEditor-Win64-DebugGame-Cmd.exe` |

Headless run:

```
<engine>/Binaries/Win64/UnrealEditor-Win64-DebugGame-Cmd.exe <project>.uproject -unattended -nopause -nullrhi
    -ExecCmds="Automation RunTests Rem.<Module>.<Foo>; Quit" -TestExit="Automation Test Queue Empty" -log
```

Check `Saved/Logs/<Project>.log` for `Test Completed. Result={Success}` lines.
Third-party editor plugins that crash under `-nullrhi` may need
`-DisablePlugins=<Name>`.

### Headless run gotchas (verified 2026-08)

- The automation filter is **not** a wildcard: `Rem.*` is a literal substring
  match and matches nothing. Use `StartsWith:Rem` (prefix) —
  `Automation RunTests StartsWith:Rem; Quit` runs the whole suite. `+`
  separates OR-filters: `Rem.Foo+Rem.Bar`.
- The runner counts **Describe nodes as test entries too** —
  `Found 725 automation tests` = 687 `It` cases + 38 `Describe` nodes.
- Negative tests must NOT trigger assertion log events: `RemCheck*`,
  `REM_VIRTUAL_WARN` defaults, and `ensure` failures emit Error log events that
  the automation framework attaches to the current test and marks it failed —
  even when the early-return behavior is what the test wants to verify. Only
  test paths that do not trip those macros.
- Editor plugins can crash the render thread under `-nullrhi` (observed with a
  custom node graph plugin) — use `-DisablePlugins=<Name>`; expect EXIT 3 with
  `EXCEPTION_ACCESS_VIOLATION` in the log otherwise.
- Run the binary matching the built configuration; mismatches silently load
  stale modules.

## 5. Assertion pitfalls (verified 2026-08)

| Pattern | Problem | Fix |
|---|---|---|
| `TestEqual(TEXT("..."), FloatA, FloatB)` with `auto`/macro-typed floats | Overload ambiguity (C2666) when one side is a macro constant like `UE_KINDA_SMALL_NUMBER` (a double literal) | Use the tolerance overload, or `TestTrue(FMath::IsNearlyEqual(A, B, Tol))`, or `static_cast` both sides |
| `TestEqual(TEXT("..."), PtrA, PtrB)` | No pointer overload; template deduction fails on `const`-mismatched pointers | `TestTrue(PtrA == PtrB)` / `TestNull` / `TestNotNull` |
| `TestEqual` on `enum class` | No enum overload | `static_cast<int32>(...)` both sides |
| `TestEqual` on `TSubclassOf` / `TObjectPtr` wrappers | No overload | `TestTrue(A == B)` (wrapper `==` exists) |
| `TestTrue(TEXT("..."), true)` | Placeholder assertion — reviewer should flag it | Never write one; assert a real condition |

## 6. Reflection round-trip pitfall: byte-copy aliasing (verified 2026-08)

`UScriptStruct::CopyScriptStruct` is a **byte copy** for USTRUCTs without
`STRUCT_CopyNative` ops — it does not call member copy constructors. A
round-trip test that copies a struct containing owning members (`FString`,
`TArray`, `FInstancedStruct`) aliases their heap buffers and double-frees on
destruction — heap corruption that surfaces far away from the test.

Rules:

- Round-trip payloads must be **POD-safe** (scalars, plain pointers, nested
  POD structs). Document the contract in the payload's comment.
- `FRemInstancedStructContainer` / engine containers copy through
  `CopyScriptStruct` — owning members there are fine because the container
  owns the storage; the pitfall is specifically **stack structs copied in
  tests**.
- Same pitfall applies to `FMemory::Memcpy`-style "deep copy" helpers — verify
  what "copy" means before round-tripping.

## 7. Shared helpers and fixtures (verified 2026-08)

- `MakeNotNull` explicit template argument is the **pointed type**, not the
  pointer type: `MakeNotNull(SomePtr)` or `MakeNotNull<UThing>(Ptr)` —
  `MakeNotNull<UThing*>(Ptr)` is `UThing**`.
- `TNotNull` has no `Get()`; compare via `operator==` or `static_cast` through
  the implicit pointer conversion.
- `UObject` and `UActorComponent` are abstract in current engine versions:
  `NewObject<UObject>()` logs an abstract-class warning that fails the test
  via its log event. Use concrete classes (`AActor` in a test world,
  `UInputComponent`, ...).
- `ACharacter::Mesh` is private — the private-member accessor macro reaches it:
  `REM_DEFINE_PRIVATE_MEMBER_ACCESSOR(...)` then `Accessor::Access(*Character)`.
- Test worlds (`FRemTestWorld`-style) must flush render-thread pending
  cleanups (`FlushRenderingCommands()`) before garbage collection in the
  destructor, or long suites crash in `FPendingCleanupObjects::~`.
- Objects holding struct views of **stack payloads** must clear the view
  before the payload dies (e.g. reset before the test ends) — otherwise a
  later GC destroys the dangling view and corrupts the heap.
- `strong_alias` macros (`STRONG_ALIAS`, `STRONG_ALIAS_EXPLICIT_CONVERSION`)
  require a **trailing semicolon** under MSVC: `STRONG_ALIAS(...);` — without
  it the next declaration fails to parse (C2236).
- `TGenerator` (UE5Coro) starts eagerly to the first `co_yield`
  (`initial_suspend = suspend_never`): iterate with range-for / `CreateIterator`;
  `while (Generator.Resume()) { use(Current()); }` silently skips the first
  value.

## 8. Dependency hygiene (verified 2026-08)

- Test modules follow the runtime layering one-way: a base plugin's test
  module must not depend on leaf plugins (or their test modules).
- Third-party libraries stay out of the BDD suites — they ship their own
  tests; the BDD specs test the Rem wrapper/integration only.
- Empty shell engine modules are not listed at all: `StructUtils` merged into
  CoreUObject (`CoreUObject/Public/StructUtils/` hosts the headers); listing
  `"StructUtils"` produces "Plugin does not list plugin" warnings and the fix
  is to **remove** the dependency, not to add the plugin listing.
- When a dependency only triggers "does not list plugin ..." warnings and its
  headers are visible inside a module already depended on — drop it.

