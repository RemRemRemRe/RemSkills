# UE Cross-Version Error Patterns

Real-world compilation error patterns encountered when adapting plugins
across UE 5.3–5.8. Each entry shows the error, cause, and fix strategy
with actual code examples from adaptation history.

Last verified: 2026-07.

---

## Pattern 1: API Not Available in Older Engine

### Example A — `FMath::Modulo` (added 5.4)

**Error**:
```
error C2039: 'Modulo': is not a member of 'FMath'
```

**Essence**: `FMath::Modulo` is a templated helper added in UE 5.4; 5.3 only
has `FMath::Fmod`. Two facts matter:

- `FMath::Fmod` exists on **all** 5.3–5.8 engines (5.4+ `FMath::Modulo` calls
  it internally), so it is the correct cross-version primitive.
- Both use **fmod semantics** (remainder toward zero) — NOT floor-modulo —
  so wrapping `FMath::Fmod` keeps behavior identical on every version,
  including negative inputs.

**Fix**: wrap in a project namespace. The wrapper must preserve the argument
types — call `FMath::Fmod` directly, do NOT funnel through `fmodf` (narrows
`double` to `float`):

```cpp
namespace Foo::Math
{
    template <typename ValueType, typename BaseType>
    [[nodiscard]] constexpr auto Modulo(ValueType Value, BaseType Base)
    {
        if constexpr (std::is_floating_point_v<ValueType>)
        {
            return FMath::Fmod(Value, Base);
        }
        else
        {
            return Value % Base;
        }
    }
}
```

Call sites switch to the wrapper: `FMath::Modulo(...)` → `Foo::Math::Modulo(...)`.

### Example B — `MakeArrayView` / `MakeConstArrayView` (not in 5.3)

**Error**:
```
error C3861: 'MakeArrayView': identifier not found
error C3861: 'MakeConstArrayView': identifier not found
```

**Fix**: Use explicit `TArrayView` / `TConstArrayView` constructor directly.

**Before**:
```cpp
StructContainer.Append(MakeConstArrayView(&NewStruct, 1));
StructContainer.InsertAt(IndexToInsert, MakeConstArrayView(&NewStruct, 1));
```

**After**:
```cpp
StructContainer.Append(TConstArrayView<FConstStructView>(&NewStruct, 1));
StructContainer.InsertAt(IndexToInsert, TConstArrayView<FConstStructView>(&NewStruct, 1));
```

### Example C — `FIntVector2::ZeroValue` (not in 5.3)

**Error**:
```
error C2039: 'ZeroValue': is not a member of 'FIntVector2'
```

**Fix**: Use literal initialization.

**Before**:
```cpp
FIntVector2 FrameRange{FIntVector2::ZeroValue};
```

**After**:
```cpp
FIntVector2 FrameRange{0, 0};
```

---

## Pattern 2: Macro Not Available

### `GET_MEMBER_NAME_STRING_VIEW_CHECKED` (5.4+)

**Error**:
```
error C3861: 'GET_MEMBER_NAME_STRING_VIEW_CHECKED': identifier not found
```

**Cause**: This macro was added in 5.4. 5.3 only has `GET_MEMBER_NAME_STRING_CHECKED`.

**Fix**: Replace with the older macro.

**Before**:
```cpp
if (PropertyChangedEvent.GetPropertyName() == GET_MEMBER_NAME_STRING_VIEW_CHECKED(FFooRow, SettingValues))
```

**After**:
```cpp
if (PropertyChangedEvent.GetPropertyName() == GET_MEMBER_NAME_STRING_CHECKED(FFooRow, SettingValues))
```

---

## Pattern 3: Base Class Method Missing

### `IsPendingDisable()` (added after 5.3)

**Error**:
```
error C2039: 'IsPendingDisable': is not a member of 'UCameraModifier'
```

**Cause**: `UCameraModifier::IsPendingDisable()` was not yet a public method.

**Fix**: Add the method in the derived class, using the underlying member variable.

**Before** (calling base class method):
```cpp
if (bNewlyCreated || ExistedModifier->IsDisabled() || ExistedModifier->IsPendingDisable())
```

**After** (add to derived class header + use cast):
```cpp
// In header:
class UMyModifier : public UCameraModifier
{
public:
    bool IsPendingDisable() const { return bPendingDisable; }
    float GetAlpha() const { return Alpha; }
};

// In usage:
if (const bool bPendingDisable = ExistedModifier->IsA<UMyModifier>()
    ? CastChecked<UMyModifier>(ExistedModifier)->IsPendingDisable()
    : false;
    bNewlyCreated || ExistedModifier->IsDisabled() || bPendingDisable)
```

**Key**: When a base class method doesn't exist in older engine versions but the
underlying data member does, expose it in the derived class via a wrapper.

---

## Pattern 4: Implicit Conversion Not Available

### `FStructView` implicit construction (5.3)

**Error**:
```
error C2440: 'return': cannot convert from 'FBazContainer *' to 'TStructView<FBazContainer>'
```

**Cause**: Implicit `TStructView` construction from raw pointer was not supported
or was marked `explicit` in 5.3.

**Fix**: Use explicit construction.

**Before**:
```cpp
TConstStructView<FBazContainer> GetContainerView() const
{
    return GetContainer();
}
```

**After**:
```cpp
TConstStructView<FBazContainer> GetContainerView() const
{
    return TConstStructView<FBazContainer>(GetContainer());
}
```

---

## Pattern 5: Include Path Changes

### `StructUtils` headers (changed across 5.3-5.5)

**Error**:
```
error C1083: Cannot open include file: 'StructUtils/InstancedStruct.h'
```

**Fix**: Try alternative paths. Common alternatives:
- `StructUtils/InstancedStruct.h` (5.4+)
- `InstancedStruct.h` (5.3, in StructUtils module)

When the exact path is uncertain, search the engine source:
```bash
find <engine-root>/Engine/Source -name "InstancedStruct.h" 2>/dev/null
```

---

## Pattern 6: Feature Not Available — Guard or Remove

### Disable a module entirely on old versions

**Error**: Module `<DepModule>` references API not in 5.3.

**Fix**: Edit `<PluginName>.Build.cs` to conditionally exclude the module.

**Before**:
```csharp
PrivateDependencyModuleNames.Add("<DepModule>");
```

**After** (conditionally exclude):
```csharp
if (Target.bBuildEditor)
{
    // <DepModule> requires 5.4+ APIs
    PrivateDependencyModuleNames.Add("<DepModule>");
}
```

Or alternatively, if the module can exist but just not compile certain files:

```csharp
// Remove from dependency list entirely for 5.3
// PrivateDependencyModuleNames.Add("<DepModule>");
```

---

## Pattern 7: General Strategy Decision Tree

```
Error received
├── API not found (C2039, C3861)
│   ├── Can wrap in project namespace? → Create Foo:: wrapper (Pattern 1A)
│   ├── Has direct older equivalent?    → Replace with older API (Pattern 2)
│   ├── Underlying data still exists?   → Expose via derived class (Pattern 3)
│   └── Feature simply doesn't exist    → Revert + re-fix or remove/disable
├── Include not found (C1083)
│   └── Search engine source for correct path → Update include (Pattern 5)
├── Conversion/constructor error (C2440, C2668)
│   └── Make construction explicit (Pattern 4)
├── Template deduction failure (C2664, C2672)
│   └── Add explicit template arguments
└── Module dependency error (UBT)
    └── Edit Build.cs dependencies
```

---

## Pattern 8: Engine Macro-Gated API Referenced Unconditionally

### Example — `CNotNull` / `CNotNullOf` concepts (UE_ENABLE_NOTNULL_WRAPPER)

**Error** (5.8 Development BuildPlugin):
```
error C3878: syntax error: unexpected token '>' following 'simple-type-specifier'
concept CNotNull = UE::Core::Private::TIsTNotNullParam_V<T>;
```

**Essence**: the concept references a symbol
(`UE::Core::Private::TIsTNotNullParam_V`) that only exists inside an engine
macro gate (`#if UE_ENABLE_NOTNULL_WRAPPER` in `Misc/NotNull.h`). When the
gate is off (Release/Shipping or overridden config) the symbol is undefined
and the concept definition fails to parse — even though the concept would
never be *used* there.

**Fix**: gate the concept with the same macro and provide a `false` fallback,
so dependent `if constexpr` / `requires` clauses still compile:

```cpp
namespace Foo
{
#if UE_ENABLE_NOTNULL_WRAPPER
template <typename T>
concept CNotNull = UE::Core::Private::TIsTNotNullParam_V<T>;

template <typename NotNull, typename ValueTypeBase>
concept CNotNullOf = CNotNull<NotNull> && /* ... */;
#else
template <typename T>
concept CNotNull = false;
template <typename NotNull, typename ValueTypeBase>
concept CNotNullOf = false;
#endif
}
```

**Key**: when a concept/type wraps an engine macro-gated symbol, mirror the
engine's own guard with a neutral fallback so all usage sites compile
unchanged.

---

## Pattern 9: Direct Include of Delegate Implementation Header

**Error** (5.8):
```
error C1189: #error: "This inline header must only be included by Delegate.h"
```

**Cause**: `Delegates/DelegateSignatureImpl.inl` must only be included by
`Delegates/Delegate.h`. Directly including it (as some upstream code does)
fails in newer engine versions.

**Fix**: Replace with the public header:

**Before**:
```cpp
#include "Delegates/DelegateSignatureImpl.inl"
```

**After**:
```cpp
#include "Delegates/Delegate.h"
```

---

## Pattern 10: New Logging Macro With Different Encoding (5.8 UE_LOGF)

**Error** (5.7 build):
```
error C3861: 'UE_LOGF': identifier not found
error C2338: static assertion failed: 'Formatting string must be a TCHAR array.'
```

**Cause**: `UE_LOGF` (UTF8/ANSI-capable formatted logging) was added in UE 5.8.
Older engines only have `UE_LOG`, which requires TCHAR format strings. Simply
aliasing `UE_LOGF` to `UE_LOG` fails when the code passes `"%hs"` + UTF8 data.

**Fix**: revert the UTF8 logging chain to a TCHAR one for older engines — in
the log macros, swap `TUtf8StringBuilder` → `TStringBuilder` (TCHAR) and
`UE_LOGF(..., "%hs", *Builder)` → `UE_LOG(..., TEXT("%s"), *Builder)`:  

**Before** (inside the log macros):
```cpp
TUtf8StringBuilder<256> Builder;
Foo::Format(Builder, FormatString, ##__VA_ARGS__);
UE_LOGF(CategoryName, Verbosity, "%hs", *Builder);
```

**After**:
```cpp
TStringBuilder<256> Builder;
Foo::Format(Builder, FormatString, ##__VA_ARGS__);
UE_LOG(CategoryName, Verbosity, TEXT("%s"), *Builder);
```

For ANSI pointers (`NarrowMessage.Get()`), use `TEXT("%hs")`:
```cpp
UE_LOG(LogOutputDevice, Error, TEXT("%hs"), NarrowMessage.Get());
```

For UTF8 string content, convert explicitly:
```cpp
UE_LOG(Cat, Verb, TEXT("%s"), *FString(UTF8_TO_TCHAR(Utf8Ptr)));
```

---

## Pattern 11: 5.8-Only Engine APIs Reverted for 5.7

Real 5.7 adaptation reverts (verified 2026-08):

| 5.8 API | 5.7 equivalent | Notes |
|---------|---------------|-------|
| `FCoreDelegates::OnEnsureFailed.Broadcast(...)` | remove the broadcast | 5.7 only has `OnHandleSystemEnsure` (no-arg); detail broadcast was added in 5.8 |
| `FBasedMovementInfo::MovementBaseInterfaceData` | `FBasedMovementInfo::MovementBase` (`TObjectPtr<UPrimitiveComponent>`) | `.Get()` yields `UPrimitiveComponent*`, convertible to `UObject*` |
| `MovementBaseUtility::GetMovementBaseTransform(&InterfaceData, ...)` | `GetMovementBaseTransform(MovementBase, ...)` | 5.7 takes the primitive directly |
| `GET_MEMBER_NAME_ANSI_STRING_VIEW_CHECKED(T, M)` | declare a compat macro via `ANSITEXTVIEW(#M)`; 5.7 FName compares fine with `FAnsiStringView` | ANSI view macro added in 5.8; keep original calls, add `#ifndef` shim at file top |
| `FCameraPose::SetEnableFirstPerson/GetEnableFirstPerson/SetFirstPersonFOV/...` | remove/comment the calls | first-person camera pose params added in 5.8 |
| `FUtf8String` → `FUtf8StringView` implicit | construct explicitly: `FUtf8StringView{Str}` | implicit conversion added in 5.8 |
| `ON_SCOPE_EXIT` (may be missing) | `#include "Misc/ScopeExit.h"` | 5.7 may not pull it in transitively |

**Key**: these are adaptation-branch reverts — do NOT push them upstream, where
the 5.8 codebase keeps the new APIs.

---

## Fix Strategy Priority

When choosing a fix strategy, prefer in this order:

1. **Wrap in project namespace** (`Foo::Math::Modulo`) — keeps code clean and version-independent
2. **Replace with older equivalent** — when a direct 1:1 replacement exists
3. **Expose via derived class** — when underlying member exists but API doesn't
4. **Make explicit** — when implicit conversion is the only issue
5. **Backport small APIs** — if the API is self-contained (a few files), copy it into the plugin for older versions
6. **Remove/disable feature** — when the feature is too large to backport, remove the code and document limitation

## Process Lessons (5.7 adaptation, verified 2026-08)

1. **Fix root causes before secondary errors**: one missing macro / syntax error
   (e.g., `ON_SCOPE_EXIT` undefined) can cascade — later overload-resolution and
   type errors in the same translation unit are often noise from the broken
   parse. Fix the root first, rebuild, then reassess the remaining errors.
   The 5.7 `IsTagQueryMatches` / `FindCommonParentTag` overload errors vanished
   once the earlier `ON_SCOPE_EXIT` syntax error was fixed.

2. **Prefer a compat shim over changing call sites**: when a 5.8 macro/API is
   missing on 5.7 and a drop-in equivalent can be replicated (e.g.,
   `GET_MEMBER_NAME_ANSI_STRING_VIEW_CHECKED` via `ANSITEXTVIEW(#M)`), declare a
   `#ifndef`-guarded shim and keep the original call sites. This keeps the
   adaptation branch closest to upstream, minimizing diff and merge pain.
   Only change call sites when a faithful shim is impossible.

3. **Adaptation reverts stay local**: revert-style fixes (5.8 API → older
   equivalent) are branch-specific — do NOT push them to upstream repos, which
   legitimately keep the newer APIs. Bug fixes (e.g., CNotNull wrapper guard)
   DO go upstream after local verification.

4. **Cherry-picked macro calls may use a different argument order**: the old
   adaptation branch may predate a macro-system refactor. A cherry-picked call
   like `FooCheckVariable(Ptr, stmt;, FOO_NO_ASSERTION)` may be the OLD order;
   the current HEAD macro expects `FooCheckVariable(FOO_NO_ASSERTION, Ptr, stmt;)`.
   When a cherry-pick introduces "no matching overload" / weird syntax errors,
   compare the macro invocation against current HEAD usages of the same macro
   before assuming a type problem.

5. **C# Build.cs cannot use `#if ENGINE_MAJOR_VERSION`**: that preprocessor is
   for C++. For UBT properties that appear only in newer engines, the cleanest
   fix is usually to **not set the property at all** and work around it (e.g.,
   keep UENUMs out of namespaces instead of setting `bAllowUETypesInNamespaces`).
   Reflection (`GetProperty(...).SetValue(...)`) compiles but old UHT may still
   reject the flag at runtime — verified 2026-08, prefer removal over reflection.

6. **Prefer `__has_include` over version macros for engine feature detection**: in
   C++ headers, `#if defined(ENGINE_MAJOR_VERSION) && (...)` guards are needed
   because older engines may not define `ENGINE_MAJOR_VERSION` at all (5.5 does
   not in all TUs). Where the question is "does this engine header exist", use
   `#if __has_include("Misc/NotNull.h")` — cleaner and reliable (verified 5.5-5.8).

7. **Backporting an engine header is not just copying**: the copied header may
   declare `CORE_API` symbols the older engine does not export (e.g.
   `ReportNotNullPtr` in 5.6's NotNull.h). Replace those with inline definitions
   in the backport. Also verify the header's own includes exist in the target
   engine (5.5 lacks `Traits/IsImplicitlyConstructible.h` — backport it too).

8. **Disabled modules stay in the source tree**: removing a module from
   `.uplugin` Modules disables it for that engine version while keeping the
   files committed (they still build on newer engines). When an engine version
   lacks a large API surface (e.g. 5.5 GameplayCameras `FCameraPose`), disabling
   the module is cleaner than commenting out dozens of calls.

9. **Backporting a type template is namespace-sensitive**: when copying
   `TStructView<T>` / `TConstStructView<T>` from a newer engine, they live in
   the **global namespace** — putting them in a namespace (e.g. `UE::StructUtils`)
   silently breaks every use site with "argument list missing after assumed
   function template" (C7568). Verify the namespace of the source before
   backporting.

10. **Compiler version drives fmt incompatibilities**: UE 5.4 built with MSVC
    14.38 cannot parse fmt 12's `FMT_APPLY_VARIADIC` (int[] pack-expansion
    trick) and promotes its internal `C4459` shadow warnings to errors. Fixes:
    replace the macro with a C++17 fold expression, and lower
    `ShadowVariableWarningLevel` to Warning on that engine. Also, wrapping the
    fmt include in `THIRD_PARTY_INCLUDES_START/END` made things worse (C2143) —
    keep the include plain.

11. **Older MSVC requires `typename` for dependent types**: code like
    `TComponentType::FInstanceDataType* GetInstanceData(...)` compiles on 5.8's
    compiler but fails on 5.4 (14.38) with C2187 `'*' was unexpected`. Add
    `typename` even where newer compilers tolerate its absence.

12. **Engine version in Build.cs**: `ModuleRules` has no `Version` property on
    5.4 — use `target.Target.Version.MajorVersion` / `.MinorVersion`
    (ReadOnlyBuildVersion). This is how to condition Build.cs behavior per engine
    version in C# (C++ `#if ENGINE_MAJOR_VERSION` does not work there).

13. **Verify each engine at its adaptation endpoint, not the working tree**: after
    an interactive rebase reorders commits, a build from the working tree mixes
    commits from multiple versions and can fail confusingly (e.g. a 5.3 commit's
    UFUNCTION conflicting with 5.4's UHT). Check out each version's last
    adaptation commit (`Changed: set engine version X.Y`'s parent) and build
    there. This isolates per-version correctness. Verified 2026-08: 5.4 and 5.3
    both pass at their endpoints.

14. **UHT forbids `UFUNCTION` inside `#if` preprocessor blocks**: you cannot
    version-guard a `UFUNCTION` declaration (only `WITH_EDITORONLY_DATA` is
    allowed). To expose an engine-added method only on old engines (e.g.
    `IsPendingDisable` added to `UCameraModifier` in 5.4), declare it as a plain
    method under the `#if` guard — it still works from C++, just not Blueprint.

15. **Oldest engine is the compatibility floor**: when the newest code uses a
    type that simply does not exist in the oldest target (e.g. `FUtf8String`
    added in 5.4, 5.3 has only `TUtf8StringBuilder` + `FUtf8StringView`),
    backport a minimal stand-in rather than copying the full engine class
    (5.4's FUtf8String is macro-template generated — not copyable). A lightweight
    version (TArray<UTF8CHAR> + Printf via FCStringAnsi::GetVarArgs) suffices
    for the used API surface.

---

## How to Add New Patterns

After you encounter and fix a new type of compilation error, add it here
so the skill improves for future adaptation cycles.

### Template for new pattern

```markdown
## Pattern N: <Category>

### `<Description>`

**Error**:
```
error CXXXX: 'exact message text'
```

**Cause**: <Why this fails — which version introduced/removed what>

**Fix**: <Strategy — wrap, replace, guard, etc.>

**Before** (`<file>`):
```cpp
// code that caused the error
```

**After** (`<file>`):
```cpp
// code after fix
```
```

### Rules for contributions

- **Use exact error text** — copy from build log verbatim so future AI can
  match by searching for the same string
- **Show real file paths** relative to the plugin root (e.g., `Source/<DepName>/Public/...`)
- **Include both Before and After** — minimal diff style
- **Note which version transition** caused it (e.g., "5.4 code running on 5.3")
- **Add the symbol** to the "Which version added this?" table in
  [version-diff-guide.md](version-diff-guide.md)
- **Keep patterns ordered by error code** (C1083, C2039, C2065, C2440, C2664, C3861, etc.)
