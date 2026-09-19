# DLL Boundaries: Exporting a Class Template's Instantiation

How a class template's **instantiation** crosses a module (DLL / shared-library)
boundary in a UE-style UBT build. The class template itself stays in the shared
header; what is exported is one concrete specialization, and every consumer is
told not to emit its own copy.

Verified 2026-09 (MSVC 14.5x, UE 5.8, DebugGame editor).

---

## 1. The problem

A class template defined in a shared header is instantiated **in every module
that uses it** unless the build says otherwise. When the template's out-of-line
member definitions live in the owning module, that module must export exactly one
instantiation and every consumer must be told not to instantiate its own —
otherwise each consumer emits its own copy of the members, and the linker pulls
in unresolved `dllimport` symbols.

The recipe is a **pair**: an explicit instantiation in the owning module's `.cpp`
and an `extern template` declaration in every consumer header.

## 2. The class template must not carry the export macro

Do **not** decorate the class template itself:

```cpp
// AVOID — this exports the whole template, not one instantiation:
template <typename T>
class MYMODULE_API TFoo
{
    ...
};
```

`dllexport` on the template exports **every** instantiation, so a consumer in a
different module can no longer emit its own: the compiler treats the
specialization as imported and the link fails on member symbols it expected the
exporting module to provide. Declaring `extern template` on a
`dllexport`-decorated class is rejected outright:

- **C4910** — `__declspec(dllexport)` cannot be applied to an explicit
  instantiation; `extern` is implied.

What crosses the boundary is therefore the **instantiation**, not the template.
Keep the class template undecorated.

## 3. The recipe

**Owning module `.cpp`** — the explicit instantiation carries the module's API
macro:

```cpp
template class MYMODULE_API TFoo<FBar>;
```

**Consumer header** — the declaration is `extern` and **undecorated**:

```cpp
extern template class TFoo<FBar>;
```

The consumer only needs "do not instantiate this locally"; the symbols come from
the exporting module. The two forms are not interchangeable: the instantiation
carries the macro, the `extern` declaration does not.

## 4. Ordering: after every specialization the instantiation uses

When the class template instantiates **another** template that the owner
specializes — typically a traits / selector specialization — the `extern
template` declaration must appear **after** that specialization. Declared before
it, the compiler instantiates the class early against the primary template, and
the later specialization then contradicts it:

- **C2908** — explicit instantiation already occurred.
- **C2766** — explicit specialization already defined.

Rule: write `extern template class TFoo<FBar>;` below every specialization of a
template whose expansion `TFoo<FBar>` uses.

## 5. Static data members

A static data member declared with the module API macro is exported/imported
normally and is what keeps **one shared object** across modules (a registry, a
singleton, a shared counter). Without the macro, each module gets its own copy —
the classic "two registries" defect. Class-body-inline members are a separate
case (§6).

## 6. Verify with the binary, never with intent

"This code exists once in the DLL" is a claim about the **built artifact**, and
only the artifact settles it. Read the exporting module's tables:

```
dumpbin /exports <module>.dll
dumpbin /imports <module>.dll
```

Other toolchains expose the same tables (`llvm-readobj --coff-exports` /
`--coff-imports`, or the platform's equivalent). What matters is the check, not
the tool.

Only **non-inline** entities cross the boundary. A member defined in the class
body is implicitly inline; it may still be emitted in every consumer, so
"instantiated once" is usually false for such members even though the type looks
exported. Do not reason from the source: class-body-inline members,
`inline`/`constexpr` statics, and implicitly instantiated templates all produce
local copies.

Corollary (owned by `rem-docs-and-config` §3): a claim about how many copies of
code exist, or about what a boundary shares, is a **measurement** obligation —
the review checks the claim, not the design.

## 7. A missing instantiation fails silently

Nothing enforces the pair. A type that forgets its explicit instantiation does
not fail to build — it simply instantiates locally in each consumer, which is
exactly the state the recipe exists to prevent. Keep the instantiation and its
`extern` declaration together as one unit, and put the pair on the review
checklist; the compiler will not report a missing one.

## Checklist

- [ ] The class template carries no module export macro
- [ ] The owning `.cpp` has `template class MYMODULE_API TFoo<FBar>;`
- [ ] Every consumer header has an undecorated `extern template class TFoo<FBar>;`
- [ ] The `extern template` sits after any specialization the instantiation uses (no C2908/C2766)
- [ ] Static data members that must be shared carry the module API macro
- [ ] Export/import tables were read (`dumpbin /exports` / `/imports` or equivalent) before claiming one copy exists
