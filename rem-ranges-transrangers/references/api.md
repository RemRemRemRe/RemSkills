# API Reference

Detail moved out of `SKILL.md` so the rules stay scannable.

### `Rem::Ranges` — Consume a ranger (get data out)

| Function | Returns | Description |
|---|---|---|
| `ForEach(Ranger)` | `void` | Fires the pipeline but always exhausts the range. Use when side-effects are the goal. **No early exit** — consumption function always returns cursor deref value, not a stop signal. |
| `ToArray(Ranger)` | `TArray<ValueType>` | Materializes the ranger into a TArray. **Requires `ranger_element_t` to be a non-reference type** — use the two-arg overload `ToArray(OutArray, Ranger)` for rangers whose elements are references (e.g. after `ranger_join`). |
| `ToArray(OutArray, Ranger)` | `void` | Materializes into an existing TArray. |
| `TakeN<Count>(Ranger)` | `TArray<ValueType>` | Takes exactly `Count` elements, returns as TArray. Supports early exit via `take<Count>`. |
| `FirstElement(Ranger)` | `ValueType` | Returns the first element (calls `NthElement<0>`). **Supports early exit** — uses `take<1>` internally, so pipeline stops at first match. Returns a default-constructed value if no elements exist (e.g., `nullptr` for pointers). |
| `NthElement<N>(Ranger)` | `ValueType` | Returns the Nth element (0-indexed). **Supports early exit** via `take<N+1>`. |
| `ArrayView(TArray)` | ranger | Wraps a TArray as a ranger (non-const). |
| `ConstArrayView(TArray)` | ranger | Wraps a TArray as a ranger (const-safe). Prefer this for read-only pipelines. |

### `transrangers` — Build a ranger (lazy pipeline)

| Function | Returns | Description |
|---|---|---|
| `all(range)` | ranger | Entry point: creates a ranger from any range with `begin()`/`end()`. lvalue version captures by reference; rvalue version owns data via `all_copy`. |
| `filter(pred, ranger)` | ranger | Lazy filter. Predicate: `bool(const Element&)`. |
| `transform(fn, ranger)` | ranger | Lazy map. `fn: Element → NewType`. Note: function comes **first**, ranger comes **second**. |
| `concat(r1, r2, ...)` | ranger | Concatenates 2+ rangers end-to-end. |
| `take(N, ranger)` | ranger | Takes at most N elements. |
| `take<N>(ranger)` | ranger | Takes at most N elements (compile-time count). |
| `ranger_join(ranger)` | ranger | Flattens a ranger-of-ranges into a flat ranger via `all_adaption`. Use when each element is itself a range (TArray, etc.). |
| `zip(r1, r2, ...)` | ranger | Pairs elements into `std::tuple<...>`. |

### `RemStd::bind_back` — Partial Application

```cpp
template <typename F, typename... BoundArgs>
constexpr auto bind_back(F&& f, BoundArgs&&... args);
```

Binds arguments to the **back** of the parameter list. Returns a callable where:
- `call(call_args...)` invokes `f(call_args..., bound_args...)`

**Critical rule**: the element parameter (the one `transrangers::transform` passes) **must be the first parameter** of the function. Bound context parameters go after:

```cpp
// CORRECT: element first, context params after
bool Match(int32 Context, TInstancedStruct<FFoo>& Arg);
//        ^-- WRONG: Context would be passed as the element by transform
// Fix: reorder params
bool Match(TInstancedStruct<FFoo>& Arg, int32 Context);
auto Matcher = RemStd::bind_back(Match, Context);  // Matcher(Arg) calls Match(Arg, Context)
```

`TInstancedStruct` is from UE StructUtils (see `StructUtils/InstancedStruct.h`).

**Use case**: when a mapper function takes extra context parameters beyond the element:

```cpp
FBar Transform(const UFoo*, int32 Context);
// bind_back creates a unary function for transrangers::transform:
auto Mapper = RemStd::bind_back(Transform, Context);
// Mapper(Section) calls Transform(Section, Context)
```
