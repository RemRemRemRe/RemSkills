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
