---
name: rem-sequencer-custom-channel-section
description: >
  Create custom FMovieSceneChannel and UMovieSceneSection for the Unreal Sequencer editor,
  with per-key struct editing via FSequencerKeyStructGenerator. Covers channel declaration
  (KeyTimes/KeyValues meta), channel traits, EvaluateChannel for discrete channels, clipboard
  override, CacheChannelProxy in sections, TSequencerChannelInterface registration, and all
  required module dependencies. Use when building a custom Sequencer track/section whose keys
  store complex struct data that must be individually editable in the Sequencer details panel.
  Last verified: 2026-07, UE 5.8.
metadata:
  category: meta
  trigger: manual
---
# UE Sequencer — Custom Channel & Section with Per-Key Editing

## When to use this skill

- You need a custom `UMovieSceneSection` whose keys hold **complex struct data**
  (not just `float`/`int`/`bool`) and must be **individually editable** in the
  Sequencer details panel.
- You are building a trigger / event / action section where each key stores
  a different configuration.
- Per-key editing is broken and the details panel is blank when selecting keys.

---

## Architecture Overview

```
UMovieSceneSection                 ← your section subclass
  └─ CacheChannelProxy()           ← expose custom channel to Sequencer UI
       └─ FMovieSceneChannelProxy
            └─ FFooChannel    ← your USTRUCT channel
                 ├─ KeyTimes[]     ← meta=(KeyTimes) — required by generator
                 └─ KeyValues[]    ← meta=(KeyValues) — required by generator
                      └─ FMyKeyData  ← your per-key value struct (MUST be regular USTRUCT)

TSequencerChannelInterface<FFooChannel>
  └─ Registered in module StartupModule()
       └─ FSequencerKeyStructGenerator  ← auto-generates key edit struct from KeyValues inner type
```

**Key insight:** The generator finds `KeyTimes` and `KeyValues` arrays via their
`meta=(KeyTimes)` / `meta=(KeyValues)` tags, extracts the inner type of
`KeyValues`, wraps it alongside an `FFrameNumber Time` in a generated
`UMovieSceneKeyStructType`, and displays it in the details panel when a key is
selected.

---

## Step 1: Define the per-key data struct

The value type stored in your channel's `KeyValues` array **must** be a regular
`USTRUCT`. `TInstancedStruct<FSomeBase>` (polymorphic types) **cannot** be the
direct value type — the generator does not know how to reflect them.

If you need polymorphism, wrap it inside a regular USTRUCT:

```cpp
// FooKeyData.h
#pragma once

#include "StructUtils/InstancedStruct.h"
#include "MyOtherStructs.h"

#include "FooKeyData.generated.h"

struct FFooPolymorphicBase;   // forward-declare the base type

USTRUCT()
struct FFooKeyData
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, Category = "Timing")
    FFooTimerConfig TimerConfig;               // plain USTRUCT — works fine

    UPROPERTY(EditAnywhere, Category = "Action",
        meta = (ExcludeBaseStruct))
    TInstancedStruct<FFooPolymorphicBase> Action;  // polymorphic inside wrapper — OK
};
```

| Pattern | Works for per-key editing? |
|---------|---------------------------|
| `TArray<float>` | Yes (built-in key editor) |
| `TArray<FLinearColor>` | Yes (built-in key editor) |
| `TArray<FMyPlainStruct>` | Yes (generator reflects it) |
| `TArray<TInstancedStruct<T>>` | **No** — generator can't reflect TInstancedStruct |
| `TArray<FMyWrapper>` where wrapper contains `TInstancedStruct` | **Yes** — outer struct is reflected, inner struct uses struct picker |

---

## Step 2: Define the custom channel

The channel is a `USTRUCT` derived from `FMovieSceneChannel`. It must:

- Have `meta=(KeyTimes)` on the times array and `meta=(KeyValues)` on the values array
- Expose `GetData()` returning `TMovieSceneChannelData<ValueType>`
- Delegate all `FMovieSceneChannel` virtuals to `GetData()`
- Specialize `TMovieSceneChannelTraits` (at minimum `SupportsDefaults = false`)

Channel boilerplate skeleton: `references/channel-boilerplate.md`.

---

## Step 3: Channel traits & mandatory free functions

### 3a. TMovieSceneChannelTraits specialization

Always required. Use `SupportsDefaults = false` for discrete (trigger/event-style)
channels that don't interpolate.

### 3b. EvaluateChannel overload (MANDATORY)

Defined as a **free function** found via ADL. The engine calls
`UE::MovieScene::EvaluateChannel<>()` which dispatches to `EvaluateChannel(...)`.
Without this overload, compilation fails with:

> `'Evaluate': is not a member of 'FFooChannel'`

For discrete channels (keyframes only, no interpolation), return `false`.

Do NOT add `Evaluate` as a member function — it won't be found by the template.

### 3c. CopyKeys / PasteKeys overrides

The default `Sequencer::CopyKeys<>` template calls
`MovieSceneClipboard::GetKeyTypeName<T>()` for the value type. If your value
type is not registered in `ClipboardTypes.h` (engine file under
`Engine/Source/Editor/MovieSceneTools/Public/ClipboardTypes.h`), the build fails
with:

> `static assertion failed: 'This function must be specialized to use with the specified type'`

Provide no-op overrides in the `Sequencer` namespace (non-template, exact match
wins over the template default).

These require `#include "SequencerChannelTraits.h"` (for clipboard type
definitions) and must be inside `#if WITH_EDITOR`.

Full traits, `EvaluateChannel`, and `CopyKeys`/`PasteKeys` listings:
`references/interface-traits.md`.

---

## Step 4: Expose channel in the section via CacheChannelProxy

Override `CacheChannelProxy()` in your `UMovieSceneSection` subclass. Return
`EMovieSceneChannelProxyType::Dynamic` so the proxy is rebuilt when section
properties change:

```cpp
// In my section .cpp:
#if WITH_EDITOR
EMovieSceneChannelProxyType UFooSection::CacheChannelProxy()
{
    FMovieSceneChannelProxyData Channels;

    FMovieSceneChannelMetaData MetaData(
        FName(TEXT("FooChannel")),
        FText::FromString(TEXT("Foo Channel"))
    );
    MetaData.bCanCollapseToTrack = true;    // show inline in section
    Channels.Add(FooChannel, MetaData);

    ChannelProxy = MakeShared<FMovieSceneChannelProxy>(MoveTemp(Channels));
    return EMovieSceneChannelProxyType::Dynamic;
}
#endif
```

| Flag | Effect |
|------|--------|
| `bCanCollapseToTrack = false` | Shows per-key diamonds on the track header (default) |
| `bCanCollapseToTrack = true` | Shows channel inline inside the section area |
| `EMovieSceneChannelProxyType::Dynamic` | Rebuilds proxy on property changes |
| `EMovieSceneChannelProxyType::Static` | Proxy built once, never rebuilt |

---

## Step 5: Register TSequencerChannelInterface

This is the step that **enables per-key editing**. Without it, the key details
panel is empty when selecting keys.

In your module's `StartupModule()`:

```cpp
#include "ISequencerModule.h"
#include "Channels/FooChannel.h"

void FFooModule::StartupModule()
{
    IFooModuleInterface::StartupModule();

    if (ISequencerModule* SequencerModule =
        FModuleManager::GetModulePtr<ISequencerModule>("Sequencer"))
    {
        SequencerModule->RegisterChannelInterface<FFooChannel>();
    }
}
```

Registration internals (`GetKeyStruct_Raw` → `FSequencerKeyStructGenerator`):
`references/registration-internals.md`.

---

## Step 6: Required module dependencies (Build.cs)

| Module | Why needed |
|--------|-----------|
| `"MovieScene"` | `FMovieSceneChannel`, `TMovieSceneChannelData`, `TMovieSceneChannelTraits` |
| `"MovieSceneTracks"` | Inheriting from `UMovieSceneEventTriggerSection` etc. |
| `"MovieSceneTools"` | Channel proxy, metadata, section editing infrastructure |
| `"Sequencer"` | `ISequencerModule`, `TSequencerChannelInterface`, `FSequencerKeyStructGenerator` |
| `"SlateCore"` | Required by `TSequencerChannelInterfaceCommon::CreateKeyEditor_Raw` (links to `SNullWidget`) |
| `"StructUtils"` | `TInstancedStruct`, `FInstancedStruct` |

Example:

```csharp
PrivateDependencyModuleNames.AddRange(
    [
        "Core",
        "CoreUObject",
        "Engine",
        "MovieScene",
        "MovieSceneTracks",
        "MovieSceneTools",
        "Sequencer",
        "SlateCore",
        "StructUtils",
    ]
);
```

---

## Common Pitfalls & Error Reference

| Build Error | Root Cause | Fix |
|------------|-----------|-----|
| `'Evaluate': is not a member of 'FMyChannel'` | Missing `EvaluateChannel` free function | Add `inline bool EvaluateChannel(...)` (Step 3b) |
| `static assertion failed: 'This function must be specialized...'` (MovieSceneClipboard.h:34) | Value type not registered for clipboard | Add no-op `CopyKeys`/`PasteKeys` in `Sequencer` namespace (Step 3c) |
| `type name first seen using 'class' now seen using 'struct'` | Forward declaration mismatch | Include the full header instead of forward-declaring (Step 2, `#include "SequencerChannelTraits.h"`) |
| `LNK2019: unresolved external symbol SNullWidget::NullWidget` | Missing SlateCore link | Add `"SlateCore"` to Build.cs (Step 6) |
| Details panel empty when key selected | `RegisterChannelInterface` not called | Add registration in `StartupModule()` (Step 5) |
| Details panel empty when key selected | Value type is `TInstancedStruct<T>` (not a regular USTRUCT) | Wrap in a plain USTRUCT (Step 1) |
| Keys not visible in Sequencer section | `CacheChannelProxy` not overridden or channel not added | Add channel to proxy in `CacheChannelProxy()` (Step 4) |
| `.generated.h` compile errors | `.generated.h` not the last include | Move `.generated.h` include to the very end of the file |

---

## Complete File Checklist

When adding a new custom channel + section with per-key editing:

- [ ] **Key data struct** — Regular USTRUCT wrapping config + `TInstancedStruct` for polymorphism
- [ ] **Channel USTRUCT** — `meta=(KeyTimes)` and `meta=(KeyValues)` on arrays; delegates to `GetData()`
- [ ] **Channel traits** — `TMovieSceneChannelTraits<>` with `SupportsDefaults = false`
- [ ] **EvaluateChannel** — Free function returning `false` for discrete channels
- [ ] **CopyKeys / PasteKeys** — No-op overrides in `Sequencer` namespace (WITH_EDITOR gated)
- [ ] **CacheChannelProxy** — Section override returning `Dynamic`, adds channel to proxy
- [ ] **RegisterChannelInterface** — Called in `StartupModule()` with `ISequencerModule`
- [ ] **Build.cs dependencies** — `MovieScene`, `MovieSceneTracks`, `MovieSceneTools`, `Sequencer`, `SlateCore`
- [ ] **`.generated.h` last** — Generated include is the final `#include` in every header
