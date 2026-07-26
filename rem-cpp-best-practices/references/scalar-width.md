# Scalar Width — float vs double

Which scalar width a numeric member or config value should declare. The rules
of thumb live in `SKILL.md` §12; this file holds the reasoning, the precision
tables and the engine citations. `ForceUnits` metadata is owned by `SKILL.md`
§10.

Header paths below are relative to `Engine/Source/Runtime/`.
Last verified: 2026-09, engine 5.8 — `Core/Public/Math/MathFwd.h`,
`Core/Public/Misc/LargeWorldCoordinates.h`, `Core/Public/Math/Vector.h`,
`Core/Private/Math/DoubleFloat.cpp`, `Core/Private/Misc/ConfigCacheIni.cpp`,
`Engine/Classes/Engine/NetSerialization.h`,
`Engine/Classes/Engine/ReplicatedState.h`.

---

## 1. `double` is the default; the `f` variant is the deliberate deviation

The engine's LWC macro hard-codes `double` as the component type of every
default math type, and the adjacent `LWC_TODO` comment ("Remove
COMPONENT_TYPE") marks that as a permanent decision rather than a transition —
`Core/Public/Misc/LargeWorldCoordinates.h`:

```cpp
#define UE_DECLARE_LWC_TYPE_3(TYPE, DIM, UE_TYPENAME) \
    UE_DECLARE_LWC_TYPE_EX(TYPE, DIM, UE_TYPENAME, double)
```

`Core/Public/Math/MathFwd.h` aliases both families, so both are available as
member types — the only question is which one a given member declares:

| Concept | Default | Narrow | Explicit wide |
|---|---|---|---|
| Vector (3) | `FVector` | `FVector3f` | `FVector3d` |
| Vector (2) | `FVector2D` | `FVector2f` | `FVector2d` |
| Vector (4) | `FVector4` | `FVector4f` | `FVector4d` |
| Rotator | `FRotator` | `FRotator3f` | `FRotator3d` |
| Quat | `FQuat` | `FQuat4f` | `FQuat4d` |
| Matrix | `FMatrix` | `FMatrix44f` | `FMatrix44d` |
| Transform | `FTransform` | `FTransform3f` | `FTransform3d` |
| Box / Box2D | `FBox` / `FBox2D` | `FBox3f` / `FBox2f` | `FBox3d` / `FBox2d` |
| Sphere / Plane / Ray | `FSphere` / `FPlane` / `FRay` | `FSphere3f` / `FPlane4f` / `FRay3f` | `...3d` / `...4d` / `...3d` |

The `d` column is the explicit spelling of the same type as the default alias;
use it only when a pairing must be visible in the code. The 2D default alias is
`FVector2D`, not `FVector2` — that header's alias list is not perfectly regular,
so read it rather than assuming a pattern.

---

## 2. What `float` costs: precision, not range

`float` has a 24-bit significand (~7 significant decimal digits), `double` a
53-bit one (~16). `float`'s range (±3.4e38) is never the binding constraint in a
world measured in centimetres — the cost is **absolute** resolution, and it
degrades linearly with distance from the origin:

| Distance from origin | Meaning | `float` step | `double` step |
|---|---|---|---|
| 1e3 | 10 m | 6.1e-5 | ~1e-13 |
| 1e5 | 1 km | 7.8e-3 | ~1e-11 |
| 1e6 | 10 km | 0.0625 | ~1e-10 |
| 1e7 | 100 km | 1.0 | ~1e-9 |

Values are engine units (cm); a step of 1.0 at 100 km is one centimetre of
ambiguity per stored coordinate. The `float` column follows from a 24-bit
significand (step `2^(e-23)` for a value in `[2^e, 2^(e+1))`), the `double`
column from a 53-bit one (`2^(e-52)`).

**The engine's own precision bar is 0.25 units.**
`Core/Private/Math/DoubleFloat.cpp` defines:

```cpp
constexpr float UE_DF_MIN_PRECISION = 1.0f/(1 << 2);
// Max value of a float before it's precision is lower than UE_DF_MIN_PRECISION
// (there may be 1 more implicit bit available in the significant, but this works as a safe upper bound)
constexpr float UE_DF_FLOAT_MAX_VALUE = ((float)(1 << 23) * UE_DF_MIN_PRECISION - 1.0f);
```

That is 0.25 units of resolution and a bound of 2,097,151 units (≈21 km).
`CheckMatrixPrecision` (non-shipping) `ensureMsgf`s against exceeding the
magnitude when a matrix is converted to GPU format, and the same bound clamps
`MakeClampedToRelativeWorldMatrix*`. So the engine accepts `float` for a
*relative* transform down to 0.25 units of resolution, up to roughly 2.1e6
units from its reference point — a calibration point for "how much precision is
actually needed", not a licence to store world state narrow. The header's own
framing is narrower still: `FDFScalar` is "usable where doubles (fp64) are not
an option".

Replication carries a comparably explicit bar: `FVector_NetQuantize100`
serializes 2 decimal places over ±10,737,418.24 with 30 bits per component
(`Engine/Classes/Engine/NetSerialization.h`) — 0.01 units of precision, which
is 100× finer than `float` resolves at 100 km, in a payload no wider than a
`float` per component. Quantization beats narrowing.

**Per-component widths are an accepted engine pattern.** The engine does not
treat a structure's components as one decision —
`Core/Public/Math/MathFwd.h` notes that `FCompactBoxSphereBounds` "always
stores float extents" while its origin stays `double`:

```cpp
using FCompactBoxSphereBounds3d = UE::Math::TBoxSphereBounds<double, float>;
```

---

## 3. The decision rule

One question: **does this value describe a place in the world, or a property of
a thing?**

| Value | Width | Why |
|---|---|---|
| World position; a world-space offset consumed as a position | `double` | error grows with distance; the value is added to other world-space `double`s |
| State the world-space graph integrates or sums per frame — `Velocity`, `Acceleration`, force accumulators — that engine APIs around it take as `FVector` | `double` | not a precision question: it feeds the position integration, so error compounds into `Location` |
| Bounded rate or distance that stays **outside** that graph — a speed, rate or length only your own math scales with | `float` is legitimate | `float` resolves ~2e-4 cm/s at 3000 cm/s — see the three tests below |
| Tuning parameter — max speed, max acceleration, gravity scale, radius, distance, duration | `float` | bounded by design and applied to state, not accumulated into it |
| Angle, angular rate | `float` | a full turn is inherently bounded; `float` still resolves ~3e-5 of a degree at 360 |
| Scale, ratio, alpha, weight, probability, normalized direction | `float` | dimensionless and bounded by construction |
| Bulk array of positions | `float` only as a re-based local array | see §7 |
| Count, index, flag | integer type | not a width question |

Three consequences the table does not spell out:

- **Never store an authoritative world position in an `f` type — nor anything
  that will be added to one.** Precision is lost at write time and widening at
  the consumer cannot recover it. The rule has no exception: §7's remedy is not
  one, because re-basing *removes* the world position (what remains is a local
  offset, which this table already permits) rather than storing it narrow.
- **Narrow the parameter, never the state.** This is the pattern the engine's
  own movement components follow, and it is the shape a config-data decision
  should copy:

  | Role | Engine members | Width |
  |---|---|---|
  | Tuning parameter | `MaxWalkSpeed`, `MaxAcceleration`, `JumpZVelocity`, `InitialSpeed`, `MaxSpeed`, `ProjectileGravityScale` | `float` |
  | Runtime state | `GravityDirection`, `Acceleration`, `LastUpdateLocation`, `LastUpdateVelocity`, `PendingForce`, `InterpLocationOffset` | `FVector` (`double`) |

  (`Engine/Classes/GameFramework/CharacterMovementComponent.h`,
  `Engine/Classes/GameFramework/ProjectileMovementComponent.h`.)
- **An offset is a `float` candidate only under three conditions**: its
  magnitude is bounded by design, it is the only expression of that quantity
  (nothing accumulates into it), and it is applied to a `double` world value
  rather than compared against one. `InterpLocationOffset` above is the
  counterexample the engine kept wide.
- **"Does `float` hold this value?" is never the deciding question.** A speed of
  3000 cm/s resolves to ~2e-4 cm/s in `float`, and the engine's own bar is 0.25
  units (§2), so a bounded quantity is numerically fine in `float` whatever its
  units. Three tests decide instead: **(a)** is it added to or compared against
  world coordinates, **(b)** is it summed across frames, **(c)** do the APIs
  consuming it take `FVector`? All three "no" → `float` is legitimate. The
  engine's movement state answers "yes" to (a) and (c) — its `Velocity` is
  integrated into `Location` every frame — which is why it stays `double` while
  `MaxWalkSpeed` beside it is `float`.

---

## 4. Conversions and API friction

Cross-width construction is `explicit`, and there are no mixed-width
vector–vector operators (scalar operands accept any arithmetic type)
(`Core/Public/Math/Vector.h`):

```cpp
template<typename FArg UE_REQUIRES(!std::is_same_v<T, FArg>)>
explicit TVector(const TVector<FArg>& From) : TVector<T>((T)From.X, (T)From.Y, (T)From.Z) {}
```

So `FVector World = Member;` does not compile when `Member` is an `FVector3f` —
write `FVector(Member)`, and convert one side explicitly in every mixed
expression. The conversion itself is a single instruction; the cost of choosing
`f` is **code noise and review surface, not CPU**.

**Name the width at the conversion site.** The project ships a macro family for
this — `RemFloatDoubleConversionMacros.h` (`RemCommon`, `Public/Macro/`):

```cpp
const auto Vector  = REM_VECTOR3_DOUBLE(1, 2, 3);    // FVector3d{ ... }
const auto Rotator = REM_ROTATOR_DOUBLE(0, 90, 0);   // FRotator3d{ ... }
const auto Narrow  = REM_VECTOR3_FLOAT(Member);      // FVector3f{ Member }
```

They are construction shorthands, not an automatic converter: the argument list
is handed to the named type's constructor, so a cross-width argument converts
through the `explicit` constructor above, and the resulting width is stated at
the call site and greppable (`REM_VECTOR3_FLOAT` vs `..._DOUBLE`). Prefer them to
an ad-hoc `static_cast` chain when a value crosses the families at runtime —
they are the project's answer to "which width did this conversion pick?", which
is otherwise invisible in review.

The engine treats narrowing as an event worth grepping —
`Core/Public/Misc/LargeWorldCoordinates.h` provides
`UE_REAL_TO_FLOAT(argument)`, documented as "use to make any narrowing casts
searchable in code when it is updated to work with a 64 bit count/range".

**Convert once, at the boundary** that turns config data into runtime state.
A conversion at load is free; a conversion inside a per-tick loop repeats a
precision decision in code that no longer shows it. Narrowing each operand to
keep a `float` pipeline buys nothing here — evaluate in the natural width and
convert once.

Migration between widths is supported in **both** directions at the type level,
and one-way only for the data:

| Path | Mechanism |
|---|---|
| Asset/link tag change, either direction | `TVector<T>::SerializeFromMismatchedTag` switches between the `Vector3f` and `Vector3d` variants (`Core/Public/Math/Vector.h`) |
| Pre-LWC package load, `float` → `double` only | `operator<<(FArchive&, TVector<double>&)` reads 3 `float`s when `UEVer() < EUnrealEngineObjectUE5Version::LARGE_WORLD_COORDINATES`; that branch carries `checkf(Ar.IsLoading(), TEXT("float -> double conversion applied outside of load!"))` |

Neither direction restores digits a `float` never stored: **changing the type
later recovers the API, not the data.**

---

## 5. Size: three media, three answers

| Medium | `float` | `double` | Does narrowing pay? |
|---|---|---|---|
| In memory | 4 B/scalar; `FVector3f` 12 B, `FQuat4f` 16 B, `FTransform3f` 40 B | 8 B/scalar; `FVector` 24 B, `FQuat` 32 B, `FTransform` 80 B | Yes — exactly 2× |
| Package (`.uasset`, `.pak`) | 3×4 B per vector | 3×8 B per vector since `EUnrealEngineObjectUE5Version::LARGE_WORLD_COORDINATES` (`Core/Public/Math/Vector.h`) | Partly — 2× before compression; scattered fields typically lose most of it to the compressor, large arrays keep it |
| Property text (editor copy/paste, `ExportText`, property-serialized config lines) | same length | same length | **No** |
| Config lines written through `GConfig` / `FConfigFile::SetFloat`/`SetDouble` | 9 significant digits | 17 significant digits | Marginally — and the `float` prints as its exact binary value |

The two text rows differ because there are two writers:

- The property text exporter formats both widths with the same specifier —
  `Expose_TFormatSpecifier(float, "%f")` and
  `Expose_TFormatSpecifier(double, "%f")`
  (`Core/Public/Templates/UnrealTypeTraits.h`), reached through
  `LexToString` → `FString::SanitizeFloat`, which is
  `Printf("%f", InFloat)` plus trailing-zero trimming
  (`Core/Private/Containers/String.cpp.inl`). Six fractional digits at most,
  identical for both widths, so the same value occupies the same characters
  either way. Structured exports pad rather than trim, which is why an
  editor-generated settings file shows `(X=4.000000,Y=1.000000,Z=1.000000)`.
- `FConfigFile::SetFloat` / `SetDouble` use `%.*g` with
  `std::numeric_limits<T>::max_digits10` (`Core/Private/Misc/ConfigCacheIni.cpp`),
  which is 9 vs 17 significant digits. A `float` written this way round-trips
  exactly but reads as `0.200000003`; the `double` reads as `0.2`.

Either way, text is not the medium for exact world coordinates and the byte
difference is not a reason to pick a width. → The size argument for `f` types
holds only for **binary storage of large arrays**.

---

## 6. Performance: where the cost actually is

| Cost | Effect of choosing `float` | When it matters |
|---|---|---|
| ALU / SIMD throughput | up to 2× more lanes (8 vs 4 per AVX2 register) | SIMD-heavy math; config-driven code is rarely this |
| Memory bandwidth / cache | 2× elements per cache line | the real source of the bulk-array win |
| Widening conversion | one instruction per value | negligible, even per frame |
| Type friction | an explicit conversion in every mixed-width expression | the dominant day-to-day cost of choosing `f` |

---

## 7. Bulk arrays and the boundary pattern

The 2× gain is only worth designing for on large arrays (a few thousand
elements and up), and even there it is rarely the first thing to try. Before
narrowing an array of world positions, check whether it can live in **local
space with one `double` origin per array or chunk** — that keeps world
precision and still stores narrow.

That is the pattern the engine uses wherever width must be traded against
precision:

| Need | Engine's answer |
|---|---|
| Compact bounds | `double` origin + `float` extents (`FCompactBoxSphereBounds3d`) |
| GPU transforms | `FDFMatrix` = `FMatrix44f` + `FVector3f PostTranslation`; `FDFInverseMatrix` = `FMatrix44f` + `FVector3f PreTranslation` (`Core/Public/Math/DoubleFloat.h`) |
| More precision than `float` where `double` is unavailable (shader) | two `float`s, not a wider type: `FDFScalar` / `FDFVector3` ("usable where doubles (fp64) are not an option") |
| Compressing replicated world positions | keep `FVector` in memory (`Engine/Classes/Engine/ReplicatedState.h`: `FRepMovement`, `FRigidBodyState`), quantize in the serializer: `FVector_NetQuantize100` → `SerializePackedVector<100, 30>` (`Engine/Classes/Engine/NetSerialization.h`) |

**The engine's pattern is "keep the widest type in memory and state; narrow or
quantize at the boundary."** Copy the pattern rather than narrowing the stored
member. Even the transport layer moved toward the wide type and made
compression explicit instead: raw `FVector` network serialization writes
doubles only from `FEngineNetworkCustomVersion::SerializeDoubleVectorsAsDoubles`
onward, and was `float` before (`Core/Public/Math/Vector.h`).
