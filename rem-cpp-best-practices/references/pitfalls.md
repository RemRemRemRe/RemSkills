# Verified Pitfalls

Pitfalls verified in real builds and test runs. Each entry:
symptom → cause → fix → verification. Entries are dated; re-verify after an
engine or dependency bump. The engine behaviors here are generic UE; the
Rem-specific entries name Rem APIs as documented in this skill.

## UHT / UPROPERTY

### `TWeakInterfacePtr` cannot be a `UPROPERTY` (verified 2026-08)

- **Symptom** — UHT error `Unable to find 'class', 'delegate', 'enum', or
  'struct' with name 'TWeakInterfacePtr'` when a `TWeakInterfacePtr<T>` member
  carries `UPROPERTY`.
- **Cause** — `TWeakInterfacePtr` is not a supported UPROPERTY type (unlike
  `TObjectPtr`, `TScriptInterface`, `TWeakObjectPtr`).
- **Fix** — keep the member non-UPROPERTY and document the weak-hold intent in
  a comment; the weak pointer self-invalidates when the object dies.
- **Verification** — UHT fails with the marker; removing the UPROPERTY
  compiles and the pointer still invalidates.
- **Applies to** — UE 5.8.

### `UPROPERTY` cannot live inside a preprocessor block (verified 2026-09)

- **Symptom** — UHT hard error pointing at the declaration:
  `'UPROPERTY' must not be inside preprocessor blocks, except for WITH_EDITORONLY_DATA`.
- **Cause** — UHT parses headers on its own, with its own macro set (the build
  config macros it knows, such as `WITH_EDITORONLY_DATA`). A member guarded by any
  other macro — a project feature flag — therefore cannot be reflected: the
  reflection would not exist in every configuration the header compiles in.
- **Fix** — choose one end state: keep the guard and leave the member
  non-UPROPERTY (accept that nothing may reflect it), or drop the guard and reflect it
  in all configurations. The half-state — guarded *and* reflected — does not compile.
- **Verification** — adding `UPROPERTY` inside such a guard fails the build with that
  exact UHT message; reverting the `UPROPERTY` builds clean.
- **Applies to** — UE 5.8.

### `NewObject` inside an actor constructor is illegal (verified 2026-08)

- **Symptom** — runtime `NewObject with empty name can't be used to create
  default subobjects (inside of UObject derived class constructor)`, fatal at
  module load / spawn.
- **Cause** — during construction, subobjects must come from the
  `ObjectInitializer`; `NewObject` is not allowed in a constructor.
- **Fix** — create the object after spawn (outer = the actor) from the caller,
  or use `CreateDefaultSubobject` in the constructor.
- **Verification** — the callstack points at the constructor line; the fixed
  code runs clean in the test world.

## Assertion macros

### `RemCheck*` / `RemEnsure*` need the macro header included (verified 2026-08)

- **Symptom** — MSVC `C2760: syntax error: ',' was unexpected here; expected
  ')'` at the macro call site.
- **Cause** — `RemCheckVariable` / `RemEnsureVariable` / `RemCheckCondition`
  are macros from `Macro/RemAssertionMacros.h`; without the include the
  compiler parses the call as a function invocation and the statement argument
  breaks the syntax.
- **Fix** — `#include "Macro/RemAssertionMacros.h"` in the TU (IWYU: never
  rely on a transitive include).
- **Verification** — the same code compiles after the include; `get_file_problems`
  stays clean.

## UE types

### Struct copies reset non-reflected members (verified 2026-09)

- **Fact** — `UScriptStruct::CopyScriptStruct` copies through one of three paths:
  native C++ copy when the struct is `STRUCT_CopyNative` and its ops implement `Copy`
  (declare `TStructOpsTypeTraits<T>{ WithCopy = true }` for that); a raw `memcpy` when
  the struct is plain old data; **property-by-property reflection copy otherwise**.
  Only the memcpy path carries non-reflected members; on the reflection path they keep
  whatever `InitializeStruct` left, i.e. their default.
- **Use** — "per-instance runtime state that must NOT travel with a copy" (a
  bound/registered flag, a cached handle) is correctly modeled as a plain
  non-UPROPERTY member of a non-POD USTRUCT: copies of the holder start in the
  default state. Because that behavior is load-bearing, state the intent on the
  member instead of leaving it looking accidental.
- **Do not** reach for `UPROPERTY(DuplicateTransient)` to get the same effect:
  `CPF_DuplicateTransient` is consulted when duplicating **UObjects**
  (`FObjectDuplicationParameters`), not by `CopyScriptStruct` — a reflected member
  *is* copied into struct copies, which turns the designed reset into a carried
  stale flag.
- **Want custom copy semantics instead?** Declare
  `TStructOpsTypeTraits<T> : TStructOpsTypeTraitsBase2<T>` with `WithCopy = true` and
  supply the C++ copy constructor/assignment; UE then calls them and the copy is
  responsible for resetting transient state explicitly.
- **Verification** — confirmed with an automation case that deep-copies a struct
  whose holder is currently in the non-default runtime state, re-registers the copy,
  and asserts the copy's own callback fires while the source stays registered.
- **Applies to** — UE 5.8, verified with `TArray<TInstancedStruct<...>>` inside a
  USTRUCT.

### `TWeakObjectPtr` has no `operator bool` (verified 2026-08)

- **Symptom** — `C2280: 'TWeakObjectPtr<...>::operator bool': attempting to
  reference a deleted function`.
- **Cause** — `TWeakObjectPtr` deletes `operator bool`; `if (WeakPtr)` does
  not compile.
- **Fix** — use `.IsValid()` / `.Get()`: `if (WeakPtr.IsValid())`.
- **Note** — `RemCheckVariable` / `RemCheckCondition` take a raw pointer; pass
  `WeakPtr.IsValid()` as the condition, not the weak pointer itself.
- **Verification** — compile; the guarded method runs without dereferencing
  null.

### `TFunction` has no `CreateLambda` (verified 2026-08)

- **Symptom** — `C2039: 'CreateLambda': is not a member of 'TFunction<...>'`.
- **Cause** — `TFunction` is std::function-like and has no static factory.
- **Fix** — construct from a lambda: `TFunction<T(U)> Fn{[](U In) { ... }};`
- **Verification** — compile.

## Test-world driving

### `SetTimerForNextTick` fires on the tick AFTER the registration tick (verified 2026-08)

- **Symptom** — a test asserts after one `FRemTestWorld::Tick` and the latent
  timer's delegate has not run.
- **Cause** — `Rem::Latent::SetTimerForNextTick` schedules for the following
  tick; the registration tick does not fire it.
- **Fix** — tick twice (or loop tick + camera tick) before asserting.
- **Verification** — the latent-timer spec documents the two-tick pattern.

### An Error-severity log during a test fails it (verified 2026-08)

- **Symptom** — a scenario that is functionally correct still reports
  `Result={Fail}`; the log shows `LogAutomationController: Error:` lines for
  Error-severity engine/project logs emitted during the test.
- **Cause** — UE automation treats any Error-severity log output during a test
  as a failure.
- **Fix** — a scenario that inherently logs Error-severity diagnostics (e.g. an
  unresolvable lookup path) cannot be automation-tested; cover the
  surrounding mechanism with adjacent scenarios and state the skip explicitly
  in the commit message. The *authoring* rule it implies — a negative test
  must not trip `RemCheck*`, an `ensure`, or a warning default — lives in
  `tests.md` §4.
- **Verification** — the test passes once the Error-emitting path is excluded;
  the remaining scenarios cover the mechanism.

## Engine behavior

### `ON_SCOPE_EXIT` captures by reference (verified 2026-08)

- **Fact** — the `ON_SCOPE_EXIT` guard's lambda captures local variables by
  reference, so a flag set *after* the guard is declared is visible when the
  guard body runs at scope exit.
- **Use** — gate the exit-time behavior on a local flag: declare
  `bool bRetry = false;` before `ON_SCOPE_EXIT { if (bRetry || ...) ... };`
  and set `bRetry = true;` before an early `return;`.
- **Verification** — the exit body observes the flag (confirmed via log output
  in the retry-path fix).

## UHT — interfaces & base lists

### UHT reads a base list literally and registers interfaces only from it (verified 2026-09)

- **Symptom** — two failure modes. (a) `Error: Found 'MY_BASE_MACRO' when expecting ...` on a base
  list written with a macro. (b) Worse: everything compiles, but `Cast<IMyInterface>(Object)`
  returns null at runtime and `Implements<IMyInterface>()` is false, so a handle built through the
  protocol silently falls back to a default.
- **Cause** — UHT does not preprocess `#include`s, so a macro defined in another header is never
  expanded in a base list (it is fine inside a class body); and UHT records an interface for
  reflection only when the interface appears **as a base itself** — one inherited *through a
  template base* (a CRTP helper) is invisible to reflection.
- **Fix** — write base lists literally (no macros, even for repetitive interface lists), and list
  every interface as its own base next to a CRTP/mixin base instead of relying on inheritance
  through the template. Two independent bases are fine: `class UMy : public IMyInterface,
  public TRemFooBase<UMy>`. A template base on a `UCLASS` is accepted by UHT - it just does not
  register interfaces.
- **Verification** — the UHT error text, and two automation specs that compiled but failed at
  runtime (`Cast` null -> wrong identity) until the interface was listed directly.
- **Applies to** — UE 5.8 (verified 2026-09).

### A USTRUCT's unguarded bases are read as struct parents (verified 2026-09)

- **Symptom** — three distinct UHT errors on one struct:
  `Unable to find parent struct type for 'FX' named 'IY'` (interface base written without a guard);
  `USTRUCTs can only have one USTRUCT base. Wrap any extra bases in a '#if CPP' block.` (a second
  struct base, or a guarded-interface attempt that left another base unguarded);
  `static_assert failed: 'USTRUCT FX cannot be polymorphic unless super FXBase is polymorphic'`
  (a struct adding a virtual through an interface while deriving from a non-polymorphic struct).
- **Cause** — every unguarded base of a `USTRUCT` is treated as a *struct* parent; interface bases
  must be hidden behind `#if CPP`; and a struct that becomes polymorphic needs a polymorphic parent.
- **Fix** — keep at most one unguarded struct base (or none) and wrap every interface base in
  `#if CPP ... #endif`; give a virtual-adding struct a polymorphic base. Related: UHT emits
  `_getUObject()` for **classes only**, so a struct's interface has no `UObject` behind it and
  `Cast<UObject>` of it is null - resolve such interfaces with a compile-time `static_cast` from the
  known concrete type instead (the shape a free-function accessor can provide).
- **Verification** — all three errors in one session, each fixed in turn; the final struct compiled
  and a spec asserted the null `Cast<UObject>`.
- **Applies to** — UE 5.8 (verified 2026-09).

### A derived-to-base conversion in a header-inline hook needs the complete type (verified 2026-09)

- **Symptom** — IDE/build error `Cannot convert UDerived* (pointer to incomplete type) to return
  type UObject*` on a virtual whose body a macro expanded in a header that only forward-declares
  `UDerived`.
- **Cause** — converting `Derived*` to `UObject*` requires `Derived` to be complete; a
  forward-declared type cannot do it.
- **Fix** — declare the override in the header and define it in the `.cpp` (or include the complete
  type there), instead of expanding the body inline.
- **Verification** — three hooks moved to `.cpp` bodies; build green. Note this diagnostic is a
  **true positive**: the same shape was reported clean in a neighbouring header that also lacked the
  complete type, so treat a single clean report as an analysis miss, not as evidence.
- **Applies to** — UE 5.8 / MSVC 19.5x (verified 2026-09).

## C++ — wrapper parameters, overloads, templates

### A CRTP base cannot probe a member of its derived class (verified 2026-09)

- **Symptom** — a member alias (or any nested type) declared by the derived class is never seen: the
  CRTP base silently falls back to its default template argument, so a trait that was supposed to
  pick a narrowed type keeps picking the erased one. Nothing fails to compile.
- **Cause** — the base is instantiated while `TDerived` is still incomplete, so
  `void_t<typename TDerived::Alias>` is SFINAE-rejected at that point and the resulting (primary)
  specialization is *cached*; completeness later does not re-open the question.
- **Fix** — pass the value as a template argument at the base-list site
  (`public TRemFooBase<UMyWorker, UMyWorker>`) instead of probing the derived class, or defer the
  probe to a point where the type is complete (a free function called with an object).
- **Verification** — a compile-time `static_assert` on the returned handle's storage form failed
  although the alias existed; adding the explicit template argument made it pass.
- **Applies to** — any compiler; verified with MSVC 19.50 (2026-09)

### A wrapper type as a parameter changes overload resolution (verified 2026-09)

- **Symptom** — two silent-looking failures after converting *part* of an overload set to a
  typed-pointer wrapper (a `TNotNull<T*>`-style parameter):
  (a) raw-pointer calls keep compiling but bind to a **different** overload - often a broader one
  (e.g. a `const UObject*` entry), which can turn a forwarding body into infinite recursion;
  (b) converting a base/derived overload pair makes every pointer argument ambiguous:
  `error C2668: ambiguous call to overloaded function`.
- **Cause** — a standard pointer conversion outranks a user-defined conversion, so a wrapper
  parameter *loses* to a raw-pointer parameter; and between two wrapper parameters the two
  user-defined conversion sequences are indistinguishable (neither is "the same function").
- **Fix** — treat an overload set as **all-or-nothing**: convert every pointer-taking overload of a
  name, or none. When neither is possible (a never-null overload next to a null-tolerant entry, or a
  base/derived pair), keep that set raw and leave a one-line comment at the declaration saying why,
  so the next reader does not "fix" it. Also: wrapper parameters do not participate in template
  argument deduction - pass a raw pointer, or take a raw local at the top of the body.
- **Verification** — a minimal translation unit compiled with MSVC (raw pointer argument selecting
  the base-typed overload; `C2668` for the pair) plus a module build after the rule was applied.
- **Applies to** — any explicitly-constructible wrapper parameter type; MSVC 19.5x (verified 2026-09).

### An out-of-line member template of a class template can fail to match its declaration (verified 2026-09)

- **Symptom** — `error C2244: unable to match function definition to an existing declaration` for
  `TClass<A>::Member<T>()` defined out of line when the `requires`-clause of the definition names
  the enclosing class template's parameters; the diagnostic shows the declaration as a candidate.
- **Cause** — MSVC does not match the constrained definition's redeclaration pattern against the
  declaration in that shape.
- **Fix** — move the constraint's checks into the body as `static_assert`s (or define the member
  inline in the class). Document why, so a later cleanup does not move it back.
- **Verification** — a type-erasure converting constructor that failed to match out of line and
  compiled once the checks moved into the body.
- **Applies to** — MSVC 19.5x, C++20 (verified 2026-09).
