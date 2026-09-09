# Observability & Profiling API Tables

Signatures and headers for the APIs referenced by `SKILL.md`. Load when writing
the instrumentation itself; the when/what rules live in `SKILL.md`.

Headers are engine-relative under `Engine/Source/Runtime/`. Last reviewed:
2026-09 — confirm the exact path and macro definition in your engine version
before citing it elsewhere.

---

## 1. Log categories

```cpp
// Header — declaration (usable from other translation units):
DECLARE_LOG_CATEGORY_EXTERN(LogFoo, Log, All);

// One .cpp — definition:
DEFINE_LOG_CATEGORY(LogFoo);

// File-local category (not exported):
DEFINE_LOG_CATEGORY_STATIC(LogFooLocal, Log, All);
```

| Parameter | Meaning |
|---|---|
| `DefaultVerbosity` | verbosity used at runtime before config overrides |
| `CompileTimeVerbosity` | verbosity compiled out above this level — set it deliberately to strip detail from shipping |

- Header: `Core/Public/Logging/LogMacros.h`
- Runtime verbosity can be changed without a rebuild via the log config, but
  anything above `CompileTimeVerbosity` does not exist in that build.
- Structured logging (UE 5.2+): `UE_LOGFMT(LogFoo, Warning, "Value {Value}", ("Value", Value))`
  with `#include "Logging/StructuredLog.h"` — prefer it for new code where the
  format string is a literal; it is compile-time checked.

## 2. Debug drawing — `Engine/Public/DrawDebugHelpers.h`

```cpp
void DrawDebugLine(const UWorld* World, FVector Start, FVector End,
    FColor Color, bool bPersistentLines = false, float LifeTime = -1.0f,
    uint8 DepthPriority = 0, float Thickness = 0.0f);

void DrawDebugSphere(const UWorld* World, FVector Center, float Radius,
    int32 Segments, FColor Color, bool bPersistentLines = false,
    float LifeTime = -1.0f, uint8 DepthPriority = 0, float Thickness = 0.0f);

void DrawDebugBox(const UWorld* World, FVector Center, FVector Extent,
    FColor Color, const FQuat& Rotation, bool bPersistentLines = false,
    float LifeTime = -1.0f, uint8 DepthPriority = 0, float Thickness = 0.0f);

void DrawDebugString(const UWorld* World, FVector TextLocation, const FString& Text,
    AActor* TestBaseActor = nullptr, FColor TextColor = FColor::White,
    float Duration = -1.0f, bool bDrawShadow = false, float FontScale = 1.0f);

void DrawDebugCircle(...);   // 2D ring, axis-selectable
void DrawDebugArrow(...);    // line + head
void DrawDebugPoint(...);    // cheap point
void DrawDebugFrustum(...);  // camera/frustum visualization
```

| Parameter | Trap |
|---|---|
| `bPersistentLines` + `LifeTime = -1` | geometry stays until the world resets — always pass a finite lifetime or clear the batch |
| `DepthPriority` | default `0` (depth-tested); `SDPG_Foreground` draws through geometry — needed for occluded markers, and it is easy to forget |
| `Thickness` | `0` is a 1-pixel line; set it for visibility on high-DPI |
| `Duration` on `DrawDebugString` | `-1` means one frame |

Guards:

```cpp
#if ENABLE_DRAW_DEBUG
    DrawDebugSphere(GetWorld(), Center, Radius, 12, FColor::Green, false, 0.0f);
#endif
```

`ENABLE_DRAW_DEBUG` is 0 in Shipping/Test configurations — confirm the macro's
current definition in your engine version. For a runtime toggle, gate on a cvar
or a gameplay debugger category instead of a compile-time switch.

Screen messages: `GEngine->AddOnScreenDebugMessage(Key, TimeToDisplay, Color, Text)`
(`Engine/Public/Engine.h`). A stable `Key` replaces the existing line; `-1` adds a
new line every call and stacks until the screen is full.

## 3. Tooling hooks

| Hook | API | Header |
|---|---|---|
| Console variable | `TAutoConsoleVariable<T>` / `FAutoConsoleVariableRef` | `Core/Public/HAL/IConsoleManager.h` |
| Console command | `FAutoConsoleCommand`, `FAutoConsoleCommandWithWorld`, `FAutoConsoleCommandWithWorldAndArgs` | same |
| Gameplay debugger category | `FGameplayDebuggerCategory` (`CollectData`, `DrawData`) | `GameplayDebugger/Public/GameplayDebuggerCategory.h` |
| Visual logger | `UE_VLOG(Owner, CategoryName, Verbosity, Format, ...)`, `UE_VLOG_LOCATION`, `UE_VLOG_SEGMENT` | `Engine/Public/VisualLogger/VisualLogger.h` |
| Insights trace channel | `UE_TRACE_CHANNEL_DEFINE(Channel)` / `UE_TRACE_CHANNEL(Channel)` | `Core/Public/Trace/Trace.h` (UE 5.0+) |

Console variable with a help string (the string is the documentation):

```cpp
static TAutoConsoleVariable<bool> CVarFooEnabled(
    TEXT("Foo.Enabled"),
    true,
    TEXT("Enable the Foo subsystem. Default: true. Takes effect immediately."),
    ECVF_Default);
```

Gameplay debugger category skeleton:

```cpp
class FDebugCategory_Foo : public FGameplayDebuggerCategory
{
public:
    FDebugCategory_Foo();
    virtual void CollectData(APlayerController* OwnerPC, AActor* DebugActor) override;
    virtual void DrawData(APlayerController* OwnerPC,
        FGameplayDebuggerCanvasContext& CanvasContext) override;

    static TSharedRef<FGameplayDebuggerCategory> MakeInstance();
};
```

## 4. Profiling

### CPU profiler scopes — `Core/Public/Trace/TraceMacros.h` (CpuProfiler)

```cpp
TRACE_CPUPROFILER_EVENT_SCOPE(Name);                    // static, literal name
TRACE_CPUPROFILER_EVENT_SCOPE_STR(Name);                // dynamic name — allocates
TRACE_CPUPROFILER_EVENT_SCOPE_ON_CHANNEL(Name, Channel);// custom trace channel
TRACE_CPUPROFILER_EVENT_SCOPE_TEXT(Name);               // preformatted text
```

Static names are the default; `_STR` exists for data-driven names and costs an
allocation per entry.

### Cycle stats — `Core/Public/Stats/Stats.h`

```cpp
DECLARE_CYCLE_STAT(TEXT("Foo Update"), STAT_FooUpdate, STATGROUP_Foo);
DECLARE_SCOPE_CYCLE_COUNTER(TEXT("Foo Update"), STAT_FooUpdate, STATGROUP_Foo);

void Update()
{
    SCOPE_CYCLE_COUNTER(STAT_FooUpdate);
    // ...
}
```

Group declaration — `Core/Public/Stats/Stats2.h`:

```cpp
DECLARE_STATS_GROUP(TEXT("Foo"), STATGROUP_Foo, STATCAT_Advanced);
DECLARE_STATS_GROUP_VERBOSE(TEXT("Foo Detail"), STATGROUP_FooDetail, STATCAT_Advanced);
DECLARE_STATS_GROUP_SORTBYNAME(TEXT("Foo"), STATGROUP_Foo, STATCAT_Advanced);
```

| Variant | Effect |
|---|---|
| `DECLARE_STATS_GROUP` | normal group |
| `_VERBOSE` | hidden unless verbose stats are enabled — for high-cardinality detail |
| `_SORTBYNAME` | entries sorted by name instead of by declaration — large groups |

### CSV profiling — `Core/Public/Stats/Stats.h`

```cpp
CSV_DEFINE_CATEGORY(Foo, true);                       // in one .cpp
CSV_DECLARE_CATEGORY_MODULE_EXTERN(MODULE_API, Foo);  // in the consuming header

CSV_SCOPED_TIMING_STAT(Foo, Update);                  // duration
CSV_CUSTOM_STAT(Foo, ItemCount, static_cast<float>(Items.Num()));  // scalar
CSV_EVENT(Foo, TEXT("Reload"));                       // point event
```

### Memory — `Core/Public/HAL/LowLevelMemTracker.h`

```cpp
LLM_SCOPE(ELLMTag::Foo);   // attribute allocations in this scope to a tag
```

---

## 5. Choosing between Insights and the stats system

| Need | Choice |
|---|---|
| Deep CPU timeline, call hierarchy, cross-thread causality | `TRACE_CPUPROFILER_EVENT_SCOPE*` (Unreal Insights) |
| A live number in the in-game `stat` overlay | `SCOPE_CYCLE_COUNTER` + a declared stat group |
| A captured series for offline comparison | `CSV_SCOPED_TIMING_STAT` / `CSV_CUSTOM_STAT` |
| Memory attribution | `LLM_SCOPE` |

New code defaults to Insights; the stats system stays for values a designer or
tester reads live in-game.
