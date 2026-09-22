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
TObjectPtr<const UObject> ConstObj{};  // UPROPERTY
const UObject* ConstPtr = ...;         // non-UPROPERTY
```

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

Always `"Rem"` or `"Rem|SubCategory"`:

```cpp
Category = "Rem"
Category = "Rem|Object"
Category = "Rem|Component"
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
| Every reflected member | `Category` | `Category = "Rem|Component"` |

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
