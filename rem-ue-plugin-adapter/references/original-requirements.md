# Original Requirements — Multi-Engine Plugin Adaptation

> Captured from initial design discussion on 2026-07-28.
> This document preserves the original workflow vision as the user described it
> before the pivot to a skill-based AI-driven approach.

---

## Scenario

A developer maintains a UE marketplace plugin that must support engine versions
5.3 through 5.8. The plugin source lives in an upstream repository. A separate
**build repository** is used for multi-engine adaptation — it contains the
upstream code plus embedded dependencies plus version-specific adaptation
commits.

The adaptation cycle repeats whenever the upstream plugin receives significant
updates that should propagate to all supported engine versions.

---

## Original Workflow (User's Description)

### Step 0 — Context

- There is a **dedicated build directory** containing a git repository for
  plugin adaptation
- The repository's current branch represents the last completed adaptation
  cycle
- The branch includes: upstream sync commit → 5.7 adaptations → 5.6
  adaptations → ... → 5.3 adaptations
- **Upstream** is the pure plugin source — it cannot depend on other plugins
  (marketplace binary independence constraint)
- Dependent plugins must be **copied into** the plugin as embedded modules,
  and their external dependency declarations removed

### Step 1 — Branch Management

1. Rename current branch to `old-<something>`
2. Checkout `upstream/main` latest commit (to get the newest plugin code)
3. This ensures all engine versions benefit from the latest changes and
   optimizations

### Step 2 — Dependency Resolution

1. Copy dependent plugin source code into the plugin directory as embedded
   modules
2. Delete dependency declarations from `.uplugin`'s `"Plugins"` array
3. Reference: look at the old adaptation branch to see how this was done
   before

### Step 3 — Cascade Adaptation (High to Low)

Process engine versions from **highest to lowest**:

#### 3a. Cherry-pick base adaptations

For the newest version (e.g., 5.8):
- Cherry-pick commits between "upstream sync" and "set engine version 5.7"
  from the old branch
- These are base adaptation commits common to all versions

For subsequent versions (e.g., 5.7 → 5.6 → 5.5 → ...):
- Cherry-pick commits between version boundaries
  (e.g., "set engine version 5.7" .. "set engine version 5.6")

**Commit identification approaches under consideration:**
- **Option A**: Identify by commit message prefix (`Fixed:`, `Changed:`)
  and version boundary markers
- **Option B**: Configuration file with SHA1 ranges per version
- **Option C**: Auto-infer from git log patterns

#### 3b. Update embedded dependencies

- **Delete** old embedded dependency directories first (prevents stale files)
- **Copy** latest dependency source into place
- Commit the update

> Explicit distinction: this is *replacement* (delete + copy), not *overlay*
> (copy over). This ensures files removed from the dependency don't persist as
> stale artifacts.

#### 3c. Commit version boundary

```
git commit --allow-empty -m "Changed: set engine version 5.8"
```

#### 3d. Build-Fix-Commit Cycle

```
loop:
  1. Build the plugin with the current engine version
  2. If build passes → proceed to next version (3e)
  3. Read compilation errors
  4. Fix errors (one logical fix at a time)
  5. git commit each fix ("Fixed: ...")
  6. Go to 1
```

#### 3e. Move to next version

Return to 3a for the next lower engine version.

### Step 4 — Final Verification

- All 6 engine versions (5.3–5.8) build successfully
- Run automated tests if available
- Update CHANGELOG
- Push and create PR/Release

---

## Design Evolution

| Date | Decision |
|------|----------|
| 2026-07-28 | Initial: parameterize the build script for multi-version support |
| 2026-07-28 | Expand: Python rewrite, configuration-driven, auto-fixer |
| 2026-07-29 | Pivot: replace rule-based auto-fixer with **skill-guided AI workflow** |

### Rationale for Skill-Based Approach

The original vision included a rule-based auto-fixer (`fix_rules.json` +
`auto_fixer.py`) that would match error patterns and apply fixes automatically.
This was reconsidered because:

1. **Fix diversity**: UE cross-version errors are too varied for a rule engine
   — they require context understanding (what is this code trying to do? what
   alternatives exist in the older engine?)
2. **Maintenance burden**: Each new error type requires writing and testing a
   new rule
3. **AI advantage**: An AI coding agent can read error logs, understand code
   context, search engine sources for alternatives, and apply nuanced fixes
   that a rule engine cannot

The skill approach preserves the **fixed infrastructure** as tools (build
script, engine config) and delegates the **intelligent decisions** to the AI,
guided by documented patterns and conventions.

---

## Key Constraints

1. **Marketplace binary independence**: Plugins cannot declare external
   dependencies. All dependencies must be embedded.
2. **No shared plugin dependencies**: The built plugin binary must be
   self-contained.
3. **Git history must be bisectable and cherry-pickable**: One logical change
   per commit, clear commit message prefixes.
4. **Version boundaries are explicit**: Empty commits mark where one engine
   version's adaptations end and the next begins.
5. **Oldest supported version determines compatibility floor**: The plugin
   must compile and function on 5.3, which constrains what language features
   and APIs can be used.

---

## Open Questions

### Resolved

| # | Question | Decision | Date |
|---|----------|----------|------|
| 1 | Cherry-pick range identification | **Option A** — commit message convention (`Changed: set engine version X.Y` as boundary markers). No config file needed. | 2026-07-29 |
| 2 | Cherry-pick conflict handling | AI tries correct resolution first. Conflicts involving stale embedded dependency code → skip that commit, let build-fix loop handle. Unresolvable conflicts → manual merge as last resort. | 2026-07-29 |

### Pending

*All questions resolved as of 2026-07-29.*

| # | Question | Decision | Date |
|---|----------|----------|------|
| 3 | Cross-version fix isolation | **Option C** — accept cross-version commits. When a fix for version N causes issues in version N-1, go back and adjust the N-level fix, then re-adapt for N-1. Git history may have "Fixed: adjust X.X fix for X.X-1 compatibility" commits. | 2026-07-29 |
| 4 | Final verification strategy | **Incremental trust** — each version's build result at the time it passed is trusted. No mandatory full rebuild of all versions in Step 4. Rebuild only if there's reason to suspect breakage. | 2026-07-29 |
| 5 | Minimum version compatibility break | **A-first, B-fallback** — if upstream uses an API only available in a newer engine, attempt to backport/copy the self-contained API code to the plugin for older versions (viable if small, e.g., a few files). If the API surface is too large, disable the feature on the older version with `#if 0` and document the limitation. | 2026-07-29 |
| 6 | Embedded dependency version adaptation | **Currently A, may switch to B** — embedded dependencies are adapted as part of this workflow (build-fix cycle includes their code). In the future, dependencies may maintain their own multi-version compatibility via `#if` guards, at which point the adaptation workflow would only copy without modifying. | 2026-07-29 |
