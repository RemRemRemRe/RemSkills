# UE Version Diff Guide — Breaking Changes 5.3 → 5.8

Known breaking changes between engine versions that affect plugin compilation.
Organized by version transition (e.g., "5.3 → 5.4" means: "this broke when going
FROM 5.4 code DOWN TO 5.3 engine"). Use this to quickly identify which version
introduced a breaking change when you see an unfamiliar error.

Last verified: 2026-07. ｜ Source: adaptation history of a marketplace camera
plugin + Epic UE release notes.

---

## How to Use

```
You see:  error C2039: 'SomeFunction': is not a member of 'SomeClass'
           ↓
Search this guide for "SomeFunction"
           ↓
Find: "SomeFunction — added in 5.4"
           ↓
Fix: revert + re-fix — use the older equivalent noted in the table
     (e.g., replace with `OlderFunction` or wrap in project namespace)
```

---

## 5.3 → 5.4 (new features not in 5.3)

| Category | What | 5.3 equivalent | Fix strategy |
|----------|------|---------------|-------------|
| Math | `FMath::Modulo(X, Y)` | `FMath::Fmod(X, Y)` for float; `X % Y` for int | Wrap in project namespace or `#if` |
| Math | `FMath::FMod(X, Y)` (renamed) | `FMath::Fmod` (lowercase 'd') | Use `fmodf()` directly or wrap |
| Reflection | `GET_MEMBER_NAME_STRING_VIEW_CHECKED(T, F)` | `GET_MEMBER_NAME_STRING_CHECKED(T, F)` | Replace macro |
| Containers | `MakeArrayView(Ptr, N)` | `TArrayView<T>(Ptr, N)` | Use explicit constructor |
| Containers | `MakeConstArrayView(Ptr, N)` | `TConstArrayView<T>(Ptr, N)` | Use explicit constructor |
| Math | `FIntVector2::ZeroValue` | `FIntVector2(0, 0)` | Use literal init |
| Camera | `UCameraModifier::IsPendingDisable()` | `bPendingDisable` member (protected) | Expose in derived class |
| Camera | `UCameraModifier::GetAlpha()` | `Alpha` member (protected) | Expose in derived class |
| Struct | `TStructView<T>` implicit from pointer | explicit only | Use `TStructView<T>(ptr)` |
| Struct | `TConstStructView<T>` implicit from pointer | explicit only | Use `TConstStructView<T>(ptr)` |
| StructUtils | `#include "StructUtils/InstancedStruct.h"` | `#include "InstancedStruct.h"` (may differ) | Search engine source |
| Strings | `Containers/Utf8String.h` (FUtf8String) | does not exist (5.3 has only TUtf8StringBuilder + FUtf8StringView) | Backport a lightweight FUtf8String into plugin ThirdParty (TArray<UTF8CHAR> storage, Printf via FCStringAnsi::GetVarArgs) |
| Strings | `Containers/AnsiString.h` (FAnsiString) | does not exist (but FCStringAnsi / FAnsiStringView do) | Replace `FAnsiString::Printf` with `FCStringAnsi::Sprintf` + `AppendAnsi`; guard include with `__has_include` |
| Containers | `EAllowShrinking` | does not exist | Use `RemoveAtSwap(Index, 1, false)` instead of `RemoveAtSwap(Index, EAllowShrinking::No)` |
| GameplayTags | `FGameplayTag::ParseParentTags(TArray&)` | does not exist (only `RequestDirectParent()`) | Walk parents with `for (auto Tag = X; Tag.IsValid(); Tag = Tag.RequestDirectParent())` |
| GameplayTags | `FGameplayTag::RequestGameplayTag(const FString&, bool)` | takes `const FName&` | Wrap in `FName(...)` |
| Draw | `DrawDebugCapsuleTraceMulti/Single` with Orientation | no Orientation parameter | Version-guard the Orientation arg (5.4+) |
| UHT | `UFUNCTION` inside `#if` preprocessor block | not allowed (except WITH_EDITORONLY_DATA) | Use plain (non-UFUNCTION) methods under the guard |
| Compiler | 5.3 prefers MSVC 14.36 | new compilers fail on engine's `__has_feature` | Install 14.36 toolchain; UBT auto-selects preferred |
| fmt | `FMT_APPLY_VARIADIC` int[] trick | fails on MSVC 14.38 | Replace with C++17 fold `(static_cast<void>(expr), ...)` |
| Module | StructUtils module layout | Different submodules | Check Build.cs references |

---

## 5.4 → 5.5

| Category | What | 5.4 equivalent | Fix strategy |
|----------|------|---------------|-------------|
| Containers | `EAllowShrinking` enum changes | Different enum values | `#if` guard or avoid |
| GameplayTags | `ParseParentTags` behavior | Different signature | `#if` guard |
| Struct | `FInstancedStruct` initialization | Different constructor rules | Make explicit |
| Core | `InvExpApprox` math function | available since at least 5.6 (`FMath::InvExpApprox` in UnrealMathUtility.h) | Verified 2026-08: no backport needed; old-branch backport was redundant — use `FMath::InvExpApprox` directly |
| Build | `BuildSettingsVersion.Latest` | May resolve differently | Pin to explicit version if needed |
| Core | `Templates/Requires.h` (UE_REQUIRES) | not present; `UE_REQUIRES` lives in `Templates/UnrealTypeTraits.h` | Backported TNotNull must include `UnrealTypeTraits.h` on 5.4 |
| Core | `UE_STRINGIZE` (HAL/PreprocessorHelpers.h) | not present | Backport in plugin: `#define UE_PRIVATE_STRINGIZE_IMPL(Token) #Token` etc. |
| Core | `UE_COLD` (HAL/Platform.h) | not present | Backport: `__declspec(noinline)` (MSVC) / `__attribute__((cold))` (GCC/Clang) |
| Struct | `TStructView<T>` / `TConstStructView<T>` templates | only non-template `FStructView` / `FConstStructView` | Backport templates to plugin ThirdParty; they live in **global namespace** (not UE::StructUtils) |
| Struct | `TInstancedStruct<T>` ctor from `TConstStructView` | not present | Use `InitializeAsScriptStruct(ptr, mem)` instead |
| Struct | `TInstancedStruct` template `operator=` | compares `this != &InOther` across template types (bug) | Avoid; assign via `InitializeAsScriptStruct` |
| Build | C# `AddRange([ ... ])` collection expressions | not supported (C# 12) | Use `AddRange(new[] { ... })` |
| Build | `ModuleRules.Version` property | not present | Use `target.Target.Version.MajorVersion` |
| Logging | `FMinimalViewInfo::bUseFirstPersonParameters` / `FirstPersonFOV` / `FirstPersonScale` | not present (5.6+) | Comment out the first-person assignment block |
| fmt | `FMT_APPLY_VARIADIC` macro `(void)unused{0,(expr,0)...}` | fails to parse on MSVC 14.38 | Replace with C++17 fold `(static_cast<void>(expr), ...)` |
| fmt | `C4459` shadow warnings inside fmt headers | promoted to error when `ShadowVariableWarningLevel=Error` on **any** 5.3–5.8 engine compiled with MSVC 14.38 (Fab/build-farm uses the preferred 14.38 toolchain; local verification may silently use a newer non-preferred compiler and miss it) | Keep `ShadowVariableWarningLevel = Warning` on ALL versions — do not gate by engine version |
| Build | C# 12 collection expressions `AddRange([ ... ])` in `*.Build.cs` | not supported by UE 5.5 and older UBT C# compilers (CS1026/CS0443/CS1002); 5.6+ accept them | Always write `AddRange(new[] { ... })` in Build.cs — lowest common denominator, commit as a base-area change |
| fmt | `C4459` shadow warnings inside fmt headers | shadow-warning-as-error promotes to error | Lower `ShadowVariableWarningLevel` to Warning on 5.4, or wrap fmt include |
| fmt | `THIRD_PARTY_INCLUDES_START/END` around fmt include | caused C2143 on 5.4 | Do NOT wrap fmt with THIRD_PARTY_INCLUDES; rely on shadow level instead |
| Test | `*.spec.cpp` automation tests using types missing on 5.4 (TSharedStruct etc.) | fail to compile | Disable with `#if 0 && WITH_DEV_AUTOMATION_TESTS` (tests are not shipping code) |

---

## 5.5 → 5.6

| Category | What | 5.5 equivalent | Fix strategy |
|----------|------|---------------|-------------|
| Render | First-person rendering parameters | Different ViewTarget API | `#if` guard or revert |
| Struct | StructUtils API surface changes | Slightly different includes | Check includes |
| Core | `GetCurves` API changes | Different signature | `#if` guard or revert |
| Core | `Misc/NotNull.h` (TNotNull) — added in 5.6 | does not exist (5.3–5.5) | Backport the header into the plugin; select engine-vs-backport via `__has_include("Misc/NotNull.h")`. The backport needs `Traits/IsImplicitlyConstructible.h` (also 5.6+) — backport it too, and replace `CORE_API` exported functions with inline definitions (older Core does not export them) |
| Cast | `Cast<T>(TNotNull<const X*>)` — 5.6+ Cast accepts TNotNull | template deduction fails | Unwrap explicitly: `Cast<T>(static_cast<const X*>(NotNull))` |
| Core | `UE_NODEBUG` attribute macro | does not exist | `#ifndef` define as empty (in a widely-included compat header) |
| Core | `UE_REWRITE` (backported) | FORCEINLINE breaks MSVC before template return type | On <5.6 define `UE_REWRITE` empty instead of `UE_NODEBUG FORCEINLINE` |
| Strings | `FName::ToUtf8String()` — added in 5.6 | `FName::ToString()` (TCHAR) | Version helper: `FUtf8String(Name.ToString())` on older |
| Strings | `FSoftObjectPath::GetSubPathUtf8String()` — added in 5.6 | `GetSubPathString()` (TCHAR) | Conditional branch; TCHAR path uses `StringCast<TCharType>(*FString)` |
| Build | `NonInlinedGenCppWarningLevel` (in `CppCompileWarningSettings`) — added in 5.6 | `ModuleRules` has no `CppCompileWarningSettings` | Drop the setting; keep Shadow/Unsafe via direct `target.ShadowVariableWarningLevel` (works 5.3-5.8, deprecated-obsolete in 5.6+) |
| UBT | `ENGINE_MAJOR_VERSION` / `ENGINE_MINOR_VERSION` not always defined in headers | not defined in 5.5 | Guard with `#if defined(ENGINE_MAJOR_VERSION) && (...)` or prefer `__has_include` |
| Module | GameplayCameras `FCameraPose` API (5.8 style) largely missing in 5.5 | much smaller API | Disable the module (like the 5.3 adaptation did) |
| Link | Backported NotNull.h declares `CORE_API ReportNotNullPtr`/`CheckLoadingNotNullPtr` | 5.5 Core does not export them | Replace with inline definitions using `UE_LOG(LogCore, Fatal, ...)` |

---

## 5.6 → 5.7

| Category | What | 5.6 equivalent | Fix strategy |
|----------|------|---------------|-------------|
| Core | `UE_COLD` function attribute | Not available | Remove attribute or `#if` guard |
| Core | `UE_REWRITE` macro | Different form | Adjust usage |
| Gameplay | `GetOwnedGameplayTags` return value | void (output param) | Adjust call pattern or `#if` |
| Camera | GameplayCameras plugin API changes | Different camera types | `#if` guard or cherry-pick adapts |
| Config | New developer settings properties | N/A | Remove references or `#if WITH_EDITOR` |
| UBT | `ModuleRules.bAllowUETypesInNamespaces` | does not exist | Do NOT set it at all — old UHT rejects the property even via reflection. Keep UENUMs out of namespaces instead (see UHT row) |
| UHT | UENUM inside a namespace | not supported (5.6 UHT fails to generate) | Move the UENUM out of the namespace to global scope; helpers can stay in the namespace |
| Strings | `NotNullGet(TNotNull&)` | does not exist | Use `operator T()` implicit conversion or `static_cast` instead of `*` (void pointers can't deref) |
| Logging | `UE_BREAK_AND_RETURN_FALSE()` | does not exist | Backport from 5.7 (AssertionMacros.h) into plugin macro header |
| Types | `bGEnsureHasExecuted<Uid>` / `FileLineHashForEnsure` (5.7 names) | different ensure internals | Backport as `bGEnsureHasExecuted57` + `FileLineHashForEnsure57` to avoid clashing with engine |
| fmt | fmt `format_to` requires `char` output iterator | UTF8CHAR is an enum (5.8 is char8_t) | Add `operator=(char)` overload that converts to UTF8CHAR |
| Strings | `TConstStructView<T>` / `TStructView<T>` templates | only non-template `FConstStructView` / `FStructView` | Reference the old adaptation branch for the exact pattern |
| Strings | `FUtf8String::FindLastChar(CharType)` — passing `TEXT('.')` (wchar_t) fails | needs `UTF8CHAR` argument | Use `UTF8CHAR('.')` instead of `TEXT('.')` on FUtf8String |

---

## 5.7 → 5.8

| Category | What | 5.7 equivalent | Fix strategy |
|----------|------|---------------|-------------|
| Core | `Units` type system (new) | N/A | Revert + re-fix: use raw float/double types in older versions |
| String | `fmt` library integration | `FString::Printf` | Revert + re-fix: replace fmt usage with Printf |
| Logging | `UE_LOGF` (UTF8/ANSI formatted logging) | `UE_LOG` (TCHAR only) | Revert UTF8 chain to TCHAR: `TUtf8StringBuilder` → `TStringBuilder`, `"%hs"` → `TEXT("%s")` |
| Delegates | `FCoreDelegates::OnEnsureFailed` (detail broadcast) | remove; only `OnHandleSystemEnsure` (no-arg) | Remove the broadcast call |
| Movement | `FBasedMovementInfo::MovementBaseInterfaceData` | `FBasedMovementInfo::MovementBase` | `.Get()` → `UPrimitiveComponent*` |
| Movement | `GetMovementBaseTransform(&InterfaceData, ...)` | `GetMovementBaseTransform(MovementBase, ...)` | Pass primitive directly |
| Reflection | `GET_MEMBER_NAME_ANSI_STRING_VIEW_CHECKED` | declare compat shim (`ANSITEXTVIEW(#M)`); FName still compares with `FAnsiStringView` | Add `#ifndef` shim, keep original calls |
| Camera | `FCameraPose` first-person params (`SetEnableFirstPerson`, `GetFirstPersonFOV`, ...) | N/A | Remove/comment the calls |
| Strings | `FUtf8String` → `FUtf8StringView` implicit | explicit `FUtf8StringView{Str}` | Construct explicitly |
| Core | `TObjectPtr` stricter enforcement | More lax | None needed going down |
| Reflection | UHT stricter validation | More permissive | Adjust UPROPERTY/UFUNCTION specifiers |
| Core | plugin-namespace `TNotNull` expanded usage | Less strict | Project-internal; adjust as needed |
| Include | `IncludeOrderVersion.Latest` | 5.7 equivalent | Usually backward-compatible |

---

## Module Changes Across Versions

Module dependencies that changed names, split, or merged:

| Old name | New name | Changed in | Action |
|----------|----------|-----------|--------|
| (tbd) | (tbd) | (tbd) | Track per-project |

> **Note**: Fill in this table as you encounter module dependency errors during
> adaptation. Common pattern: a module was split in newer UE, so going down you
> need to merge the deps back; going up you need to split them.

---

## UHT / Reflection Changes

UHT (Unreal Header Tool) becomes stricter with each version. Going down:

| Issue | Versions affected | Fix |
|-------|------------------|-----|
| New UPROPERTY specifiers not recognized | 5.x code → 5.(x-1) | Remove specifier or `#if` |
| New UFUNCTION specifiers | Same | Remove or guard |
| Stricter `BlueprintType` / `Blueprintable` requirements | 5.7+ → 5.6- | Add missing specifiers or adjust |

---

## Build System Changes

| Change | Version | Impact |
|--------|---------|--------|
| `CppStandard = CppStandardVersion.EngineDefault` | All | All versions 5.3–5.8 resolve to C++20 via `EngineDefault`. No C++23 differences. |
| `DefaultBuildSettings = BuildSettingsVersion.Latest` | All | Resolves to different defaults per version |
| `IncludeOrderVersion = EngineIncludeOrderVersion.Latest` | All | Include order policy changes per version |
| `bUseUnity = false` | All | Must be consistent; Unity builds mask missing includes |

---

## Quick Reference: "Which version added this?"

When you see an unfamiliar symbol in a build error, find it here:

| Symbol | Added in | Removed? | Quick fix |
|--------|---------|----------|-----------|
| `FMath::Modulo` | 5.4 | No | Wrap or use `FMath::Fmod` |
| `GET_MEMBER_NAME_STRING_VIEW_CHECKED` | 5.4 | No | Use `GET_MEMBER_NAME_STRING_CHECKED` |
| `MakeArrayView` | 5.1 | No | Use `TArrayView<T>(ptr, n)` |
| `MakeConstArrayView` | 5.1 | No | Use `TConstArrayView<T>(ptr, n)` |
| `FIntVector2::ZeroValue` | 5.4 | No | Use `FIntVector2(0, 0)` |
| `UCameraModifier::IsPendingDisable` | 5.4 | No | Expose in derived class |
| `UCameraModifier::GetAlpha` | 5.4 | No | Expose in derived class |
| `UE_COLD` | 5.7 | No | Remove attribute |
| `InvExpApprox` | ≤5.6 (already in engine) | No | Use `FMath::InvExpApprox` — no backport needed |
| `GET_TYPED_VARARGS` | 5.4 | ? | Revert: remove or re-implement without macro |
| `Units` (type) | 5.8 | No | Revert + re-fix: use raw float/double |
| `UE_LOGF` | 5.8 | No | Use `UE_LOG` + TCHAR chain (see error-patterns Pattern 10) |
| `FCoreDelegates::OnEnsureFailed` | 5.8 | No | Remove the broadcast (5.7 has `OnHandleSystemEnsure` no-arg only) |
| `FBasedMovementInfo::MovementBaseInterfaceData` | 5.8 | No | Use `.MovementBase` (TObjectPtr<UPrimitiveComponent>) |
| `GET_MEMBER_NAME_ANSI_STRING_VIEW_CHECKED` | 5.8 | No | Declare compat shim (`ANSITEXTVIEW(#M)`); FName == FAnsiStringView works in 5.7 |
| `FCameraPose::SetEnableFirstPerson` etc. | 5.8 | No | Remove/comment the calls |
| (add more as discovered) | | | |

---

## How to Contribute to This Guide

When you encounter and fix a new version-specific issue, add a row to the
appropriate section above. Include:

1. The exact symbol/API that failed
2. Which version it was added/changed in
3. The older equivalent or workaround
4. The fix strategy that worked

This guide grows more valuable with each adaptation cycle.
