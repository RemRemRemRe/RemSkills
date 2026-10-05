# Design & Zero-Overhead

Detail moved out of `SKILL.md` so the rules stay scannable.

### Single Responsibility

Each class/struct does one thing. Each function does one thing. If a struct
has `UPROPERTY` data and logic, the logic is in a separate non-reflected base
or a free function in `Rem::`.

### Respect levels of abstraction

A function body reads at **one level of abstraction**: high-level statements
(intent, domain operations) at the top, low-level mechanics (index loops, byte
fiddling, string formatting) extracted into helpers — never interleaved. A loop
that mixes "add the item to the inventory" with "advance the cursor / wrap the
index" obscures both. See [Respect levels of
abstraction](https://www.fluentcpp.com/2016/12/15/respect-levels-of-abstraction/)
(Fluent C++).

- The function name sets the level; the body must not dip below it. When body
  details belong to a lower level, extract them into a helper or a `Rem::` free
  function.
- Mixed-level bodies are the first symptom of a function doing two things —
  level mixing makes the Single Responsibility rule unverifiable.

### Interface Segregation / Dependency Inversion

- Define abstract interfaces via `UINTERFACE(MinimalAPI)` + `I*` class
- Or via C++20 concepts (preferred for compile-time dispatch)
- Free functions in `Rem::` namespaces over member functions where possible

### Liskov substitution — clone-like interfaces

A clone/factory-by-virtual interface must stay substitutable: a derived override keeps the base's
ownership and copy semantics (`TUniquePtr<Base>` by default), its `noexcept` contract, and every
caller holding the base stays correct with the derived result. Covariant returns are fine;
ownership changes, stronger preconditions and weaker postconditions are not. If a derived type
cannot honour the contract — non-copyable state, a narrower result — do not derive it from that
interface; split the interface. The clone copies everything the base contract promises, not a
shallow or partial subset.

### Declaring a worker's identity and liveness (pattern, verified 2026-09)

When several interfaces each need to answer "which object bounds my lifetime, and am I still
usable?", do not give every interface its own accessor. Put **one primitive with a uniform
signature** behind a dedicated protocol and expose **typed accessors** on top:

- one virtual, e.g. `virtual UObject* GetOwner() const = 0;` - uniform, so a class implementing
  several of those interfaces implements it **once**, and no two interfaces collide on it (the
  same name with a *different* return type cannot be implemented by one class at all);
- a typed accessor per interface type that returns a handle carrying the identity plus the pointer
  (`{liveness, pointee}`), resolved with a **compile-time** `static_cast` from the concrete type -
  never `Cast<UObject>`, which is null for USTRUCT implementers (UHT emits `_getUObject()` for
  classes only) and can fail at runtime for classes;
- for a `UCLASS` the accessor can come from a CRTP mixin base; a `USTRUCT` cannot list a template
  base (UHT reads unguarded bases as struct parents), so it uses a free-function form over the same
  implementation.

Ask first whether a protocol is needed at all: when the identity is already known at the **creation
site** (the caller passes the owning object), the concrete handle can simply be built there, and the
interfaces need no addition at all. Add the protocol only when a worker's identity must differ from
what the creation call knows.

**Handle storage.** When liveness and pointee are the same object (static inheritance), the compact
form stores only the weak liveness and derives the pointee with a compile-time `static_cast` — the
same address UHT computes via `VTABLE_OFFSET` — so never store an integer offset. A `TSharedPtr`
liveness is a **strong** reference (it keeps the payload alive); `TWeakPtr` is weak but exposes only
`Pin()`/`IsValid()` — no payload accessor. And a runtime weak handle is **not** a serialized
reference: anything that must survive serialization/editor reload/rename stays `TSoftObjectPtr`.

### Holding a callback a module registers (pattern, verified 2026-09)

When a family needs a callback some other module registers at startup (a capability it contributes),
hold it in a small type with **one signature template parameter** instead of a pair of types:

- `template <typename TSignature> class TCallbackHolder` with `using FFunction = TFunction<TSignature>`,
  a `Set` (an empty function clears it), a `TryProvide(Args...)` that default-constructs its result
  when nothing is registered, and an `IsRegistered`;
- the signature parameter is what keeps it flexible: `Result(Arg)` today, `void()` or `Result(A, B, C)`
  tomorrow, with no change to the type and no "single argument only" limit - and no word like "handle"
  in the name, because the signature already says what the type produces;
- define the forwarding member in the class body: an out-of-line definition whose return type spells
  the enclosing template's parameter fails to match under MSVC (see `references/pitfalls.md`).

A generic mechanism also treats its **request** as opaque: a value, a struct or a non-copyable type
all work — pass it by `const&` end to end. The mechanism stores, compares and converts nothing and
assumes no shape (not even pointer-ness); the request's meaning stays with the family that owns it.

### Zero-Overhead

| Principle | Guideline |
|-----------|-----------|
| No virtual unless polymorphic dispatch is required | `virtual` has vtable cost |
| `if constexpr` > runtime polymorphism | Compile-time branch is zero-cost |
| Templates pay only for instantiations | No runtime dispatch overhead |
| `constexpr` compute at compile time | Zero runtime cost |
| Pass trivial types by value | `int32`, `float`, `FVector` |
| Pass non-trivial types by `const&` | `FString`, `TArray` |
| Move from rvalues | `void SetName(FString Name) { Name = MoveTemp(Name); }` |
| Non-null member storage | `TNonNullPtr<T>` — `TOptional<TNotNull<T*>>` is not intrusive (16 B); never a sentinel address. `TNotNull` belongs at the API boundary (params, checked getters) |

### Move semantics

```cpp
// Sink parameter pattern:
void SetName(FString Name)
{
    Name_ = MoveTemp(Name);
}

// Move out of return:
TArray<FItem> Items = GetItems();   // RVO or move, no copy

// Move in generic code:
template <typename T>
void Store(T&& Value)
{
    Data = std::forward<T>(Value);   // perfect-forwarding
}
```

### Elegance — objective proxies

"Elegant" is not reviewable as stated, so it is checked through proxies a
reviewer can point at. A review may raise **at most three** elegance findings
per change, each naming the concrete alternative — anything beyond that is
taste, not a defect, and must not be reported.

| Proxy | The finding looks like |
|---|---|
| Minimal surface | An exported/public member no caller uses; a `public` that could be `private`; a non-`const` method that never mutates |
| Names reveal intent | A name that describes the mechanism instead of the concept (`ProcessData` for what is really "apply damage") |
| No hidden side effects | A getter that mutates; a constructor that touches the world; a query that allocates unbounded |
| No dead weight | Dead code, commented-out code, unused parameters, unreferenced helpers, `#if 0` blocks |
| No premature abstraction | A base class / interface / template with exactly one implementation and no planned second; a parameter that only ever takes one value |
| Symmetry and consistency | Sibling methods with different shapes; one path throwing and another returning a sentinel; a new helper duplicating one that already exists (survey `RemCommon` first — §3) |
| One reason to change | A header including unrelated subsystems; a function whose name needs "And" |

Deletion is the preferred fix: a proxy that fails because the code is
unnecessary is resolved by removing it, not by adding a layer.
