# File & Include Layout

Detail moved out of `SKILL.md` so the rules stay scannable.

### Encoding and line endings

Source files are **UTF-8 without a BOM**. The BOM is not content: it turns the first line into a
different line, so a file that gains or loses one shows an unrelated diff, and a tool that re-adds it
silently rewrites the header line. For the same reason, never let a tool change a file's line endings;
in a repository with `core.autocrlf` set, that churn is invisible in `git diff` and surfaces later as a
whole-file rewrite.

### Header file layout (exact order)

```cpp
// Copyright RemRemRemRe. {Year}. All Rights Reserved.

#pragma once

// 1. Base class header
#include "Kismet/BlueprintFunctionLibrary.h"

// 2. Other dependencies (categorize at your discretion)
#include "RemNotNull.h"
#include "UObject/Object.h"

// 3. generated.h — MUST be included BEFORE any type declarations.
//    GENERATED_BODY() expands to a macro defined in the generated header; a
//    trailing include leaves it undefined (C4430). UHT emits forward
//    declarations itself, so the include stays outside namespaces.
#include "MyFile.generated.h"

// 4. Forward declarations (after all #includes)
class UObject;
class UWorld;
struct FGameplayTag;
template <typename T> struct TIsUEnumClass;
enum class ESomeEnum : uint8;
```

### Source file layout

```cpp
// Copyright RemRemRemRe. {Year}. All Rights Reserved.

// 1. Own header first
#include "MyFile.h"

// 2. Other dependencies
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"

// 3. Inline generated cpp by name (if needed)
UE_INLINE_GENERATED_CPP_BY_NAME(MyClass)

// 4. File-local objects: console variables, helpers, constants — anonymous namespace,
//    not file scope behind `static`
namespace
{

TAutoConsoleVariable<bool> CVarFeatureEnabled{TEXT("My.Feature.Enable"), true, TEXT("help text")};

}

// 5. Implementation ...
```

### Rules

| Rule | Details |
|------|---------|
| Copyright header | `// Copyright RemRemRemRe. {Year}. All Rights Reserved.` on every file; **new files follow the owning module's existing format** (some legacy modules use the no-year variant — migrate a module's header format as a separate pass, not inside feature commits) |
| `#pragma once` | Always, right after copyright |
| Base class first | In `.h`, the first `#include` is the base class header |
| `generated.h` before types | Must be included **before** any `UCLASS`/`USTRUCT` declaration (UHT requirement); forward declarations come after all includes |
| Own header first | In `.cpp`, matching header is the first `#include` |
| IWYU | Include every header directly used; do not rely on transitive includes |
| Incomplete type | Prefer a **forward declaration**; `#include` only when the complete type is needed (project rule) |
| Empty line separators | Separate groups with empty lines for readability |
| File-local objects | A console variable, helper function or constant that only the `.cpp` uses lives in an **anonymous namespace** at the top of the file, not at file scope behind `static` |
| `.inl` for templates | Heavy template implementations go in `FileName.inl` alongside the header. The `.h` stays minimal; callers `#include` the `.inl` directly when they need the template. Do NOT auto-include `.inl` from `.h` — it forces heavier transitive dependencies on every consumer of the `.h`. |

Dependency minimization is a HARD constraint: a `.h` never includes `.inl`.
Consumer-facing extension APIs that need `.inl` content live in their own
`FileName.inl` (e.g. `RemScopedStructContainer.inl` holds the container
`FindStructView` overloads); consumers include it explicitly. Shared primitives
used by several `.inl` files go in a dedicated lightweight `.inl`
(`RemStructViewStatics.inl`) — `.h` files still do not include it.

### Declaration / definition separation

Keep headers minimal to reduce reading noise. Inline function
definitions that must live in the header go at the **end of the file**
(after all declarations). Prefer `.cpp` for implementation bodies.

**Enforcement:** this applies to **every** inline definition that must stay in
the header — constructor bodies and small accessors in test-type headers
included. A method or constructor body written inside the class body is a
review rejection; declare it in the class and define it at the file bottom
(or in the `.cpp`).

```cpp
// MyType.h
#pragma once

USTRUCT()
struct FMyType
{
    GENERATED_BODY()

    void Initialize();
    void Shutdown();

private:
    int32 SomeHelper() const;
};

// --- inline definitions at file bottom ---
inline int32 FMyType::SomeHelper() const
{
    return 42;
}
```

---
