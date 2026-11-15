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

`get_file_problems` **misses the WEAK WARNING tier entirely**, and in practice the
WARNING tier too: measured 2026-11, a file whose two WARNINGs `lint_files`
reported came back as `errors: []` with `--onlyErrors false` as well, so treat
`get_file_problems` as the ERROR-only probe it behaves like. `lint_files`
returns WARNING and above — including the WEAK WARNING class of "can be made"
suggestions:

```
Parameter 'X' can be made const
Variable 'Y' can be made constexpr
```

Run `lint_files --files '[<paths>]'` (same batch loop) and act on **WEAK
WARNING and above**; WEAK WARNINGs are the "can be made const / constexpr"
family and are cheap to fix. **Its severity arguments are inert**: measured
2026-11, `--severities '["HINT"]'` and `--minSeverity HINT` were both accepted
and silently ignored — the same WARNING set came back — so there is no way to
ask for a narrower or wider band. HINTs never arrive through MCP; check those
manually (§4 member ordering, declaration/member order, spelling). Verified
2026-08: a `const`-able parameter in a test header was invisible to
`get_file_problems` (`errors: []`) and only `lint_files` reported it.

**Detection only — no quick-fix tool.** Rider MCP exposes no intention/quick-fix
action: `lint_files` detects but cannot fix (`--fix` is ignored), and
`reformat_file` is formatting-only — it never adds `virtual`, `const` or an
access specifier, so those findings stay manual. Probed 2026-11: no
`apply_quick_fix` / `quick_fix` / `fix_file_problems` / `apply_intention` /
`code_cleanup` tool exists either. A fix is therefore always an edit plus a
re-lint that proves the finding is gone.

The calls a sweep actually uses (paths relative to the workspace root, one batch
per call): `get_file_problems --filePath <path>`, `lint_files --files '["<path>", ...]'`,
`reformat_file --files '["<path>"]'`, `search_text --q <regex> --maxResults <n>`.
Of those four, only `reformat_file` writes — and it writes only formatting (see the
flush trap below).

**A flush can overwrite a hand edit (verified 2026-11).** `rename_refactoring` and
`reformat_file` act on the IDE's in-memory copy of a file, and
`post_edit_quality_check` is what writes that copy back to disk — replacing the
file whole, including any hunk edited directly after the IDE last read it. Re-apply
the hand edit, verify it, and never flush after one.

**Some inspections are unreachable — do not chase them.** An "Indent size is
incorrect, expected N spaces" WARNING survived `reformat_file` (a no-op) on a line
that already carried exactly N leading spaces. When the reported expectation and
the file agree, the finding is a tool artifact: record it, allowlist it, move on.

**WARNING-tier visibility issues are also only caught reliably by a sweep of
files the reformat did not touch.** The reformat pass lints only the files it
changed; pre-existing findings in untouched files (e.g. module impl classes
whose `StartupModule`/`ShutdownModule` overrides lack `public:` — the default
class access is private, so the override visibility narrows from the public
base) stay silent until a full `lint_files` sweep. Sweep the whole module's
`Source/` when the change set touches a plugin, not just the diff files.

A visibility **widening** is not a defect: raising a derived access specifier
(`protected` → `public`) is legitimate and may be exactly what an external
caller needs — only a **narrowing** below the base is. Check external callers
before "aligning" a member to its base; a blind alignment broke a build.

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

### Known Rider analysis false positives (verified 2026-08, re-verified 2026-09 on Rider 2026.2.2)

`lint_files` / `get_file_problems` sometimes report **problems the build does
not reproduce** — the code compiles fine. Do not "fix" these without checking
against the compiler:

- **UTF-8 `%s` format arguments** (WARNING) — `FUtf8String::Printf("%s",
  Utf8StringVar)` and `UE_LOGF(..., "%s", Utf8Builder)` are reported as
  "Cannot print value of type const char8_t* that implies specifier %p with
  format specifier %s that implies type const char*". UE 5.x explicitly
  supports UTF8CHAR strings as `%s` arguments (`Utf8String.h` header comment:
  "the string still supports UTF8CHAR strings as arguments, e.g.
  FUtf8String::Printf("Name: %s", Utf8Name)"; `LogMacros.h`: "Prefer UE_LOGF
  because its ASCII or UTF-8 format strings"). Rider does not know the `%s`
  overload accepts char8_t). Live cases (UE 5.8.3 / Rider 2026.2.2):
  the `UE_LOGF(..., "%s", *EnsureBuilder)` calls in `RemAlsMacros.cpp` and a file
  in a non-public plugin (`FUtf8String::Printf("%s.Completed",
  *...ToUtf8String())`) — only `lint_files` reports them;
  `get_file_problems` returns clean for both files.
- Triage rule: an ERROR that looks like a missing include, unresolved alias,
  or failed template substitution in a file that **compiles** (the build
  passed) is a Rider analysis bug, not a real defect. Cross-check with the
  build result before touching the code.

### Known false positives, and one true positive in disguise (verified 2026-09)

More families confirmed as noise on this codebase - do not "fix" them:

- **Redundant `typename`** on a dependent nested type: **not a false positive since C++20** — P0634R3
  makes the prefix optional wherever only a type can appear (a leading return type, a parameter, a
  template argument, an alias RHS), which is exactly where this hint fires. It is still *required*
  in contexts the grammar cannot disambiguate (a variable declaration in a block scope). Verified
  with MSVC 19.50 on one file: it compiles with the prefix removed under `/std:c++20 /permissive-`
  and fails with `C2061`/`C2059` under `/std:c++17`. Keeping the prefix is a style choice, not a
  correctness one — do not add it back "to fix the analyzer", and do not assume every compiler in
  reach implements P0634 (UE 5.8's toolchains do).
- **Redundant template arguments / "use CTAD"** where the explicit argument is *semantically*
  required - e.g. naming the base class a weak pointer should erase to on purpose. Deduction would
  change the meaning, not just the spelling.
- **"Parameter can be made pointer to const"** applied to a wrapper-pointer API that stores a
  non-const `T*` internally: following it breaks the wrapper's type and its contract.
- **Unused template parameters** of a SFINAE primary template (they exist to switch the
  specialization).

The inverse also happens: a diagnostic that looks like stale analysis can be **correct**. An
incomplete-type conversion reported in a header that only forward-declares the type is real, and the
same shape may be reported *clean* in a neighbouring header - that clean report is the analysis
miss, not evidence. When a diagnostic is plausible, adjudicate it against the language rule or a
minimal repro before dismissing it.
