# Test Module Reference

Templates, the module placement table and the verified gotchas for the
dedicated test module. Test *rules* live in `SKILL.md` §16; whether a change's
tests are *complete* (the pre-commit gate) is owned by `rem-test-completeness`;
the headless run command itself — the one that carries the project's paths and
filter — is owned by `rem-commit-workflow`.

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

> Host note: the forms below are Windows/Win64. On other hosts substitute the
> platform's script suffix (`.sh` for `.bat`), the platform directory
> (`<Platform>` for `Win64`), and drop the `.exe` suffix.

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

## 8. NetSerialize round-trip archive choice (verified 2026-08)

Round-trip a custom `NetSerialize` with **`FMemoryWriter`/`FMemoryReader`**, not
`FBitWriter`/`FBitReader`. Some serializers depend on the archive's network
versioning state — `FGameplayTag::NetSerialize_Packed` reads
`Ar.EngineNetVer()` and the tag manager's packed-index parameters, which a bare
`FBitWriter` does not carry, so the bit-archive round-trip fails in the test
harness. Real RPC serialization uses a versioned `FNetBitWriter` and works; the
memory-archive round-trip validates save/load symmetry without that harness
noise. Don't chase bit-archive round-trips in unit tests.

## 9. Fixture semantics depend on configuration (verified 2026-08)

A behavior contract can differ under different configurations of the same
system — a test that asserts one configuration's semantics fails on another.
Example: inventory `CanAddItem` overwrites a same-kind slot in a
non-stacking group but **merges** counts in a stacking group (MaxStack > 0).
When a config flag changes semantics, the fixture must exercise **both**
configurations, and each case must state which one it asserts. A single-config
fixture silently locks in one branch and the other rots.
## 10. Module placement

Test code never lives in a runtime module — it goes in a dedicated test module
sibling to the module under test:

| Concern | Convention |
|---------|-----------|
| Module | `<Plugin>/Source/<ModuleName>Test` (e.g. `RemCommon` → `RemCommonTest`) |
| `.uplugin` type | `"Type": "UncookedOnly"` — compiled only into editor/uncooked targets, never into packaged builds |
| Test files | `Source/<ModuleName>Test/Private/Test/`, named `*Foo.spec.cpp` |
| Module impl | Minimal `IMPLEMENT_MODULE(FDefaultModuleImpl, <ModuleName>Test)`; a module without `IMPLEMENT_MODULE` loads but fails to initialize ("could not be initialized successfully") |
| Dependencies | The runtime module under test + Core/CoreUObject/Engine; `RemSharedModuleRules.Apply(this)` |

## 11. Dependency hygiene (verified 2026-08)

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
  tests; the BDD specs test the Rem wrapper/integration only.
- **Empty shell modules** — `StructUtils` merged into CoreUObject, so listing it
  produces a "does not list plugin" warning; the fix is to **remove** the
  dependency, not to add the plugin listing (owned by `references/modules.md`).

## 12. Template headers need instantiation

A header-only template with no in-repo consumer compiles nothing — errors
(wrong `auto` deduction, MSVC overload quirks with `TNotNull` arithmetic,
missing includes) stay latent until first instantiation. Every template header
shipped in the repo must be instantiated by tests; this is the primary purpose
of the test module.

## 13. Capture devices and the dev-only config matrix (verified 2026-09)

### The capture device must declare itself multi-threaded

A test capture device sees its lines **synchronously only while it is
unbuffered**. The engine's log redirector delivers a **buffered** device its
output asynchronously, on a dedicated log thread, so a device that does not
report itself safe for multiple threads loses lines or races against the case's
assertion phase — even though the writing call already returned. Declare the
device multi-threaded (the engine's own automation test output device does)
before trusting it to capture everything the scope produced.

Two ordering facts of the same mechanism:

- **Arm the capture after the backlog replay.** The redirector replays buffered
  backlog first; arming before the replay counts lines the case did not produce.
  Arm after the replay, then run the assertion scope.
- **The ensure-report path has its own handler-scope pattern.** An `ensure`
  report does not travel the ordinary log-redirector route, so a capture device
  alone never sees it — use the handler-scope pattern that mechanism documents.

### The dev-only config matrix

A case that asserts a development-only report must be compiled out wherever
that report cannot exist, or it goes red in a configuration that is working as
designed. One condition per report kind:

| Report kind | Condition the case needs |
|---|---|
| `ensure` report | `DO_ENSURE` |
| log report | the logging-enabled condition (the `NO_LOGGING` switch the engine's log macros derive from) |
| the mechanism's own development-only blocks | the development-only macro (`REM_WITH_DEVELOPMENT_ONLY_CODE`, `SKILL.md` §14) |

`UE_BUILD_TEST` is the trap: it is a **middle configuration** — ensures and
logging are off while the non-shipping guards are still compiled in. A bare
`#if <dev-only macro>` therefore compiles such a case in there and turns it red,
although the configuration is correct.

Guard **per case**, not per file: the counter cases and the behaviour case need
different conditions, so one file-level guard both hides cases that could run and
keeps cases that cannot.

## 14. Tick-order prerequisites: observe with a probe, not with spawn order (verified 2026-09)

A tick prerequisite is a claim about **tick order**, and nothing static shows it.

- **Engine semantics** — `AController::AddPawnTickDependency(Pawn)` calls
  `Pawn->PrimaryActorTick.AddPrerequisite(Controller, Controller->PrimaryActorTick)`, and a
  prerequisite tick function runs **first**: the **controller ticks before the pawn**, contrary to the
  naive reading of the method name (verified in the engine source and at runtime).
- **How to test it** — spawn a probe actor that also ticks and records "how many times the other side
  had ticked when I ticked"; assert on those counts. Pin the baseline order with explicit tick groups
  rather than spawn order (`Pawn->PrimaryActorTick.TickGroup = TG_PrePhysics;`,
  `Controller->PrimaryActorTick.TickGroup = TG_DuringPhysics;`). Never depend on spawn order or on
  `TSet` iteration order, and do not route the assertion through a query API a behaviour change could
  also pass.
- **Falsification** — replacing the `Add` call with a no-op turns two assertions red; replacing the
  matching `Remove` with a no-op turns the other two red; restoring both returns the suite green.
  Produce that four-way red/green before trusting the probe.

BDD spec style, the test-USTRUCT namespace rules and the build/run
configuration are stated once each: style and the namespace rules in §1–§2 +
`SKILL.md` §16, the DebugGame configuration and the headless run command in §4
+ `rem-commit-workflow`.

---
