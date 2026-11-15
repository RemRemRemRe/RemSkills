# Type Mapping & Reflection Specifiers

Reference tables for type selection and UPROPERTY/UFUNCTION specifiers.
Load when writing reflected properties or choosing between STL and UE types.
Rules of thumb live in the main SKILL.md; this file holds the complete tables.

---

## 1. UObject pointer types by context

| Context | Type to use |
|---------|-------------|
| `UPROPERTY` member | `TObjectPtr<UObject>` |
| Function parameter | `TNotNull<UObject*>` / `TNotNull<const UObject*>` — null is not allowed by default |
| Function return | `TNotNull<UObject*>` for the non-null contract; bare `UObject*` only for the nullable half (`TryGet*`) |
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

### `const` UObject pointer

```cpp
TObjectPtr<const UObject> ConstObj{};  // UPROPERTY: the pointee's const is fine
const UObject* ConstPtr = ...;         // non-UPROPERTY: a read-only local or parameter
```

A `UPROPERTY` member itself cannot be const-qualified (UHT: `Const properties are not supported.`,
`UhtPropertyParser.cs`), but the **pointee's** constness is expressible and supported:
`TObjectPtr<const UObject>` and `TArray<TObjectPtr<const UObject>>` are valid members (a reflected
settings asset in a consuming project stores its asset array as `TArray<TObjectPtr<const …>>` and
builds). Keep that const when the type's API promises it — dropping it to satisfy the `TObjectPtr` rule
loses a real semantic. A project may also leave a `const T*` member raw until its `TObjectPtr<const T>`
conversion is planned; that is a migration state, not a legal shape exception.

**Dropping the const charges a `const_cast` at every assignment.** A const-returning API (an asset
lookup, a `Cast<T>` whose source is const) binds straight into `TObjectPtr<const T>` and needs a cast
into `TObjectPtr<T>`:

```cpp
const UDataAsset* Loaded = ResolveAsset();      // the API hands out const
TObjectPtr<const UDataAsset> Kept = Loaded;     // ok: the const survives
TObjectPtr<UDataAsset> Mutable = const_cast<UDataAsset*>(Loaded);   // the cost of dropping it
```

That is the reason to prefer `TObjectPtr<const T>` over dropping the const when the member is not
written through.

**A getter that returns a reference into the member cannot survive the conversion.** `T* const& Get()`
(or an `auto&&` family) would have to expose `TObjectPtr<T>&` — a storage type in the API. Replace it
with a value getter returning `.Get()`; a `Get*Ref` name does not survive a `TObjectPtr` conversion.

**The rule is enforced by the header tool — enable it instead of scanning by hand.**
`TargetRules.NativePointerMemberBehaviorOverride = PointerMemberBehavior.Disallow` in the target files
makes UHT reject a raw `UObject`-pointer member, and it covers **container element types**: a probe
declaring both `APawn* Member;` and `TArray<APawn*> Array;` produced two errors of the same shape
("Native pointer usage in member declaration detected [[[APawn*]]] … consider TObjectPtr as an
alternative"). UBT forwards the setting as `-ini:Engine:[UnrealHeaderTool]:…NativePointerMemberBehavior=`.
Measured 2026-11: the same key written only into `DefaultEngine.ini`
(`NonEngineNativePointerMemberBehavior=Disallow`) had **no effect** — the probe members compiled — so
the TargetRules override is the switch that works.

The check sees **reflected** members only (`UPROPERTY`), so a non-UPROPERTY UObject member stays invisible
to UHT (the analysis' garbage-collection warning is the signal there); `TStateTreePropertyRef` bindings
are not its business. The signature half is already a UHT error for reflected functions ("UFunctions
cannot take a TObjectPtr as a function parameter or return value", `UhtClassProperty.cs`); a plain C++
function is not seen.

Epic also ships the **converter**: `UnrealObjectPtrTool` (`Engine/Source/Programs/UnrealObjectPtrTool`)
reads the UHT log's `Native pointer usage in member declaration detected [[…]]` lines and rewrites the
declarations — `-n|PREVIEW` to count first, `-r|REVERSE` for the opposite direction, `-SCCCommand=` to
check files out — defaulting to `Engine/Programs/UnrealHeaderTool/Saved/Logs/UnrealHeaderTool.log`. With
the check at `Disallow` a violation is an error rather than a log line, so run the tool against a build
made with `AllowAndLog` when you want it to do the rewriting.

`TObjectPtr` never appears in a function parameter, a return type or a local variable: those
carry raw `T*` (or `TNotNull` for the non-null contract). The one exception is a parameter that has
to name a `UPROPERTY` container's element type, where no raw spelling exists:

```cpp
void Walk(const TConstArrayView<TObjectPtr<UObject>> Objects);   // no raw equivalent
void Walk(const TArray<UObject*>& Objects);                     // reject: a UPROPERTY array of
                                                                // TObjectPtr does not convert to it
```

Two consequences that cost time when a member is converted (measured 2026-11):

- **An array of raw pointers does not assign into an array of `TObjectPtr`.** The cross-element copy
  constructor is `explicit`, so `TArray<AActor*> Plain; TArray<TObjectPtr<AActor>> Wrapped = Plain;`
  does not compile — use `Wrapped.Reset(); Wrapped.Append(Plain);` (and the reverse direction for a
  read: `TConstArrayView<AActor*> PlainView = Wrapped;` does convert, through
  `TContainerElementTypeCompatibility`).
- **`auto*` cannot deduce through a `TObjectPtr` element.** In a range-for over `TArray<TObjectPtr<T>>`
  bind `auto& Element` and use `Element->…` / `Element.Get()`; `IsValid` overloads in the project's
  utilities already accept `TObjectPtr`, so a validity check needs no `.Get()`.

---

## 2. UPROPERTY patterns

```cpp
// Object reference — always AddFilterUI
UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rem",
          meta = (AddFilterUI = true))
TObjectPtr<UObject> Object{};

// Array of wrappers — TitleProperty for display
UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rem",
          meta = (AddFilterUI = true, TitleProperty = Object))
TArray<FRemFooWrapper> Objects;

// Instanced struct collection — ExcludeBaseStruct
UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Rem|Component",
          meta = (ExcludeBaseStruct))
TArray<TInstancedStruct<FRemFooBase>> Components;

// Boolean — only use bitfield when it actually saves memory under alignment
UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Rem|Component")
bool bInitialized{false};

// Bitfield only when packing gains real space (multiple flags adjacent):
UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Rem|Component")
uint8 bFlagA : 1{false};
UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Rem|Component")
uint8 bFlagB : 1{false};

// Numeric with constraints — ForceUnits keeps display unit fixed (Units would auto-scale)
UPROPERTY(EditAnywhere, Category = "Rem", meta = (ClampMin = "0", ForceUnits = "s"))
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

A reflected member that the editor or Blueprint exposes **carries a Category**; the
value belongs to the authoring module, not to this skill:

- **No grouping of its own → `"Rem"`** (or `"Rem|SubCategory"` when the module
  groups its properties under Rem).
- **A module with its own grouping keeps it.** `"Parameter"`, `"Data"`,
  `"Projectile"`, `"Event"` are legitimate when that module's details panels are
  organised that way — do not rewrite them to `Rem|…` in passing. A review
  finding is a *missing* Category, never a non-`Rem` one (ruled 2026-11).
- **Not exposed → no Category needed**: `UFUNCTION(Exec)` console commands, a
  `UPROPERTY()` that exists only for reflection, anything the details panel never
  shows. On an `Exec` command `Category` is inert metadata (§10).

```cpp
Category = "Rem"            // the default when the module has no grouping
Category = "Rem|Object"     // a module that groups everything under Rem
Category = "Projectile"     // a module that owns its own grouping
```

### Metadata completeness

Which metadata a property needs, by kind (`SKILL.md` §10 has the rule of
thumb; this is the lookup table):

| Property kind | Metadata | Example |
|---|---|---|
| Quantity with a physical unit | `ForceUnits` (+ `ClampMin`/`ClampMax` if ranged) | `meta = (ClampMin = "0", ForceUnits = "s")` |
| Bounded ratio displayed as a percentage | `ForceUnits = "%"` — `EUnit::Percentage` with a factor of 0.01, so `0`–`1` renders as `0`–`100%` | `meta = (ForceUnits = "%")` |
| Unitless number with a valid range | `ClampMin`/`ClampMax` when out-of-range values are invalid, and the tooltip states the meaning | `meta = (ClampMin = "0", ClampMax = "1")` |
| Object reference | `AddFilterUI`; `AllowedClasses` to narrow | `meta = (AddFilterUI = true, AllowedClasses = "/Script/Engine.Actor")` |
| Class reference | `MetaClass` when the base type is too permissive | `meta = (MetaClass = "/Script/Engine.Actor")` |
| Array of wrappers | `TitleProperty` | `meta = (TitleProperty = Object)` |
| Instanced struct collection | `ExcludeBaseStruct` | `meta = (ExcludeBaseStruct)` |
| Value valid only in one mode | `EditCondition` — never document the condition in a comment | `meta = (EditCondition = "bUseFoo")` |
| Edit-time derived data | `EditConditionHides` where it hides, plus a `PostEditChangeProperty` handler — do not leave the rebuild implicit | `meta = (EditConditionHides, EditCondition = "bUseFoo")` |
| Value needing explanation | `ToolTip`, or a `/** */` doc comment (the editor shows both) | `meta = (ToolTip = "Seconds before the entry expires.")` |
| Every member the editor or Blueprint exposes | `Category` | `Category = "Rem|Component"` |

Unit strings follow the engine's unit identifiers (`s`, `cm`, `kg`, `deg`, `%`, ...).
A tooltip restates the unit in words when the identifier alone could be
misread — `ForceUnits` fixes the display, it does not explain the quantity.

A comment next to a declaration is **user-visible text** when it becomes the
tooltip, so it carries meaning, not bookkeeping: no specifier text, no
preprocessor lines (`SKILL.md` §4).

## 3. UFUNCTION patterns

```cpp
UFUNCTION(BlueprintPure, Category = "Rem|Object",
          meta = (DeterminesOutputType = "ObjectClass"))
static UObject* GetObject(const TSoftObjectPtr<UObject>& SoftObjectPtr,
                          UClass* ObjectClass);

UFUNCTION(BlueprintCallable, Category = "Rem",
          Meta = (DevelopmentOnly, CompactNodeTitle = "Do Nothing"))
static void DoNothing();
```

---

## 4. STL vs UE types

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
| `FString` | `std::string` | Engine legacy wide-string; `FUtf8String` works as UPROPERTY and should be used instead |
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

### `TArray::Add` vs `TArray::Emplace`

`Add` delegates to `Emplace` internally:

```cpp
SizeType Add(ElementType&& Item) { return Emplace(MoveTempIfPossible(Item)); }
SizeType Add(const ElementType& Item) { return Emplace(Item); }
```

No performance difference. The distinction is semantic:

| Context | Use |
|---|---|
| Adding an **existing value** (copy or move) | `Add(Value)` / `Add(MoveTemp(Value))` |
| Constructing **in-place** from constructor args | `Emplace(Arg1, Arg2)` |
| Constructing via **explicit** constructor (e.g. `TInstancedStruct` from `TConstStructView`) | `Emplace(View)` — `Add` cannot use explicit ctors |

Default to `Add` when you have a value; `Emplace` when you have constructor args
or the target type's constructor is explicit.

### String type priority

`FUtf8String` is the **primary** string type for all new code. `FString` (a.k.a.
`FWideString`) is legacy — use only when the engine API demands it. `FAnsiString`
is not used in this project.

| String type | When to use |
|-------------|-------------|
| `FUtf8String` | Default for all return values, parameters, and storage |
| `FUtf8StringView` | Pass-by-value; read-only slices without allocation |
| `TUtf8StringBuilder<N>` | Build strings incrementally (N=256 for typical messages) |
| `TStringBuilderBase<UTF8CHAR>&` | Output parameter for builder-based `ToString(Builder, Value)` |
| `FString` / `FWideString` | Legacy — only when the UE API requires it; convert to `FUtf8String` ASAP |
| `FStringView` | Legacy — only when the UE API requires it |
| `FAnsiString` | Not used — prefer `FUtf8String` for ANSI-range content |

All string-building flows go through `Rem::Format` which wraps `fmt::format_to`
directly into a `TStringBuilderBase<CharType>`. Format strings use `{}`
placeholders (no numbers needed — `fmt` infers argument order).

```cpp
// Return FUtf8String by default:
[[nodiscard]] FUtf8String ToString() const;

// Builder-based output (zero allocation):
void ToString(TStringBuilderBase<UTF8CHAR>& Builder) const;

// Formatting with {} placeholders:
Rem::Format("Value: {}, Delta: {}", Value, DeltaTime);
```

### No structured bindings

Do not use structured bindings (`auto [a, b] = ...`). Debugger support
(VS / Rider) remains incomplete — variables show as unviewable.

### Float literals stay typed

```cpp
float Value = 1.0f;    // NOT 1.0 (would be double)
double Value = 1.0;    // NOT 1.0f (would be float)
int32 Value = 1;       // fine
```
