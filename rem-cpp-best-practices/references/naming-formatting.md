# Naming & Formatting Reference

Extended examples for naming conventions and formatting rules. The rules
themselves are summarized in the main SKILL.md; this file holds the full
detail and code samples.

---

## 1. Naming details

### Type prefixes (UHT-enforced)

| Prefix | Kind | Example |
|--------|------|---------|
| `U` | UObject subclass (non-Actor) | `URemActorComponent` |
| `A` | AActor subclass | `ARemCharacter` |
| `F` | Plain struct or non-UObject class | `FRemFooBase`, `FRemBarContainer` |
| `E` | Enum / enum class | `ERemFooOperator` |
| `I` | Abstract interface class | `IRemCommonModule`, `IRemScriptStructInterface` |
| `T` | Class template | `TRemFooCurve` |
| `C` | Concept (C++20) | `CInstanceOf`, `CUObject`, `CStringable` |
| `b` | Boolean variable / bitfield | `bInitialized`, `bIsDead` |

### Namespace structure

```
Rem::               — root namespace for all free functions
Rem::Math::         — math/lerp/clamp utilities
Rem::Struct::       — struct/view utilities
Rem::Enum::         — enum utilities
Rem::Subsystem::    — subsystem accessors
Rem::Latent::       — latent action helpers
Rem::ScopeExit::    — scope guard utilities
Rem::Animation::    — animation helpers
Rem::Object::       — object utilities
Rem::Private::      — internal implementation details (never in public API)
```

Every free utility function lives in `Rem::` or a sub-namespace.

### Function & member naming

- **PascalCase** everywhere: types, functions, members, locals, parameters
- **No abbreviations, full words** — names are the primary source of type
  information in `auto`-heavy code. `AbilitySystem`, not `ASC`;
  `MovementComponent`, not `MoverComp`. Contractions that squeeze a word
  (dropping interior characters) are also abbreviations and are prohibited:
  `Instance`, not `Inst`; `Seconds`, not `Sec`. Single-letter names (`T`,
  `U`, `A`, `B`) reduce readability and break IDE search. Exceptions only for:
  - Extremely well-known acronyms (`FOV`, `LOD`)
  - The abbreviation IS the type name (e.g., `IO` as a domain concept)
  - Template parameters (where `T` is the convention)
  - Lambda comparator parameters in `Sort` / `FindBy` where the context is
    limited to a single expression line — only there `A`/`B` are acceptable
- **No abbreviations** extends to local variables, function parameters, data
  members — every name must be self-documenting
- **Getter**: `Get<Name>()` — `GetOwner()`, `GetComponentIndex()`
- **Bool check**: `Is<Condition>()` / `Has<Property>()` — `IsInitialized()`, `HasTag()`, `ShouldTick()`
- **Output params**: prefix `Out` — `void GetItems(TArray<FItem>& OutItems)`
- **Non-const getter pair**: define both `const` and non-`const` overloads returning `auto&&`
- **Function objects**: `Rem::Fn::FunctionName` — via `REM_FUNCTION_TO_FUNCTOR_SIMPLE`

### Template parameter naming

- `T` for single generic type
- `BaseStructT`, `TOwner`, `EnumClass` for named constraints
- Concept names are PascalCase inside `Rem::` — `CInstanceOf<T>`, `CUObject<T>`

### `using ThisClass` alias

`GENERATED_BODY()` auto-declares:
- `UCLASS`: both `using Super = ...;` and `using ThisClass = ...;`
- `USTRUCT`: only `using Super = ...;` — no `ThisClass`

Define `using ThisClass = FMyType;` manually for USTRUCTs where needed.
For non-reflected F-classes, define both on an as-needed basis:

```cpp
USTRUCT()
struct FMyData : public FBase
{
    GENERATED_BODY()

    using ThisClass = FMyData;   // USTRUCT gets Super from UHT, add ThisClass manually
    // Super already declared by GENERATED_BODY

    float Speed{};
    void Apply();
};

// Non-reflected class:
class FMyHelper : public FBase
{
    using ThisClass = FMyHelper;  // as needed
    using Super = FBase;          // as needed
};
```

`using` declarations are treated as **data** in the member ordering rule —
they appear immediately after `GENERATED_BODY()`, before `UPROPERTY` data
members and before any function declarations.

---

## 2. Formatting details

### Braces & indentation

```cpp
struct FExample
{
    GENERATED_BODY()

    void DoThing()
    {
        if (Condition)
        {
            Statement();
        }
    }
};
```

- **Allman braces** — opening brace on its own line for every construct (functions, classes, if, for, while, namespace)
- **Spaces** for indentation, 4-character width
- **One statement per line**
- **Pointer/reference spacing**: `Type* Ptr` / `const Type& Ref` — `*` and `&` bind to the type (right-hand)
- **Explicit braces** on all blocks — even single-statement branches

### Comment formats — `/** */` for declarations, `//` for implementations

- **`/**` Doxygen-style comments** — on public declarations in headers (types, functions, variables).
  IDE shows these on hover; Doxygen/doc generators parse them:
  ```cpp
  /**
   * Functor wrapper for UE's Cast<T> template.
   *
   * Pass to transrangers::transform as a callable without overload ambiguity.
   */
  template <typename To>
  struct TCast { ... };
  ```

- **`//` line comments** — in `.cpp` implementations, inline inside function bodies,
  and for brief one-line notes:
  ```cpp
  // ── Cast helpers ──
  const auto ChannelData = Section->Channel.GetData();  // lifetime: owned by Section
  ```

- **`///` triple-slash** — not used. Prefer `/** */` for declarations.

- **No namespace closing comments** — `} // namespace Rem` is unnecessary; modern IDEs
  show the enclosing scope on hover / breadcrumb. Close with bare `}`.

### Member ordering

Within a type declaration, data members come before function members.
Data is the most critical information for understanding a class's role — it must
be immediately visible. Each group has its own explicit visibility label:

```cpp
struct FExample
{
    GENERATED_BODY()

public:
    UPROPERTY(EditAnywhere, Category = "Rem")
    float Speed{};

protected:
    UPROPERTY(VisibleAnywhere, Category = "Rem|Component")
    TObjectPtr<UObject> Owner{};

private:
    uint8 bCached : 1{false};

public:
    void GetSpeed() const;
    void SetSpeed(float InSpeed);

protected:
    void InternalUpdate();

private:
    void RecalculateCache();
};
```

Functions with the same visibility are grouped together after the data members
of that visibility. Repeat `public:`/`protected:`/`private:` as needed to express
the grouping.

### Namespace indentation

Namespace contents are NOT indented (the project `.DotSettings` set
`NAMESPACE_INDENTATION = None`, matching `RemNotNull.h`):

```cpp
namespace Rem
{
template <class T>
concept CSomeConcept = requires(T Object) { Object.Foo(); };
}
```

### Rule of Five / Rule of Zero

Explicitly declare or delete all five:

```cpp
// Non-copyable, non-movable container:
FMyType()                                    = default;
FMyType(const FMyType&)                      = delete;
FMyType(FMyType&&) noexcept                  = delete;
FMyType& operator=(const FMyType&)           = delete;
FMyType& operator=(FMyType&&) noexcept       = delete;
~FMyType() noexcept                          = default;

// Or use the macro:
REM_DEFINE_THE_RULE_OF_FIVE(FMyType)
```

### Section organization

Use `#pragma region` / `#pragma endregion` with descriptive names:

```cpp
#pragma region Rule Of Five
// ...
#pragma endregion Rule Of Five
```

For USTRUCT/UCLASS, section order: GENERATED_BODY → public → protected → private.

### Code alignment

Alignment is handled entirely by the Rider `.DotSettings` — see the solution-level
code style file. Manual alignment (column-aligning parameters or declarations) is
disabled; each enum member stays on its own line.

Note: the project `.DotSettings` enable `INT_ALIGN_EQ`, `INT_ALIGN_COMMENTS`,
`INT_ALIGN_DECLARATION_NAMES`, and `INT_ALIGN_DESIGNATED_INITIALIZERS` — so
assignment groups, trailing comments, and designated initializers ARE aligned.
Format with Rider and keep what it produces; never hand-align beyond that.
