---
name: rem-ue-localization
description: >
  Unreal Engine localization for plugins and projects: localization targets and their
  loading policies, the namespace+key lookups behind editor-visible text (details-panel
  categories, tooltips, display names, code strings), the gather → translate → compile
  pipeline (gettext .po to .locres), and how to verify a language switch. Use when adding
  a language to a UE plugin or project, when a translation does not appear in the editor,
  or when a plugin must ship translated text.
metadata:
  category: workflow
  trigger: manual
---

# UE Localization

Last verified: 2026-09, UE 5.8. Engine paths are relative to the engine root.

## Local overlay

Machine-local values for this skill live in `local/` next to this file: git-ignored, created as
symlinks into a private repository that tracks them - never committed here. Files this skill reads
when present:

- `local/project-localization.md` - real paths, verified commands, pilot results, project trade-offs

A file in `local/` takes precedence over `references/` and over the generic rules below; this
`SKILL.md` stays the only source of the skill's instructions, and local files carry values or
configuration only. When `local/` is absent, follow the generic rules.

## 1. Scope

| In scope | Out of scope |
|---|---|
| Editor-visible text: details-panel categories, tooltips, display names, notifications | Log / assert / cvar text — developer-facing English (`rem-observability-and-profiling`) |
| Text data plumbing: targets, gather configs, `.po`, `.locres` | Asset-content translation as a design task |
| Making a language switch verifiable | Vendor / TMS contracts — see §8 for the escalation threshold |

## 2. The lookup model

Text is resolved by **namespace + key** when it is displayed, never by the literal written
in the declaration:

| Displayed as | Namespace | Key | Source |
|---|---|---|---|
| Details-panel category | `UObjectCategory` | the raw `Category` metadata string | `Engine/Source/Runtime/Engine/Private/ObjectEditorUtils.cpp` |
| Tooltip | `UObjectToolTips`, `UObjectShortTooltips` | field path | `Engine/Source/Runtime/CoreUObject/Private/UObject/Class.cpp` |
| Display name | `UObjectDisplayNames` | field path | `Engine/Source/Runtime/CoreUObject/Private/UObject/Class.cpp` |
| A code string | the `LOCTEXT` / `NSLOCTEXT` namespace | that call's key | `Engine/Source/Editor/UnrealEd/Private/Commandlets/GatherTextFromSourceCommandlet.cpp` |

Consequences:

- A translation appears only when a **loaded** resource holds that namespace+key. The
  engine ships translations for its own tree — never for a plugin's classes.
- Metadata is translatable **without code changes**: the literal stays in the declaration
  and a compiled resource overrides the display. Prefer that over an asset string table
  for metadata.
- Tooltips are derived from doc comments: UHT stores `/** ... */` above a declaration as
  `ToolTip` metadata, so an undocumented declaration with an adjacent `//` comment can
  surface that comment as its tooltip. Authoring rules live in `rem-cpp-best-practices`
  §4; the data-side symptom is in `references/pitfalls.md`.

## 3. Targets and loading

| | Plugin target | Project target |
|---|---|---|
| Declared in | `<plugin>.uplugin` → `LocalizationTargets` | project localization settings |
| Fields | `Name`, `LoadingPolicy`, `ConfigGenerationPolicy` | target settings |
| Data at | `<plugin-dir>/Content/Localization/<Name>/<Culture>/<Name>.locres` | `<project>/Content/Localization/<Target>/<Culture>/<Target>.locres` |
| Discovered by | the plugin manager, for enabled plugins whose target list is non-empty | the project's localization paths |

| `LoadingPolicy` | Loads when |
|---|---|
| `Editor` | editor builds only — the default choice for editor-facing text, and it keeps the data out of packaged builds |
| `Always` / `Game` | always / in game; the only policies staged into packaged builds |
| `PropertyNames` | only while the editor preference "use localized property names" is enabled |
| `ToolTips` | editor builds, like `Editor` |

Rules:

1. **Declare the target, or nothing loads.** An empty `LocalizationTargets` list makes the
   plugin's data invisible — silently, with no error anywhere.
2. **Ship `.locres` + `.locmeta`; treat `.manifest`/`.archive` as regenerable
   intermediates** — commit them only when an external pipeline consumes the manifest as
   its source of truth (§8).
3. **Use culture tags the engine ships data for** — script subtags such as `zh-Hans`, not
   legacy forms such as `zh-CN` — and always name a native culture.
4. **Verify the culture actually resolves** before blaming the data: the command line
   (`-culture=<Culture>`) or the editor's language preference, with a project-level
   override only when pinning the language is intended (`LockLocalization`).

## 4. The pipeline

Four stages, expressed as `[GatherTextStepN]` sections of one config (or split per stage):

| Stage | Effect |
|---|---|
| gather | source strings + assets + reflected metadata → `manifest`, per-culture `archive` |
| export | `archive` → `<Culture>/<Target>.po` (the translator-facing file) |
| *translate* | edit the `.po` |
| import | `.po` → `archive` |
| compile | `archive` → `<Culture>/<Target>.locres` + `<Target>.locmeta` |

- Drive it with `-run=GatherText -config=<config.ini>`; `-Preview` validates a config
  without writing the real artifacts (it still writes `<Target>_Preview.manifest`).
- **Hand-write the config when metadata matters.** The config that the engine's UAT
  generator produces for a target whose loading policy is not `ToolTips`/`PropertyNames`
  contains no metadata step, so categories and tooltips would be gathered from nowhere.
- **Rebuild before gathering.** UHT bakes metadata (and therefore comment-derived
  tooltips) into the module at compile time; a comment-only edit is invisible to a gather
  until the module is rebuilt.

Config format, per-stage keys, commands and the runtime loading mechanics:
`references/pipeline.md`.

## 5. Rules that keep the data correct

| Rule | Why |
|---|---|
| Translate a `\|`-separated category **as one key** | The sub-category node displays the last `\|`-separated segment of the *translated* string culture-invariantly, so the whole path is the key and its leaf must read standalone |
| A translation identical to its source is ignored | The lookup treats it as untranslated and falls back to prettifying the identifier — the entry achieves nothing |
| Untranslated entries are acceptable | They resolve to the native text, so translation can proceed incrementally with no blank UI |
| Do not translate logs, asserts, cvars | They are developer-facing (`rem-observability-and-profiling`) |
| Keep `.po` edits mechanical | `msgstr` stays on one line and quoted; multi-line text uses `\n` escapes, or the import step fails outright |
| Never judge a `.locres` by a whole-file text scan | Keys and values mix encodings inside the file; decoding it as one blob produces false negatives — parse it or ask the runtime |
| Conflicts resolve by load order, not by "latest wins" | Equal-priority resources keep the first loaded (game → editor → engine → plugin), so engine and project translations are not shadowed by a plugin's untranslated entries |

## 6. Committing the data

The engine loads `.locres` / `.locmeta` at runtime, so the compiled data has to reach
whoever consumes the plugin. Two shapes are valid — pick by how it is delivered:

| Delivery | Shape |
|---|---|
| Consumers clone the repository, or take an archive of it (zip, download) | commit the compiled data — they cannot run the pipeline themselves |
| Consumers get a package built where the engine is available (marketplace upload, CI artifact) | **do not commit it**: the repository keeps `.po` + configs, and the packaging step generates the data (a release-checklist line, plus the generated paths in `.gitignore`) |

The `.po` is always committed: it is the source of truth and the review surface. When the
compiled data *is* committed, keep the repository reviewable:

| Artifact | Commit shape | Why |
|---|---|---|
| `.po` (and gather configs) | with the change that produced them, as text | it is the source of truth and the only reviewable diff of a translation change |
| `.locres` / `.locmeta` | **one data-only commit per translation update** | binaries cannot be diffed or merged; keeping them out of every other commit leaves the binary with no history of its own |
| `.manifest` / `.archive` | not committed (regenerated) unless an external pipeline consumes the manifest | pipeline intermediates (see §3.2) |

Rules:

1. **Keep the binary out of the working commits.** Stage by exact path and add the data
   commit last; a binary that changes in several commits of one update cannot be reviewed,
   and it makes rebases and merges unresolvable.
2. **Resolve a translation conflict by regenerating, not by merging.** Re-run the pipeline
   for the affected cultures and commit the result as the data commit.
3. **Retro-fit the shape before pushing, not after.** An un-pushed range that scattered the
   binary can be rebuilt: drop the binary path from every commit (`git rm --cached`) and
   add one data commit — following `rem-rewrite-commit-history` (its rebuild recipe, its
   tree-identity check and its no-pruning rule). If the decision is "do not commit it"
   (§6 above), the same rebuild drops the data commit instead, and the generated paths move
   to `.gitignore`.
4. **Mark the binaries as generated** in `.gitattributes` (`-diff linguist-generated`) so a
   reviewer is pointed at the `.po` diff instead of "binary file changed".
5. **A packaging-time generation is a release step, not free**: whoever builds the drop must
   run the pipeline (engine + the plugin at its expected path) before packaging, or the
   package ships English.

## 7. Verification

| Level | How |
|---|---|
| Data | Parse the compiled `.locres` and assert the expected namespace+key carries the translation. A small reader following `FTextLocalizationResource::LoadFromArchive` is enough — validate it against an engine-shipped `.locres` first |
| Runtime | An automation spec that switches the culture and asserts through the same entry points the editor uses: `FObjectEditorUtils::GetCategoryText` for categories, the live display-string lookup for tooltips/display names/source strings. A culture switch reloads every text source (plugin targets included) and refreshes the live table, so no restart is needed |
| Visual | Switch the editor's language preference and look at the panel — the shortest path to "does it really show" |

## 8. Tooling escalation

| Stage | Tooling | Escalate when |
|---|---|---|
| One language, one translator | `.po` in the repo + a PO editor | — |
| Consistency across a codebase | a term list next to the data | two or more modules/plugins share vocabulary |
| Several translators, or ≥3 languages | a gettext-native web TMS | translators do not use git, or review/QA is required |
| Community translation | a public TMS project | the repository is public and the string surface is stable |

The interchange format is gettext `.po` with `msgctxt`; the stock pipeline has no XLIFF
path, so a TMS must speak gettext (or a conversion step is required). Commit the manifest
only once such a pipeline consumes it (§3.2).

## Reference files

| File | When to load |
|---|---|
| `references/pipeline.md` | Writing or repairing a gather config, running the stages, understanding how the data is loaded at runtime |
| `references/pitfalls.md` | A translation does not appear, data will not load, or a toolchain step failed |

## Cross-references

- `rem-cpp-best-practices` — comment discipline (doc comments become tooltips), `ForceUnits`, metadata completeness
- `rem-observability-and-profiling` — what stays developer-facing English
- `rem-test-completeness` — the pre-commit test gate for a localization change
- `rem-commit-workflow` — committing the data, the configs and the spec

## Checklist

Before shipping a localization change:

- [ ] Target declared (`LocalizationTargets`, with a `LoadingPolicy` that fits the audience) and the data at the exact `<Target>/<Culture>/<Target>.locres` path
- [ ] Culture list uses engine-shipped subtags and names a native culture; the culture resolves at runtime
- [ ] The gather config covers every text kind in play: source strings, metadata with engine-matching namespaces/keys, assets when they carry text
- [ ] Metadata gathered after a rebuild; `ModulesToPreload` and source-path filters confirmed by a preview run
- [ ] `.locres` + `.locmeta` shipped; intermediates either regenerable or committed deliberately for an external pipeline
- [ ] Categories translated as whole `|` paths; no translation equal to its source
- [ ] Logs, asserts and cvars left in English
- [ ] `.po` edits single-line/escaped; import and compile re-run after editing
- [ ] Compiled `.locres`/`.locmeta` either committed deliberately (one data-only commit per update, marked generated) or generated by the packaging step — the `.po` is the diff a reviewer reads
- [ ] Verified at data level and/or by a culture-switching spec, through the editor's own lookup entry points
- [ ] Compile and the project's test suite run after the change
