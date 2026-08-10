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
