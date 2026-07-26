# Macro & Logging Reference

Complete signatures for Rem assertion/log macros and the `REM_DEFINE_*` macro
patterns. Load when writing logging, assertions, or reflected boilerplate.
When-to-use rules live in the main SKILL.md; this file holds the signatures.

---

## 1. Assertion macros — `RemEnsureCondition` / `RemEnsureVariable`

Two primary families, separated by what they validate:

| Macro | Validates | Equivalent to |
|-------|-----------|---------------|
| `RemEnsureCondition(...)` | An arbitrary boolean expression | `if (!LIKELY(Condition)) { ensureAlways(...); Handling; }` |
| `RemEnsureVariable(...)` | A pointer/object via `Rem::IsValid()` | `RemEnsureCondition(..., Rem::IsValid(Pointer), ...)` |

Both accept 1, 2, or 3 arguments via `REM_MULTI_MACRO` overload resolution.
The first optional argument is the **assertion macro** to fire on failure
(defaults to `ensureAlways`). The last optional argument is the **invalid
handling statement** — arbitrary statements executed when the condition is
false (typically `return;`, `return {};`, or a brace-enclosed block).

**Signatures and usage:**

```cpp
// 1 arg: condition only — fires ensureAlways, no handling
RemEnsureCondition(bInitialized);

// 2 args: condition + handling statement (defaults to ensureAlways)
RemEnsureCondition(MoverComp != nullptr, return;);

// 3 args: custom assertion macro + condition + handling
RemEnsureCondition(ensure, MoverComp != nullptr, return;);

// Same overloads for variable validation (uses Rem::IsValid internally):
RemEnsureVariable(MoverComp);                         // ensureAlways, no handling
RemEnsureVariable(MoverComp, return;);                 // ensureAlways + handling
RemEnsureVariable(check, MoverComp, return;);          // check() + handling
```

The assertion macro itself (`ensure`, `ensureAlways`, `check`, `verify`, etc.)
handles messaging — `RemEnsure*` macros do **not** accept log category,
verbosity, or message parameters. Use a `REM_LOG_*` call alongside when a
message is needed:

```cpp
RemEnsureVariable(MoverComp, return;);
REM_LOG_ROLE_FUNCTION(GetOwner(), LogRemMover, Warning, "Component not found");
```

The invalid handling statement is wrapped by `REM_INVALID_HANDLING_STATEMENT`
which strips it when `REM_LET_IT_CRASH` is defined — use this for final builds
that should crash instead of silently returning.

**Branch prediction:** `RemEnsureCondition` internally uses `LIKELY` /
`UNLIKELY` — the failure path is cold and the check has near-zero overhead
on the hot path. `RemEnsureVariable` delegates to `RemEnsureCondition`.

## 2. `RemCheckCondition` / `RemCheckVariable`

Currently **aliases** for `RemEnsure*` when `DISABLE_CHECK_MACRO` is `false`
(the default). They share identical signatures and behavior.

The intended semantic distinction:
- `RemCheck*` — developer-error checks, intended to be stripped in shipping
  (gated by `DISABLE_CHECK_MACRO` in the future)
- `RemEnsure*` — runtime-possible states, always active

| Setting | Effect |
|---------|--------|
| `DISABLE_CHECK_MACRO = false` (default) | `RemCheck*` is identical to `RemEnsure*` |
| `DISABLE_CHECK_MACRO = true` | `RemCheck*` compiles to nothing |

**Usage:**

```cpp
RemCheckCondition(bInitialized);
RemCheckVariable(Pointer, return;);
RemCheckVariable(check, CriticalPtr, return;);
```

## 3. Config macros

| Macro | Effect |
|-------|--------|
| `REM_LET_IT_CRASH` | Strips all invalid handling statements — failures become fatal |
| `REM_DISABLE_ASSERTION` | Disables the assertion self-test (`REM_ASSER_CONDITION_EVALUATED`) |
| `DISABLE_CHECK_MACRO` | Strips `RemCheck*` macros entirely |
| `NO_LOGGING` | Strips all `REM_LOG_*` macros (see section 4) |
| `REM_NO_ASSERTION` | Readability placeholder — no diagnostic, no handling |
| `REM_NO_HANDLING` | Readability placeholder — diagnostic only, no handling |
| `REM_NO_ASSERTION_OR_HANDLING(Condition)` | Readability: assert only, no handling, explicit condition |

## 4. Log macros — `REM_LOG_ROLE` / `REM_LOG_FUNCTION` / `REM_LOG_ROLE_FUNCTION`

Three base families, distinguished by what decorator is prepended/appended to
the log message:

| Macro | Decorator |
|-------|-----------|
| `REM_LOG_ROLE(Object, Category, Verbosity, Format, ...)` | Net role name (Server/Client/etc.) prepended |
| `REM_LOG_FUNCTION(Category, Verbosity, Format, ...)` | `__FUNCTION__:line` appended |
| `REM_LOG_ROLE_FUNCTION(Object, Category, Verbosity, Format, ...)` | Both: role prepended, function appended |

Each family has two additional variants:

| Suffix | First extra parameter | Behavior |
|--------|-----------------------|----------|
| `_COND` | `Condition` | Logs only when condition is true (branch annotated `UNLIKELY`) |
| `_CVAR` | `ConsoleVariableName` | Logs only when the named CVar is true; `REM_ENSURE`s that the CVar exists |

Plus one scope-based macro:

| Macro | Behavior |
|-------|----------|
| `REM_SCOPED_LOG(Object, Category, Verbosity, LogStart, LogEnd)` | Logs `LogStart` on scope entry, `LogEnd` on scope exit (via `ON_SCOPE_EXIT`) |

When `NO_LOGGING` is defined, all `REM_LOG_*` macros compile to nothing.

**Format string:** Uses `{}` placeholder syntax (no numbers — `fmt` infers argument
order). `Rem::Format` delegates to `fmt::format_to` which writes into a
`TUtf8StringBuilder<256>`. Output goes through `UE_LOGF` with the `%hs` narrow-string
format specifier. Always specify the category explicitly — there is no default.

**Usage:**

```cpp
REM_LOG_ROLE(GetOwner(), LogRemMover, Warning,
    "Value: {}, Delta: {}", Value, DeltaTime);

REM_LOG_FUNCTION(LogRemMover, Verbose,
    "Tick at {}", GetWorld()->GetTimeSeconds());

REM_LOG_ROLE_FUNCTION(GetOwner(), LogRemMover, Error,
    "Fatal state in {}", GetNameSafe(this));

// Conditional — logs only when bVerbose is true:
REM_LOG_FUNCTION_COND(bVerbose, LogRemMover, Verbose,
    "Extra detail: {}", Detail);

// CVar-gated — logs only when "Rem.Mover.Debug" console variable is true:
REM_LOG_FUNCTION_CVAR(TEXT("Rem.Mover.Debug"), LogRemMover, Warning,
    "Debug info: {}", Info);
```

## 5. Raw ensure wrappers — `REM_ENSURE` / `REM_ENSURE_ALWAYS`

Thin wrappers around Unreal's built-in assertion macros that switch between
lightweight and standard implementations based on build configuration:

| Macro | Wraps | Lightweight mode |
|-------|-------|-----------------|
| `REM_ENSURE(Expr)` | `ensure(Expr)` | ALS-style (no callstack) |
| `REM_ENSURE_ALWAYS(Expr)` | `ensureAlways(Expr)` | ALS-style (no callstack) |
| `REM_ENSURE_MESSAGE(Expr, Fmt, ...)` | `ensureMsgf(Expr, Fmt, ...)` | ALS-style |
| `REM_ENSURE_ALWAYS_MESSAGE(Expr, Fmt, ...)` | `ensureAlwaysMsgf(Expr, Fmt, ...)` | ALS-style |

Lightweight mode is active when `REM_WITH_DEVELOPMENT_ONLY_CODE` is true (i.e. in
editor/development builds). In non-development builds, these fall back to the
standard Unreal `ensure*` macros which include callstack capture and report
submission.

## 6. Custom log categories

```cpp
// Header:
DECLARE_LOG_CATEGORY_EXTERN(LogRem, Log, All);

// Source:
DEFINE_LOG_CATEGORY(LogRem);
```

Then:
```cpp
UE_LOGF(LogRem, Warning, TEXT("Value: %d"), SomeValue);
```

---

## 7. `REM_DEFINE_*` getter macros (preferred over manual getters)

```cpp
// Full getter — returns reference, const + non-const:
REM_DEFINE_GETTERS_RETURN_REFERENCE(/*NamePredicate*/, /*NameSuffix*/, ReturnExpression)

// Value getter — returns by value, const only:
REM_DEFINE_GETTERS_RETURN_VALUE(/*NamePredicate*/, /*NameSuffix*/, ReturnExpression)

// Simple reference getter (predicate == suffix):
REM_DEFINE_GETTERS_RETURN_REFERENCE_SIMPLE(Name)

// Const-only reference getter:
REM_DEFINE_CONST_ONLY_GETTERS_RETURN_REFERENCE(NamePredicate, ReturnExpression)

// Template variant:
REM_DEFINE_TEMPLATE_GETTER_RETURN_VALUE(Concept, NamePredicate, NameSuffix, ReturnExpression)
```

Usage example:
```cpp
USTRUCT()
struct FRemFooWrapper
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, Category = "Rem")
    float Number{};

    REM_DEFINE_GETTERS_RETURN_REFERENCE(/*no predicate*/, /*no suffix*/, Number)
};
// Generates: GetNumber() const and GetNumber() (non-const), both return auto&&
```

**`CONST_ONLY` getters are read-only; plain getters return a mutable reference.**
`REM_DEFINE_CONST_ONLY_GETTERS_RETURN_REFERENCE[_SIMPLE]` expands to only
`auto&& GetX() const { return X; }` — inside a `const` member function the member is a
`const` lvalue, so `auto&&` deduces `const T&`; the result stays read-only even on a
mutable object. `REM_DEFINE_GETTERS_RETURN_REFERENCE[_SIMPLE]` instead generates both a
`const` and a non-`const` overload — the non-`const` one returns `T&`, so `GetX() = Value`
is valid and modifies the member. Use a setter for modifications (clearer intent, room for
validation); the mutable reference is the escape hatch, not the default. When a class is
`CONST_ONLY` and callers must override the value (e.g. tests temporarily swapping
configured classes), the write needs a setter or `REM_DEFINE_PRIVATE_MEMBER_ACCESSOR`
(§9) — the const getter cannot do it.

## 8. Other `REM_*` patterns

```cpp
REM_DEFINE_THE_RULE_OF_FIVE(Type)  // declares all 5 as = default
```

```cpp
REM_DEFINE_GET_SCRIPT_STRUCT_INTERFACE  // generates GetScriptStruct() override
```

```cpp
REM_FUNCTION_TO_FUNCTOR_SIMPLE(IsValid)  // creates Rem::Fn::IsValid
```

### Deleted-copy marker on USTRUCT required by engine

```cpp
template <>
struct TStructOpsTypeTraits<FMyStruct> : TStructOpsTypeTraitsBase2<FMyStruct>
{
    enum { WithCopy = false };
};
```

---

## 9. `REM_DEFINE_PRIVATE_MEMBER_ACCESSOR`

Alternative to UE's `UE_DEFINE_PRIVATE_MEMBER_PTR()` that also works with overloaded
member functions, zero-argument member functions, and static members. Based on the
ALS-Refactored `AlsPrivateMemberAccessor.h` pattern (public). Declared in the
`RemPrivateMemberAccessor.h` macro header of RemCommon. Use it to read or write private
members of engine or third-party types that expose **no public API**; when a public getter
exists, prefer it over the accessor — plain (non-`CONST_ONLY`) getters even allow writes
through their non-const overload, and a setter is the clearest option (see §7 for the
`CONST_ONLY` read-only nuance).

```cpp
REM_DEFINE_PRIVATE_MEMBER_ACCESSOR(AccessorName,
    &UFoo::Member,   // pointer to member (plain pointer for a static member)
    MemberType);     // e.g. int32 UFoo::*, int32 (UFoo::*)(int32) const, int32*
```

`AccessorName::Access(Receiver, Args...)` reaches the member:

| Member kind | Call | Result |
|---|---|---|
| data member | `Access(Obj)` | `T&` — read/write |
| const data member | `Access(Obj)` | `const T&` — read-only |
| member function, with arguments | `Access(Obj, Args...)` | call result |
| member function, zero arguments | `Access(Obj)` | call result |
| any of the above through a pointer receiver | `Access(ObjPtr, ...)` | same, via `->*` |
| static data member / function | `Access(Obj, ...)` | member value / call result — receiver ignored |

Dispatch is by member-pointer type (`std::is_member_function_pointer_v`, member-object
branch, plain-pointer branch), not by argument count — so zero-argument member functions
are invoked rather than misread as data members. `Access` always takes the receiver
first; for static members the receiver argument is required but ignored. Static-member
support and zero-argument member functions: last verified 2026-08.

```cpp
struct UFoo
{
private:
    int32 Secret{7};
    int32 Multiply(const int32 Factor) const { return Secret * Factor; }

    static int32 StaticValue;
};

int32 UFoo::StaticValue = 10;

REM_DEFINE_PRIVATE_MEMBER_ACCESSOR(GSecretAccessor, &UFoo::Secret, int32 UFoo::*);
REM_DEFINE_PRIVATE_MEMBER_ACCESSOR(GMultiplyAccessor,
    &UFoo::Multiply, int32 (UFoo::*)(int32) const);
REM_DEFINE_PRIVATE_MEMBER_ACCESSOR(GStaticAccessor, &UFoo::StaticValue, int32*);

GSecretAccessor::Access(*Foo) = 5;   // write
GMultiplyAccessor::Access(*Foo, 3);  // call
GStaticAccessor::Access(*Foo);       // static value; receiver ignored
```
