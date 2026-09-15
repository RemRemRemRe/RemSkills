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
