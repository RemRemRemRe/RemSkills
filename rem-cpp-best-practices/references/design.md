# Design & Zero-Overhead

Detail moved out of `SKILL.md` so the rules stay scannable.

### Single Responsibility

Each class/struct does one thing. Each function does one thing. If a struct
has `UPROPERTY` data and logic, the logic is in a separate non-reflected base
or a free function in `Rem::`.

### Minimal stored state — re-derive instead of caching

A data member costs four things: a lifetime to keep correct, an invalidation path at every writer, a
validity question at every read, and a line in every constructor and copy. Before adding one, ask
whether it can be read at the point of use from the object that owns it.

- **Do not cache another object's state.** A sibling component, a subsystem, a controller's pawn, the
  player state behind an ability system, a configuration object: the owner can be rebuilt, replaced or
  destroyed between two calls, so the cache is stale exactly where it matters. Reading at use costs one
  getter; keeping the cache correct costs an update path at every write site, most of which nobody
  remembers.
- **A cache is justified by one of three facts, and the fact is stated on the member:** the read is
  measurably expensive relative to its frequency; the value must be read *after* its source is gone (a
  registered handle together with the key it has to be unregistered with); or it is the result of work
  that cannot be repeated (a computed id). "Might be a bit faster" is not one of them — measure first,
  and a container lookup or a getter almost never shows up.
- **Scope the cache to the operation, not to the object.** A value one call needs is a local; a value
  one frame needs is a member cleared at the end of that frame. A member that outlives its use turns
  into `if (Cached.IsValid())` spread over the whole type — state that exists to answer a question
  nobody asked.

```cpp
// Declared elsewhere, so the example is self-contained:
// UBar* ResolveBar();

// AVOID — the first answer is frozen, and every writer has to invalidate it.
class FFoo
{
public:
    void Initialize()
    {
        Cached = ResolveBar();       // stale after any rebuild or respawn
    }

    void Act() const
    {
        if (auto* Bar = Cached.Get())
        {
            Bar->Do();
        }
    }

private:
    TWeakObjectPtr<UBar> Cached{};
};

// PREFER — resolved where it is used: no lifetime, no writer, no validity question.
class FFoo
{
public:
    void Act() const
    {
        if (auto* Bar = ResolveBar())
        {
            Bar->Do();
        }
    }
};
```

The legitimate cache, from the same family: a delegate handle **and** the key it was registered with.
The key must be passed back to unregister, the configuration it came from may have changed in between,
and there is no other source for it — so the pair is stored, with the reason written on the member.

### One transition per name — `Bind` does not call `Unbind`

A function name is a postcondition. `Bind` promises "the bindings this call makes exist"; a `Bind` whose
first line is `Unbind()` also promises "whatever was there is gone", which is a second job performed
invisibly:

```cpp
// AVOID — hidden teardown: the name no longer says whether anything was released.
void Bind()
{
    Unbind();
    RegisterFirst();
    RegisterSecond();
}

// PREFER — the replacement is one visible, ordered statement at the transition point.
Unbind();
Bind();
```

What the hidden version costs:

- **The call site cannot be read.** Setup and replacement look identical, so a reviewer cannot see the
  release and the person chasing a leaked handle cannot find it.
- **The functions stop being independently testable.** "Does `Bind` allocate?" now depends on prior
  state, and a test that binds twice tests something different from one that binds once.
- **The failure modes merge.** A half-failed previous bind, a guard that skipped the release, or a
  nested call becomes a double registration or a leak that only the combined entry point can contain —
  and it cannot, because it does not know which of the two cases it is in.
- **The teardown is forced on callers that never needed it,** for example an initialize path that has
  nothing bound yet.

When replacement is genuinely one domain operation, name the operation: `Rebind()` whose whole body is
`Unbind();` then `Bind();`. When the requirement is instead idempotency — initialize and resume both
call it — guard on the state (`if (bBound) { return; }`) rather than tearing down and rebuilding.

Exception: an owner whose semantics *are* "regenerate from scratch on every call" (a cache that
recomputes per generation) keeps the teardown inside, under a name that says so — `Rebuild()` — and
still as the first statement rather than buried in a helper.

**A rebind that can happen writes both lines; an operation that happens once does not.** The distinction
is the object's lifetime, not caution: if the unit can be announced twice, `Unbind(); Bind();` sits at
that transition; if the announcement is once per team and the release belongs to teardown, `Bind`
appears alone and only `Uninitialize` releases. Adding the leading `Unbind` "just in case" is the
defensive shape `Write for the guaranteed order` rejects.

### Take the narrowest type the body uses

A parameter typed for the caller's most specific class narrows every future caller and forces a cast
where a base type already works. Ask what the body actually touches: a helper that only calls
`GetName()` needs `UObject`, not `APawn`; one that only reads a transform needs `AActor`. Choosing the
base costs nothing when the use is genuine; choosing the derived one costs a second overload the day
another type needs it.

Containers are the exception that proves the rule: a view does not widen. `TConstArrayView<APawn*>` is
not a `TConstArrayView<AActor*>`, and a template parameter cannot be deduced from a `TArray<APawn*>`
argument into `TConstArrayView<TObject*>` — the conversion is not a deduction context. The compatibility
trait says exactly this: `TIsCompatibleElementType_V = std::is_convertible_v<T**, ElementType* const*>`
(`Core/Public/Containers/ArrayView.h`), which permits adding `const` to the same pointee type, not
changing the pointee's class. `MakeConstArrayView`/`MakeConstArrayView64` are factories that deduce
the element from the pointer, so a wrapper changes the size type and nothing else. A general helper
therefore deduces the range and constrains its element:

```cpp
template <typename TRange>
    requires (CUObject<std::remove_pointer_t<TElementType_T<TRange>>>)
[[nodiscard]] FUtf8String JoinObjectNames(const TRange& Objects);
```

### Preconditions sit at the top of the function

A null check on an object the function cannot work without is a **precondition**, not a branch: it
belongs in the first lines, before the body has locals. The shape `if (A) { if (B) { work } }` is two
unnamed preconditions — the body above it already ran with values it could not use, and the reader
holds two states at once. Prefer, in this order:

1. a `TNotNull` parameter, when the caller already knows the value is there;
2. a top-of-function guard (`if (!Object) { return; }`) when the absence is a reachable runtime state;
3. a `RemEnsure*`/`RemCheck*` with a bail-out, when the absence is a bug rather than a state.

Absence that is *legal* stays a branch where it is decided — a leader that may not exist yet, a
container that may be empty — but it is decided once, near the top, not re-checked by every helper the
value passes through.

### Write for the guaranteed order

A later stage that re-does an earlier stage's work "just in case" does not make the system safer: it hides
the broken caller, doubles the paths that can register, bind or initialise the same thing, and every
reader has to work out which ordering is real. If the announcement is guaranteed to precede the tags, the
tag handler needs no fallback bind.

- **Assume the order the design states.** A caller that violated it is a defect; the code that would
  survive the violation is dead weight in every normal run.
- **Assert the invariant instead of defending it.** `RemCheckCondition(!bBound, return;)` in `BindUnits`
  names the rule (one bind, at the announcement); a lazy "bind if not bound yet" inside the reform hides
  the same rule and makes a second announce silently legal.
- **What is not the same thing:** a value that can genuinely be absent at runtime (a dying ability system
  behind a weak pointer, a null entry a Blueprint wrote into a `UPROPERTY` array) is data, not ordering.
  That check stays — it is the input's shape, not another layer's promise.
- **What is also not the same thing:** a state machine's own re-entrancy (a follow coroutine answering a
  tag change while the reform that started it runs). That guard stays and is named for what it is.

The test: delete the fallback and name the caller that would break. If the answer is "none, the order is
fixed", it was defence against a hypothetical; if it is "the Blueprint that can write this array", it is
input validation and belongs.

The guarantee may still be a promise a layer above keeps rather than a fact in this tree — assert it
anyway. A branch added because the guarantee is not enforced yet is the branch that outlives the
guarantee; `RemCheck*` (development-only, stripped in Shipping) is the shape for it.

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

**A function is named for the value it produces, not for the member it writes.** `ComputePartyCurrent`
named the field the result was stored in; the value was the chain, so `ComputePartyChain`. A name that
repeats a member name also reads as "recompute this field", which is the implementation, not the
intent.

Deletion is the preferred fix: a proxy that fails because the code is
unnecessary is resolved by removing it, not by adding a layer.

**A member function that touches no member is a `static` function.** Being non-static claims a coupling
the body does not have: a reader assumes it reads or writes the object's state, a test writer hunts for
the state to set up, and the class looks bigger than it is. The same applies to a helper that only needs
its parameters — make it `static` (or a free function in `Rem::` when it needs no class at all). The
IDE's *member can be made static* hint does **not** arrive through the MCP diagnostics interface
(measured 2026-11: `get_file_problems` and `lint_files` both return nothing for a file the IDE flags),
so this one is checked by hand or by `rem-cpp-best-practices/tools/check_static_members.py --path <dir>`.

### Choosing where an extension lives

An extension point should not tax the code that never uses it: "flexible" is a cost every reader and
every asset pays, including the ones that never need the variation. Decide by asking where the
variation actually lives, not which mechanism is most general.

- **The behaviour differs** → a subclass with a virtual hook: the base keeps the flow and the default,
  the variant carries its own data, and nothing exists on the base that only one variant uses. A field
  that is always present but meaningful for one case ("empty by default") is still a field, a branch
  and a serialized slot - the smell this ordering exists to remove.
- **Only a value differs** → an enum or a plain field. A duration, a radius or a mode is data; one
  subclass per value multiplies types without changing structure.
- **The variant must be picked from an asset and brings its own payload** → a type-erased payload such
  as an instanced struct. It is the most expensive of the three to read and debug: take it last, and
  only when the choice truly lives in data.
- **A flag that switches behaviour** → usually wrong. Two paths that share almost nothing are two
  types; two paths that share everything are one type, and the flag is data.

### Flat execution blocks — avoid rocket code

> This rule exists because AI-generated code frequently produces deeply nested `if` chains (the
> "rocket" anti-pattern) that obscure the main logic.

`std::invoke([&]{ ... })` creates a scoped execution block in which `RemEnsure*`/`RemCheck*` with
`return` bail out cleanly, so the main logic stays at one indentation level.

```cpp
// Rocket code (AVOID):
if (auto* A = GetA())
{
    if (auto* B = A->GetB())
    {
        if (auto* C = B->GetC())
        {
            // actual logic  —  4 levels deep
        }
    }
}

// Flat block (PREFER):
std::invoke([&]
{
    auto* A = GetA();
    RemCheckVariable(A, return;);
    auto* B = A->GetB();
    RemCheckVariable(B, return;);
    auto* C = B->GetC();
    RemCheckVariable(C, return;);
    // actual logic  —  flat, no nesting
});
```

`std::invoke` immediately executes the lambda. `return` inside the lambda exits the lambda, not the
enclosing function — use it to bail out on failed preconditions. Capture `[&]` for full access to the
enclosing scope.
