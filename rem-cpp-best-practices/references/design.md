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
