---
name: rem-ue-plugin-adapter
description: >
  Multi-engine Unreal Engine plugin adaptation workflow. Guides the AI through
  adapting a UE plugin from upstream latest code down to 5.3–5.8 engine versions.
  Covers branch management, dependency embedding, cherry-picking prior adaptation
  commits, the build-fix-commit loop (compile, read errors, decide fixes, commit),
  and final verification. Use when the user asks to adapt a plugin to multiple
  engine versions, run cross-version builds, or fix compilation errors across
  UE 5.3–5.8. Trigger: manual. Last verified: 2026-07.
metadata:
  category: meta
  trigger: manual
---

# UE Plugin Multi-Engine Adapter

Adapt a UE marketplace plugin from upstream latest code to **engine versions
5.3 through 5.8**, going high-to-low (newest engine first). The AI drives the
workflow: runs builds, reads errors, decides and applies fixes, commits.

---

## 1. Prerequisites

Before starting, verify:

| Item | Check |
|------|-------|
| Plugin `local.json` | Per-plugin config exists **outside the skill** (e.g. `<config-dir>/<Plugin>/local.json`) — see §10. Passed via `--config`; the tools **error out** if it is missing or mismatched |
| Machine engines config | Referenced by the plugin config via `engines_config` (e.g. `<config-dir>/engines.local.json`); template at `<skill-dir>/tools/engines.json` |
| Python 3.8+ | Available on PATH (`python --version`) |
| Git | Available on PATH; build repo is a git repository |
| Upstream remote | Build repo has `upstream` remote pointing to plugin source |
| Old adapt branch | Previous adaptation branch exists in build repo |
| Adaptation notes | Plugin-specific knowledge (dependencies, disabled modules, known regressions) lives in the plugin's external config dir — read before starting |

The tool scripts live in `<skill-dir>/tools/`. All paths in this skill
are relative to the skill root (`rem-ue-plugin-adapter/`) unless stated
otherwise. When executing commands, prepend the skill directory path.

For setting up the Visual Studio development environment for C++ work
(compiler toolchain, IDE, debugger), see Epic's official guide:
[Setting Up Visual Studio Development Environment for C++ Projects](https://dev.epicgames.com/documentation/unreal-engine/setting-up-visual-studio-development-environment-for-cplusplus-projects-in-unreal-engine).

Example: `<skill-dir>/tools/build_plugin.py` expands to the full path of
the build script.

### Verify with dry-run

```bash
python <skill-dir>/tools/build_plugin.py -n <plugin> --config "<path-to-local-config>" -v <version> --dry-run
```

This checks that RunUAT.bat and .uplugin exist without running a build.
`--config` points to the **plugin's external local.json** (see §10) — it is
required and the tools fail with usage hints if it is missing.

---

## 2. Workflow Overview

```
Step 1: Branch setup     → rename old branch, checkout upstream, create adapt branch
Step 2: Embed deps       → copy dependent plugin source, remove external deps
Step 3: Cascade adapt    → for each version (high→low):
  3a. Cherry-pick        → pick adaptation commits from old branch
  3b. Update deps        → refresh embedded dependency code
  3c. Version boundary   → commit "Changed: set engine version X.Y"
  3d. Build-Fix Loop     → compile → read errors → fix → commit → repeat
Step 4: Final verify     → all versions build, run tests, update changelog
```

Each step is detailed below. The AI performs each step manually — read the
instructions, execute the commands, observe results, and proceed.

---

## 3. Step 1 — Branch Setup

### 3.1 Rename current branch

```bash
cd <build-repo>
git branch -m old-<YYYYMMDD>
```

### 3.2 Fetch upstream and create adapt branch

```bash
git fetch upstream
git checkout -b adapt-5.3-to-5.8 upstream/main
```

The branch name follows the pattern `adapt-<lowest>-to-<highest>`.

### 3.3 Verify

```bash
git log --oneline -5
```

Confirm the latest commit is from upstream/main.

---

## 4. Step 2 — Embed Dependencies

Marketplace plugins cannot declare external plugin dependencies (Fab requires
independent binaries). Dependent plugins must be copied into the current plugin
as embedded modules.

### 4.1 Copy dependency source

Dependency **sources are machine-specific paths** defined in the local engine
config (`engines.local.json` → `dependencies` map, see §10). The dependency
**names** to embed come from `adapt_config.json` in the build repo root.

For each dependency:

```bash
# Remove old copy (ensures no stale files)
rm -rf Source/<DepName>

# Copy latest source (path from engines.local.json dependencies map)
cp -r <dependency-source-path>/Source/* Source/<DepName>/
```

The AI must read the `dependencies` map from the local config to know where
each dependency's source lives, and cross-reference it with
`adapt_config.json`'s dependency names to know which ones to embed.

**Clean nested git dirs**: third-party libraries embedded via `ThirdParty/`
often carry their own `.git` / `.gitmodules` (submodules). Remove them after
copying, or git will treat them as nested repositories instead of tracking
their contents:

```bash
find Source/ThirdParty -name .git -type d -prune -exec rm -rf {} \;
rm -f Source/ThirdParty/.gitmodules
```

> Note: `find` here is used for cleanup, not code search.

### 4.2 Update .uplugin

Edit `<PluginName>.uplugin`:
- **Remove** entries from the `"Plugins"` array for each embedded dependency
- **Keep** entries in the `"Modules"` array (the module code now lives in-tree)
- **Version bump**: if `plugin_version` is set in local config, update
  `VersionName` at the first version boundary (see §5.3); remove the redundant
  `"Version"` integer field

**Shared build rules**: embedded modules may reference a shared build-rule
class defined in a sibling module's `Build.cs` (e.g. a
`SharedModuleRules.Apply(this)` helper in a common module). No expansion
is needed — the class compiles with the module and resolves for all
`using <SharedRuleNamespace>;` references in sibling modules.

**`plugin_path` semantics**: `defaults.plugin_path` must be the directory
*containing* `<PluginName>/` (the parent), not the plugin directory itself.
Tools resolve the `.uplugin` as `{plugin_path}/{PluginName}/{PluginName}.uplugin`.

### 4.3 Commit

```bash
git add -A
git commit -m "Changed: embed dependency plugins"
```

> **Note on dependency adaptation**: Embedded dependencies (e.g., `<DepA>`,
> `<DepB>`) are adapted as part of this workflow. Their source
> files are included in the build-fix cycle. This means the build-fix loop in
> §6 will also fix version-specific issues in dependency code. In the future,
> dependencies may maintain their own multi-version `#if` guards, at which
> point they would only be copied without modification.

> **Reference**: Look at the old adapt branch for the equivalent commit to
> understand the exact .uplugin modifications needed. Also see
> [references/original-requirements.md](references/original-requirements.md)
> for the full workflow rationale and design decisions.

---

## 5. Step 3 — Cascade Adaptation

Process engine versions **highest to lowest** (e.g., 5.8 → 5.7 → ... → 5.3).

### 5.1 Determine cherry-pick ranges

The old adapt branch has a commit structure like:

```
upstream-sync → [... 5.7 fixes ...] → "set engine version 5.7" →
  [... 5.6 fixes ...] → "set engine version 5.6" →
  [... 5.5 fixes ...] → "set engine version 5.5" →
  ... → "set engine version 5.3"
```

Cherry-pick ranges (newest version first):

| Version | Range | What it contains |
|---------|-------|-----------------|
| 5.8     | `upstream-sync`..`set engine version 5.7` | Base adaptations from 5.7 sync |
| 5.7     | `set engine version 5.7`..`set engine version 5.6` | 5.7-specific fixes |
| 5.6     | `set engine version 5.6`..`set engine version 5.5` | 5.6-specific fixes |
| ...     | ... | ... |
| 5.3     | `set engine version 5.4`..`set engine version 5.3` | 5.3-specific fixes |

**How to find the commits** — run this command to locate version boundaries:

```bash
git log old-<YYYYMMDD> --oneline --grep="set engine version"
```

Then for each version, cherry-pick the commits between its boundary and the next:

```bash
# Example for 5.7: cherry-pick commits between "set engine version 5.7"
# and "set engine version 5.6" (exclusive)
git cherry-pick <commit-after-5.7-boundary>..<5.6-boundary-commit>
```

**Conflict resolution**: if cherry-pick encounters conflicts, resolve them
manually. Common conflicts occur when the same file was modified differently
across versions. After resolving:

```bash
git add <resolved-files>
git cherry-pick --continue
```

**Skip already-adopted commits**: before resolving a conflicted cherry-pick,
check whether the commit's *substance* already exists in the current HEAD
(e.g., upstream adopted the same change later). Compare the diff ignoring
whitespace (`git show <sha> -w`); if the change is already present, abort
the cherry-pick (`git cherry-pick --abort`) and skip it — resolving the
conflict would only re-apply stale edits.

**Config-file conflicts**: for files restructured locally (e.g., `.uplugin`
with embedded modules), a small upstream change conflicts wholesale. Resolve
by keeping the HEAD version (`git checkout --ours <file>`) then manually
apply only the intended value change (e.g., `EnabledByDefault: false → true`).

### 5.2 Update embedded dependencies

Same as Step 2, but incremental — delete old copies, copy latest source,
commit:

```bash
rm -rf Source/<DepName> && cp -r <path>/* Source/<DepName>/
git add -A && git commit -m "Changed: update embedded dependencies for X.Y"
```

### 5.3 Commit version boundary

```bash
git commit --allow-empty -m "Changed: set engine version X.Y"
```

This empty commit marks where one engine version's adaptations end and the
next begins. It is the delimiter for future cherry-pick operations.

**Version bump**: at the **first** (highest) version boundary, if the local
config has a non-empty `plugin_version` (e.g., `"4.1.0"`), write it into the
`.uplugin` `VersionName` in the same commit. The old `"Version"` integer
field is removed as redundant. After the **full** adaptation (all versions)
completes, clear `plugin_version` back to `""` in the local config.

### 5.4 Build-Fix Loop

**This is the core interactive step.** See Section 6 for the detailed
procedure.

---

## 6. Build-Fix Loop

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

## 7. Step 4 — Final Verification

After all versions build successfully:

- [ ] Spot-check: run `build_plugin.py` on a representative version to confirm
  no regressions
- [ ] **Incremental trust**: each version's build was verified at the time it
  passed — a full rebuild of all 6 versions is not mandatory unless there's
  reason to suspect cross-version breakage
- [ ] Check output directories contain built binaries
- [ ] Run automated tests if available
- [ ] Update CHANGELOG
- [ ] Push branch and create PR/Release
- [ ] To produce encrypted release archives, see Step 5 — **manual, requires user authorization**

---

## 8. Step 5 — Archive Packaging (manual, user-authorized)

> **Trigger**: this step is **manual and requires explicit user authorization**.
> The AI never runs packaging on its own — it proposes the commands and the user
> approves or executes them. Packaging creates **encrypted** 7z archives with a
> random password; the password must never be written into git, logs, or skill
> files.

### 8.1 Prerequisites

| Item | Check |
|------|-------|
| All versions built & packaged | Output dir exists for every target version: `{output_path}/{platform}/{version}/{PluginName}/` |
| 7-Zip | `7z.exe` location (machine-specific, e.g. `D:/7-Zip/7z.exe` — ask the user) |
| `VersionName` | Read from `.uplugin` (e.g. `4.1.0`) — used in the archive name |

### 8.2 Generate a strong random password

```powershell
powershell -NoProfile -Command "$a='ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#%^*-_=+'; $r=[System.Security.Cryptography.RandomNumberGenerator]::Create(); $c=New-Object char[] 28; for($i=0;$i -lt 28;$i++){ $b=New-Object byte[] 1; $r.GetBytes($b); $c[$i]=$a[$b[0] % $a.Length] }; -join $c"
```

28 chars, mixed case + digits + symbols, excludes ambiguous chars (`0/O/1/l/I`).
Hand the password to the user for safekeeping; never commit it.

### 8.3 Create one archive per engine version

For each target version `X.Y` (e.g. `5.3`, `5.8`), run from the plugin's
**output** directory (not the source repo):

```bash
cd {output_path}/{platform}/{version}/{PluginName}
<7z> a -t7z -mhe=on -p"<PASSWORD>" "{output_path}/{platform}/{PluginName}{X}{Y}.{VersionName}.7z" \
    Config Source LICENSE-ALS-Refactored {PluginName}.uplugin
```

- `-mhe=on` — encrypts the archive header: file/dir names are **not visible
  before decryption**. Only `7z` format supports this; `zip` does NOT — always
  pass `-t7z`
- Add **only** `Config`, `Source`, `LICENSE-ALS-Refactored`, `{PluginName}.uplugin`
  — never `Binaries`/`Intermediate`
- Archive naming: `{PluginName}{Major}{Minor}.{VersionName}.7z`
  (version digits concatenated) → e.g. `FooPlugin58.4.1.0.7z` (plugin `FooPlugin`, version 5.8, VersionName 4.1.0)

### 8.4 Verify

```bash
# Without password: must fail or prompt for password (proves header encryption)
<7z> l {archive}.7z

# With password: top-level entries must be exactly the 4 expected items
<7z> l -p"<PASSWORD>" {archive}.7z
```

Check the top-level entries are only `Config`, `Source`,
`LICENSE-ALS-Refactored`, `{PluginName}.uplugin`, and that no
`Binaries`/`Intermediate` paths appear anywhere in the listing.

---

## 9. Git Conventions

### Branch naming

```
adapt-<lowest-version>-to-<highest-version>
```

Example: `adapt-5.3-to-5.8`

### Commit message prefix

| Prefix | Use |
|--------|-----|
| `Fixed:` | Fixing a compilation error for a specific engine version |
| `Changed:` | Deliberate adaptation: version boundary, dependency update, feature revert, config change |
| `New:` | Adding new capability (rare in adaptation) |
| `Misc:` | Cleanup, formatting, non-functional |
| `Improved:` | Enhancing existing code without fixing a bug |

### Commit granularity

**One logical change per commit.** Do NOT batch multiple unrelated fixes into
one commit. This keeps git history bisectable and cherry-pickable for future
adaptation cycles.

---

## 10. Tool Reference

### build_plugin.py

```
python <skill-dir>/tools/build_plugin.py \
  -n <plugin-name>          # required; must match config's plugin.name
  -v <version> [<v2> ...]   # engine version(s); default: all in engines config
  --plugin-path <path>       # override default plugin source dir
  --output-path <path>       # override default output dir
  --config <path>            # REQUIRED: path to the plugin's external local.json
  --dry-run                  # validate paths, skip build
  -q                         # suppress extra output
```

`--config` is **required** — the skill holds no machine/project data. If it
is missing, points to a nonexistent file, or its `plugin.name` does not match
`-n`, the tool errors out with usage hints.

### External config layout (skill stays clean)

The skill directory only contains generic workflow + generic engine knowledge.
All per-plugin data lives **outside** the skill, in a machine-specific config
dir (e.g. `<config-dir>/`):

```
PluginAdapterConfig/   # example name for the external config dir
├── engines.local.json          # machine-level engine paths (shared by all plugins)
└── <PluginName>/               # one directory per external plugin
    ├── local.json              # plugin config (required by --config)
    └── adaptation-notes.md     # plugin-specific knowledge/decisions (read+update each cycle)
```

### Plugin local.json (external, required)

```json
{
  "plugin": {
    "name": "<PluginName>",
    "plugin_path": "<parent-dir-containing-plugin>",
    "output_path": "<output-dir>",
    "platform": "Win64",
    "build_repo": "<path-to-build-repo>",
    "plugin_version": ""
  },
  "engines_config": "<abs-path-to-engines.local.json>",
  "dependencies": {
    "<DepA>": "<path-to-DepA-source>",
    "<DepB>": "<path-to-DepB-source>"
  },
  "upstream": { "remote": "<upstream-remote-name>", "branch": "<upstream-branch>" },
  "logs": { "dir": "<log-dir>" }
}
```

- **plugin.name**: must equal `-n`; mismatch → tool errors out
- **engines_config**: absolute path to the machine-level engines config
- **dependencies**: map of embedded dependency name → its source directory
  (machine-specific paths)
- **plugin_version**: one-shot version bump for this adaptation run (full
  semver, e.g. `"4.1.0"`). Written into `.uplugin` VersionName at the first
  version boundary commit; cleared after the full adaptation completes.
  Empty normally.
- **logs.dir**: where build/operation logs are written for human review

### engines.json (shared template)

`<skill-dir>/tools/engines.json` is the **machine-level shared template** with
placeholder paths. Copy it to the external config dir as `engines.local.json`
and fill in real paths (referenced from the plugin config via
`engines_config`). The template itself contains no personal paths.

```json
{
  "engines": {
    "5.8": { "root": "<source-engine-path>", "type": "source" },
    "5.7": { "root": "<binary-engine-path>/UE_5.7", "type": "binary" }
  }
}
```

- **root**: directory containing `Engine/` subfolder
- **type**: `"source"` (built from source) or `"binary"` (Epic official build)

Pass the plugin config explicitly:

```bash
python <skill-dir>/tools/build_plugin.py -n <plugin> \
  --config "<config-dir>/<plugin>/local.json" -v 5.8
```

### Log files

When `logs.dir` is configured, tools write logs for human review:

| Log | Path | Content |
|-----|------|---------|
| Build log | `{logs.dir}/build/{plugin}_{version}_{timestamp}.log` | Full stdout + stderr of each build invocation |
| Operation log | `{logs.dir}/operation/{plugin}_{version}.log` | Append-only timeline: builds, auto-fixes, commits, manual interventions |

Review the operation log to understand what the adaptation did; inspect
build logs for the full error output of any failing build.

> The `.bat` wrappers in `tools/` already pass `--config` — edit the `CONFIG`
> variable at the top to point to your local file.

### Error parsing script (optional)

For parsing build logs programmatically:

```bash
python <skill-dir>/tools/auto_fixer.py --log build.log --rules <skill-dir>/tools/fix_rules.json
```

This extracts structured errors but does **not** apply fixes automatically.
Use it to quickly identify error locations and match against known patterns.

---

## 11. Important Constraints

- **Marketplace binary independence** (Fab requirement, see
  [Fab Publishing docs](https://www.fab.com/docs/seller/publishing)):
  plugins cannot declare external plugin dependencies. Embed all dependencies.
- **`IncludeOrderVersion = EngineIncludeOrderVersion.Latest`** in Build.cs
  may need adjustment for older engines that don't recognize it.
- **Source-built vs binary engines**: source builds (like 5.8) may have
  features not yet in binary releases. Binary builds may have different
  module layouts. Verify each engine's capabilities before fixing.
- **C++ standard**: UE 5.3–5.8 all use C++20
  (`ModuleRules.CppStandardVersion.EngineDefault` resolves to C++20 across
  all these versions). Do NOT guard for C++23 features — none exist in this range.
- **Version guard macros**: `ENGINE_MAJOR_VERSION` and `ENGINE_MINOR_VERSION`
  are defined by UE in `Engine/Source/Runtime/Core/Public/Misc/CoreMiscDefines.h`.
  Prefer **revert + re-fix** over `#if ENGINE_MAJOR_VERSION` guards — each
  adaptation branch is engine-version-specific; guards create dead code that
  must be maintained across all versions.
- **Commit message format**: derived from project convention in the build
  repository's adaptation history (see §9 for full specification).
- **Version guard macros**: `ENGINE_MAJOR_VERSION` and `ENGINE_MINOR_VERSION`
  are defined by UE in `Engine/Source/Runtime/Core/Public/Misc/CoreMiscDefines.h`
- **BuildPlugin packaging environment ≠ dev project**: a plugin may compile in
  the developer's project but fail in BuildPlugin's isolated
  `HostProject` context. Always verify with the actual `build_plugin.py`
  packaging build, not just the dev project.
- **Never modify engine source**: all fixes must be in plugin code. Engine
  headers may be read for reference but never edited.
- **Push verified upstream fixes**: when a fix is verified in the embedded
  (marketplace) copy, apply it to the source plugin repo and push to its
  origin (repo URL recorded in the plugin's adaptation notes), so the next
  upstream sync includes it. Commit locally first; push timing is the user's call.

---

## Checklist

Before starting or resuming adaptation:

- [ ] Plugin `local.json` exists outside the skill and dry-run passes (`--config` required; tools error out otherwise)
- [ ] `engines.json` has all target versions with valid paths
- [ ] Build repo is a clean git working directory (`git status` is clean)
- [ ] Old adaptation branch is accessible (`git branch -a` shows it)
- [ ] Dry-run build passes for the current engine version
- [ ] Read [references/version-diff-guide.md](references/version-diff-guide.md) for known breaking changes between target versions

After each build-fix iteration:
- [ ] Fix is minimal — only addresses the specific error
- [ ] Fix uses **revert + re-fix** strategy: replaced newer API with target-version equivalent, no `#if` guards
- [ ] Prefer **compat shims over call-site changes** where a faithful drop-in exists (keeps diff minimal vs upstream)
- [ ] Backported engine headers checked: their `CORE_API` symbols and inner includes exist in the target engine (inline the missing ones)
- [ ] Version detection in C++ headers uses `#if defined(ENGINE_MAJOR_VERSION) && ...` or `__has_include`, not bare `#if ENGINE_MAJOR_VERSION`
- [ ] Root causes fixed before secondary errors — reassessed remaining errors after rebuild
- [ ] Fix is committed with `Fixed:` prefix and clear description
- [ ] One logical change per commit
- [ ] If the error was a new pattern not in references/, added to error-patterns.md and version-diff-guide.md
- [ ] Adaptation reverts stay **local-only** (do NOT push upstream). Genuine bug fixes (engine-version-independent) apply upstream locally too (push is user's call)

After completing a version:
- [ ] Version boundary commit `"Changed: set engine version X.Y"` is present
- [ ] Build passes cleanly for this version
- [ ] Output directory contains built binaries

After completing all versions:
- [ ] All versions build without errors
- [ ] CHANGELOG updated
- [ ] Branch pushed and PR created
- [ ] New error patterns documented in references/ for future cycles
- [ ] Archive packaging (Step 5) only performed with explicit user authorization
