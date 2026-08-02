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
  category: workflow
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
**names** to embed come from `adapt_config.json` in the build repo root; the
template for that file ships as `tools/adapt_config.json` in this skill folder —
copy it to the build repo root and fill in the dependency names and cherry-pick
ranges on first use.

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

The build repo is a generated tree — its contents are copied from the plugin
source or produced by the tools, so staging it wholesale is safe *here*. That
is the stated exception to `rem-commit-workflow`'s "stage by exact path" rule,
which applies to the project repository.

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

The core loop: build → read the first error → decide (fix code / fix build settings / adapt API) → commit → rebuild. One logical fix per commit so the adaptation history stays bisectable; never batch unrelated compile errors into one commit.

The full loop, error triage table and worked examples: `references/build-fix-loop.md`.

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

Manual, user-authorized step: package the adapted plugin into a release archive (version folder layout, per-engine subfolders, exclusions). Never run it unattended — it writes outside the working tree.

Procedure, layout and the exact exclusions: `references/archive-packaging.md`.

---

## 9. Git Conventions

### Branch naming

```
adapt-<lowest-version>-to-<highest-version>
```

Example: `adapt-5.3-to-5.8`

### Commit message prefix

The accepted types are owned by `rem-commit-workflow` (`New`, `Changed`,
`Improvement`, `Removed`, `Fixed`, `Misc`) — do not invent variants. Which one
fits an adaptation step:

| Prefix | Adaptation step |
|--------|-----------------|
| `Fixed:` | Fixing a compilation error for a specific engine version |
| `Changed:` | Deliberate adaptation: version boundary, dependency update, feature revert, config change |
| `New:` | Adding new capability (rare in adaptation) |
| `Improvement:` | Enhancing existing code without fixing a bug |
| `Misc:` | Cleanup, formatting, non-functional |

### Commit granularity

**One logical change per commit** — the rule and its rationale are owned by
`rem-commit-workflow`. It matters most here: bisectable, cherry-pickable
history is what makes the next adaptation cycle cheap. Do NOT batch unrelated
fixes into one commit.

---

## 10. Tool Reference

The helper scripts and their arguments (config resolution, per-plugin `local.json`, error-out-when-missing behaviour). Tool tables and invocation examples: `references/tools.md`.

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
- **Upstream sync decisions** — classify every adaptation change before
  syncing back:
  | Category | Examples | Sync? |
  |----------|----------|-------|
  | Generic compile/logic fixes (engine-version-independent) | `return {}` → explicit-type construct (Clang) | ✅ yes |
  | Compiler-compat fixes the upstream toolchain does not need | `FMT_APPLY_VARIADIC` fold rewrite (MSVC 14.38 issue; upstream builds with newer MSVC) | ❌ no — unless upstream actually hits the same toolchain |
  | Marketplace/Fab-only requirements | fmt trimmed to `include/`, `PlatformAllowList`, shadow-warning downgrade | ❌ no |
  | Version-specific compatibility (backports) | FUtf8String/TNotNull/StructViewCompat backports, `IsPendingDisable` exposure, `Modulo` wrapper | ❌ no (single-version upstream has no use) |
  | Shared build-rule/version-branching logic | `RemSharedModuleRules` engine-version branches | ❌ no |
  Ask the user for the upstream toolchain/scope before syncing compiler-related
  fixes; when in doubt, record the decision in the plugin's adaptation notes.

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

---

## Reference files

| File | When to load |
|------|--------------|
| `references/build-fix-loop.md` | Running the build-fix loop; triaging a compile error |
| `references/error-patterns.md` | Hitting an error that may already be documented |
| `references/version-diff-guide.md` | Adapting an API that changed between engine versions |
| `references/tools.md` | Invoking the helper scripts; config resolution |
| `references/archive-packaging.md` | Performing Step 5 archive packaging |
| `references/original-requirements.md` | Original requirements behind these rules |
