# Build-Fix Loop

Detail moved out of `SKILL.md` so the rules stay scannable.

For the **current engine version**, repeatedly:

```
 1. Build the plugin
 2. If PASS → version done, exit loop
 3. Read error output
 4. Analyze errors, decide fix strategy
 5. Apply fix to source files
 6. Git commit the fix
 7. Go to 1
```

### 6.1 Quick-Reference Card

When you see an error, scan this table first. If the symbol matches, apply
the fix directly. For unfamiliar symbols, look them up in
[references/version-diff-guide.md](references/version-diff-guide.md).

| Error code | What it means | First action |
|-----------|---------------|-------------|
| C2039 | `'X': is not a member of 'Y'` | Check version-diff-guide for X -> use older API or wrap |
| C3861 | `'X': identifier not found` | Check if macro/function was added in a later version |
| C1083 | `Cannot open include file: 'X'` | Search engine source for correct path (may differ by version) |
| C2065 | `'X': undeclared identifier` | Usually a missing include — add it |
| C2440 | `cannot convert from 'A' to 'B'` | Make construction explicit; check implicit conversion rules |
| C2664/C2668 | Conversion/overload ambiguity | `explicit` keyword, `static_cast`, or adjust signature |
| UBT error | Module not found | Edit Build.cs dependencies (module renamed/split) |
| C2672/C2783 | Template deduction failure | Add explicit template arguments |

**Quick decision tree**:
1. Symbol in version-diff-guide? -> Apply documented fix
2. Symbol not documented? -> Search engine source for the symbol; if absent, it's new -> wrap/guard
3. Include error? -> Search engine source for the header; it may have moved
4. Module error? -> Check if module was renamed/merged in the target version

### 6.2 Invoke build

```bash
python <skill-dir>/tools/build_plugin.py \
  -n <plugin-name> \
  -v <version> \
  --config "<path-to-local-config>" \
  --plugin-path "<build-repo>" \
  --output-path "<output-dir>"
```

The script prints a configuration summary, runs RunUAT BuildPlugin, and
reports PASS or FAIL. On failure, the last 40 lines of stderr are shown.

If `logs.dir` is configured (see §10), full build logs are written to
`{logs.dir}/build/` and the operation timeline to `{logs.dir}/operation/`.
Point the user to these for review.

**Capture the full output** — you need it for error analysis:

```bash
python <skill-dir>/tools/build_plugin.py -n <plugin> -v <version> --plugin-path "<build-repo>" 2>&1 | tee build_ue<version>.log
```

### 6.3 Read and classify errors

Extract errors from the build log. MSVC error format:

```
file(line): error CXXXX: message
file(line,col): error CXXXX: message
file(line): fatal error CXXXX: message
```

Group errors by:
- **File** — which source file has the problem
- **Error code** — C2039 (not a member), C3861 (identifier not found),
  C1083 (cannot open include), C2065 (undeclared identifier), C2440 (cannot convert),
  C2664 (cannot convert argument), etc.
- **Symbol** — the specific identifier that failed

> **Tip**: If the symbol looks like a UE API, check
> [references/version-diff-guide.md](references/version-diff-guide.md) first —
> it maps known symbols to the version that introduced them and the older
> equivalent.

### 6.4 Decide fix strategy

Analyze each error and choose a fix strategy. See
[references/error-patterns.md](references/error-patterns.md) for detailed,
real-world examples with before/after code, and
[references/version-diff-guide.md](references/version-diff-guide.md) for a
symbol-level lookup table. Below is a quick reference:

| Error category | Typical fix |
|---------------|-------------|
| API not available in older version | **Revert + re-fix**: replace the newer API with the older equivalent directly in source. Do NOT use `#if` guards — the adaptation branch is version-specific. |
| Include path changed | Replace `#include "Old.h"` → `#include "New.h"` |
| Missing include entirely | Add `#include "..."` after last existing include |
| Module dependency renamed/removed | Edit `Build.cs` — add/remove `PublicDependencyModuleNames` or `PrivateDependencyModuleNames` |
| Feature not available at all | Revert the feature implementation; re-implement using only APIs available in the target version |
| Feature needs backport | Copy self-contained API code from newer engine into plugin (if small, few files). If too large, disable the feature + document limitation. |
| Constructor/conversion ambiguity | Add `explicit`, adjust initialization syntax |
| Template argument deduction failure | Add explicit template arguments, adjust SFINAE constraints |

### 6.5 Apply the fix

Use `edit` to modify source files. Key principles:

- **Revert + re-fix**: the adaptation branch is engine-version-specific.
  Rather than wrapping code in `#if ENGINE_MAJOR_VERSION` guards (which creates
  dead code that must be maintained), revert the incompatible change and
  re-implement it using only APIs available in the target engine version.
- **Minimal change**: fix only what's broken, don't reformat or refactor
- **One concern per commit**: each fix gets its own commit

Real adaptation commits follow this pattern — they replace the newer API
with an older equivalent or a project-namespace wrapper:

```cpp
// BEFORE (5.4+ API):    FMath::Modulo(Angle, 360.0f);
// AFTER  (revert+fix):  Foo::Math::Modulo(Angle, 360.0f);  // project-namespace wrapper

// BEFORE (5.4+ macro):  GET_MEMBER_NAME_STRING_VIEW_CHECKED(T, F)
// AFTER  (revert+fix):  GET_MEMBER_NAME_STRING_CHECKED(T, F)

// BEFORE (5.4+ util):   MakeArrayView(&S, 1)
// AFTER  (revert+fix):  TArrayView<T>(&S, 1)
```

### 6.6 Commit

```
git add -A
git commit -m "Fixed: <brief description of the fix>"
```

Commit message format:
- **Fixed:** — a fix that resolves a compilation error
- **Changed:** — a deliberate change/adaptation (version boundary, dependency update, reverting a new feature)
- **Misc:** — cleanup, formatting, non-functional changes

Examples from real adaptation history:
```
Fixed: FMath::Modulo and FMath::FMod is not available on 5.3
Fixed: missing include
Fixed: import changes from 5.7
Fixed: struct view constructor should be explicit
Changed: set engine version 5.4
Changed: disable <DepC> in 5.3
Changed: revert changes for ParseParentTags
```

### 6.7 Repeat

Go back to 6.2. If the same errors persist after a fix, re-read the code
carefully — the fix may not have been applied correctly, or there may be a
deeper root cause.

If no clear fix strategy exists, report the error to the user with context
and ask for guidance.

#### Handling cascading errors

A single root cause (a missing macro, an undefined symbol, a syntax error)
can produce many downstream errors: overload resolution failures, type
conversion noise, and "missing ';' before ..." in the same translation unit.
**Fix the root cause first, rebuild, then reassess** — many secondary errors
vanish once the parse recovers.

#### Prefer compat shims over call-site changes

When a newer-engine macro/API is missing on an older engine and a faithful
drop-in can be replicated (e.g., `GET_MEMBER_NAME_ANSI_STRING_VIEW_CHECKED`
via `ANSITEXTVIEW(#M)`), declare a `#ifndef`-guarded shim and **keep the
original call sites**. This keeps the adaptation branch closest to upstream.
Only change call sites when a faithful shim is impossible.

#### Cross-version note

When adapting version N-1 after N is done: if a fix from version N causes a
compilation error in N-1, **go back to the N-level source** and revert the
incompatible change, then re-implement it using APIs available in N-1.
The git history may include commits like
"Fixed: adjust X.Y fix for X.Y-1 compatibility".

#### Incremental trust — do NOT re-verify finished versions

Each engine version is verified once, at the time it is adapted. Once a
version's build passes and it is packaged, **do not rebuild higher versions
after adapting a lower one** — even if shared source files (compat headers,
Build.cs, etc.) changed. Higher versions are already built and packaged; the
lower-version changes only matter the next time those versions are rebuilt,
which would surface any issue then. Re-running builds for finished versions
wastes time and provides no new information.

---
