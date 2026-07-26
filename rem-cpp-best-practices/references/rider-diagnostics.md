# Rider MCP Diagnostics

Detail moved out of `SKILL.md` so the rules stay scannable.

Run IDE diagnostics on every changed file **before committing**, not only after
the build. `get_file_problems` catches issues incremental builds mask:

- missing `#include`s (an incomplete type compiles when another translation
  unit pulls the header in transitively — UHT still sees the broken header)
- operand/type mismatches in expressions the compiler happens to accept
- `UCLASS`/`USTRUCT` structure errors

Usage: `get_file_problems --filePath <abs-path>` on each changed file (batch
them in one `mcpScript` loop). **Severity contract**: ERROR and WARNING are
returned; **HINT severities are NOT exposed** — e.g. Rider's "declaration
order should match definition order" hint never arrives through MCP, so
member/declaration ordering must be checked manually (see §4 member ordering).
After fixing, re-run to confirm clean — a real case: a `UObject*`/`UPackage*`
ternary and a missing `GameFramework/Actor.h` include both passed the build
and were caught only by `get_file_problems`.

### Full-severity sweep: use `lint_files`, not just `get_file_problems`

`get_file_problems` **misses the WEAK WARNING tier entirely** (it returns
ERROR/WARNING only). `lint_files` returns every severity — including the
WEAK WARNING class of "can be made" suggestions:

```
Parameter 'X' can be made const
Variable 'Y' can be made constexpr
```

Run `lint_files --files '[<paths>]'` (same batch loop) and act on **WEAK
WARNING and above**; WEAK WARNINGs are the "can be made const / constexpr"
family and are cheap to fix. HINTs still never arrive through MCP — check
those manually (§4 member ordering). Verified 2026-08: a `const`-able
parameter in a test header was invisible to `get_file_problems` (`errors: []`)
and only `lint_files` reported it.

**WARNING-tier visibility issues are also only caught reliably by a sweep of
files the reformat did not touch.** The reformat pass lints only the files it
changed; pre-existing findings in untouched files (e.g. module impl classes
whose `StartupModule`/`ShutdownModule` overrides lack `public:` — the default
class access is private, so the override visibility narrows from the public
base) stay silent until a full `lint_files` sweep. Sweep the whole module's
`Source/` when the change set touches a plugin, not just the diff files.

### MCP silence is not proof the file is clean

The severity contract is **context-dependent**. In a C project context (a
`.c`/`.h` analysed as part of a C project), the "can be made const" family and
the spell-checker typos are HINT-level and do not arrive through MCP at all —
`get_file_problems` and `lint_files` return only the unrelated ERRORs.

Verified 2026-09 on a vendored C header: the Rider UI listed ~75
`Parameter 'x' can be made const` and ~60 `Typo: In word ...` entries while both
MCP calls returned exactly one ERROR (a C-context include-path artifact). Never
conclude "no suggestions" from an empty MCP result — when a file is analysed in
a second project context, read the Rider UI or ask for the list.

Watch the C-context cascade too: one C++ construct in a header included by `.c`
files (default arguments) makes Rider parse the rest as C and emit cascaded
`Expected ',' or ')'` / `Type-specifier missing` / `Assigned value is never used`
noise. Fix the root cause or ignore the context — and check which compiler the
build actually uses before "fixing" C semantics: a Makefile with `CC = g++`
compiles `.c` files as C++, so C99 `inline`/default-argument rules do not apply.

### Known Rider analysis false positives (verified 2026-08)

`lint_files` / `get_file_problems` sometimes report **ERRORs that the build
does not reproduce** — the code compiles fine. Do not "fix" these without
checking against the compiler:

- **Strong-alias construction** (`strong_alias` wrapper types) — constructing
  an alias from a related enum/value is reported as `No viable constructor` /
  `does not satisfy concept strong::is_alias` / `Substitution failed`:
  e.g. `Rem::Enum::EExcludeSelf{Rem::Enum::EYesOrNo::Yes}`, or a struct alias
  over `Rem::Struct::TScopedStructContainer<>*` constructed from a container
  pointer. Rider fails to resolve the alias concept constraint; the compiler
  accepts it.
- **UTF-8 `%s` format arguments** — `FUtf8String::Printf("%s", Utf8StringVar)`
  and `UE_LOGF(..., "%s", Utf8Builder)` are reported as "Cannot print value of
  type const char8_t* ... with format specifier %s". UE 5.x explicitly supports
  UTF8CHAR strings as `%s` arguments (`Utf8String.h` header comment: "the string
  still supports UTF8CHAR strings as arguments, e.g. FUtf8String::Printf("Name:
  %s", Utf8Name)"; `LogMacros.h`: "Prefer UE_LOGF because its ASCII or UTF-8
  format strings"). Rider does not know the `%s` overload accepts char8_t.
- **Alias-type copy constructions** — e.g. `TSoftClassPtr` reported as
  "Cannot resolve symbol" / "Cannot substitute template argument", or
  `SListView<TWeakObjectPtr<UWidget>>` reported as "Type ... is incomplete",
  when the types are typedef/alias aliases Rider's analysis fails to resolve.
  (Observed in `RemWidgetComponentEditorSetting.h` and
  `RemComponentBasedWidgetDetails.cpp`.)
- Triage rule: an ERROR that looks like a missing include, unresolved alias,
  or failed template substitution in a file that **compiles** (the build
  passed) is a Rider analysis bug, not a real defect. Cross-check with the
  build result before touching the code.
