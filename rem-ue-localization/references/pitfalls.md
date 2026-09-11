# Localization Pitfalls

Companion to `rem-ue-localization`. Each entry: symptom → cause → fix → verification.
Last verified: 2026-09, UE 5.8.

## `LocalizationTargets` missing → the data is never loaded (verified 2026-09)

- **Symptom** — a plugin ships a valid `.locres` and the editor still shows English; no
  error, no warning anywhere.
- **Cause** — plugin localization data is registered from the descriptor's target list
  only; an empty list makes the plugin's `Content/Localization` invisible.
- **Fix** — declare the target in the `.uplugin` (`Name`, `LoadingPolicy`,
  `ConfigGenerationPolicy`) and keep the data at
  `Content/Localization/<Name>/<Culture>/<Name>.locres`.
- **Verification** — the data directory appears in the localization load paths, or a
  culture-switching spec resolves a known key.
- **Applies to** — all UE 5.x (`Runtime/Projects/Private/PluginManager.cpp`).

## A comment-only edit does not change the gathered tooltip (verified 2026-09)

- **Symptom** — after editing a doc comment the manifest/`.po` still carries the old
  tooltip (or a tooltip that was deleted).
- **Cause** — metadata, including the comment-derived `ToolTip`, is baked into the module
  by UHT at compile time; the gather reads the loaded module, not the sources on disk.
- **Fix** — rebuild the target, then gather.
- **Verification** — the regenerated manifest contains the new string and no longer
  contains the removed one.
- **Applies to** — all UE 5.x.

## Categories and tooltips are missing from the manifest (verified 2026-09)

- **Symptom** — source strings are gathered, `UObjectCategory` / `UObjectToolTips`
  entries are not.
- **Cause** — the source gatherer does not read metadata, and the config the engine's UAT
  generator produces for a target whose loading policy is not `ToolTips`/`PropertyNames`
  has no metadata step at all.
- **Fix** — add a `GatherTextFromMetaData` step with the engine-matching namespace/key
  pairs (`UObjectCategory` + `{MetaDataValue}`, the others `{FieldPath}`); use the
  engine's own `Category.ini` / `ToolTips.ini` as the template.
- **Verification** — the manifest lists the expected namespaces with plausible counts.
- **Applies to** — all UE 5.x; the UAT generator behaviour is visible in
  `Programs/AutomationTool/Localization/LocalizationConfigFileGenerator.cs`.

## Metadata gathering finds zero fields (verified 2026-09)

- **Symptom** — the metadata step runs and produces nothing.
- **Cause** — `IncludePathFilters` are matched against the **source header's absolute
  path** (resolved through source-code navigation), and the owning modules must already be
  loaded; a binary-only plugin or a filter that does not match the header path yields
  nothing.
- **Fix** — filter on the source tree (`%LOCPROJECTROOT%<plugin-source-dir>/*`) and list
  the modules in `ModulesToPreload`.
- **Verification** — the manifest contains the metadata namespaces with entries; a preview
  run reports the gathered counts.
- **Applies to** — all UE 5.x
  (`Editor/UnrealEd/Private/Commandlets/GatherTextFromMetadataCommandlet.cpp`).

## A sub-category node still shows English (verified 2026-09)

- **Symptom** — the top-level details category is translated, its nested sub-category is
  not.
- **Cause** — a nested category node displays only the last `|`-separated segment of the
  translated path, culture-invariantly; translating a leaf (or a word inside the path)
  does not produce a node translation.
- **Fix** — translate each `A|B` path as a single key, keeping the leaf readable
  standalone (`<...>|Data` style leaves are the display text).
- **Verification** — every distinct `Category` metadata string of the module has a
  translation entry.
- **Applies to** — all UE 5.x (`Editor/PropertyEditor/Private/CategoryPropertyNode.cpp`).

## A translation is ignored although it is present (verified 2026-09)

- **Symptom** — the `.locres` contains an entry for the key, the UI still shows English.
- **Cause** — a translation equal to the source string is treated as untranslated (the
  lookup falls back to prettifying), and a source-string hash mismatch defeats the lookup
  entirely.
- **Fix** — never write an entry whose translation equals its source; re-gather after a
  string changes instead of editing only the translation.
- **Verification** — the lookup returns the translated text for the same source hash that
  the gather produced.
- **Applies to** — all UE 5.x.

## The preview run leaves a file behind (verified 2026-09)

- **Symptom** — a `*_Preview.manifest` file appears in the data directory after a
  "no-write" preview run.
- **Cause** — preview skips the real artifacts but still writes the manifest with a
  `_Preview` suffix.
- **Fix** — ignore `*_Preview.manifest` in version control, or delete it after the run.
- **Verification** — `git status` stays clean after a preview.
- **Applies to** — all UE 5.x.

## A legacy culture tag has no data (verified 2026-09)

- **Symptom** — the editor language is selectable but strings stay English; the shipped
  engine data has no such culture.
- **Cause** — legacy tags such as `zh-CN` no longer match the shipped script-subtag
  directories (`zh-Hans`), while some engine ini files still list the legacy form.
- **Fix** — use the script-subtag culture names consistently in the configs and in the
  language preference.
- **Verification** — the culture folder exists in the target's data directory.
- **Applies to** — UE 5.x with script-subtag cultures.

## Untranslated entries appear in the compiled `.locres` (verified 2026-09)

- **Symptom** — the compiled localized file has roughly the size of the native one and
  contains source-language values for untranslated keys.
- **Cause** — entries whose resolved translation differs from the source are all written;
  an archive round-trip can leave the source text as the translation.
- **Fix** — harmless for display (the values equal the native text) and for conflicts
  (equal priority keeps the first loaded resource, and plugin data loads last); translate
  the entries you care about and ignore the rest.
- **Verification** — the engine's or project's translation for the same key still wins in
  the UI; a development build may log a translation conflict for such keys.
- **Applies to** — all UE 5.x (`Runtime/Core/Private/Internationalization/TextLocalizationResource.cpp`).

## The import stage fails outright (verified 2026-09)

- **Symptom** — the import step exits non-zero, translations are not applied, and the
  compiled resource keeps the previous translations.
- **Cause** — the hand-edited `.po` is malformed: a `msgstr` written across real newlines,
  an unescaped quote, or a missing terminator.
- **Fix** — keep every `msgstr` on one line with a closing quote and express line breaks
  as `\n` escapes; re-import and re-compile afterwards.
- **Verification** — the import step exits 0 and a parsed `.locres` shows the new values.
- **Applies to** — all UE 5.x.

## A whole-file text scan reports a translation as missing (verified 2026-09)

- **Symptom** — searching a `.locres` for a known translation finds nothing (or only
  some of them), while the runtime resolves them fine.
- **Cause** — keys and values mix encodings inside the file, so decoding the whole file as
  one UTF-16 (or UTF-8) blob loses alignment and silently drops matches.
- **Fix** — parse the file (a reader following `FTextLocalizationResource::LoadFromArchive`
  is ~60 lines) or assert through the runtime; validate the reader against an
  engine-shipped `.locres` first.
- **Verification** — the parser reproduces a known engine translation, then reports the
  expected counts for the target.
- **Applies to** — all UE 5.x (optimized `.locres` formats).

## A comment leaks into a tooltip (verified 2026-09)

- **Symptom** — the details panel shows text such as `, Meta = (ForceUnits = "%")` or
  `#if <MACRO>` as a tooltip.
- **Cause** — UHT collects the comment next to a declaration (including an inline comment
  inside the specifier list, or a bare `//` line) as `Comment` metadata, and the tooltip
  falls back to it when the declaration has no doc comment.
- **Fix** — express the intent as real metadata and give the declaration a doc comment;
  never park specifier text or preprocessor lines in a comment next to a declaration.
  Authoring rules: `rem-cpp-best-practices` §4.
- **Verification** — no property tooltip of the affected types contains specifier text or
  starts with `#` (an automation spec can assert this over a class's fields).
- **Applies to** — all UE 5.x.
