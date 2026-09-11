# Localization Pipeline Details

Companion to `rem-ue-localization` §4. Last verified: 2026-09, UE 5.8.

## 1. Config format

A gather config is one ini with a `[CommonSettings]` section plus ordered
`[GatherTextStepN]` sections; each step names a commandlet class via
`CommandletClass=`. Paths are relative to the project directory, or absolute via the
`%LOCPROJECTROOT%` / `%LOCENGINEROOT%` placeholders.

```ini
[CommonSettings]
SourcePath=<plugin-dir>/Content/Localization/<Target>
DestinationPath=<plugin-dir>/Content/Localization/<Target>
ManifestName=<Target>.manifest
ArchiveName=<Target>.archive
PortableObjectName=<Target>.po
ResourceName=<Target>.locres
NativeCulture=en
CulturesToGenerate=en
CulturesToGenerate=<Culture>

; source strings (LOCTEXT / NSLOCTEXT), including editor-only blocks
[GatherTextStep0]
CommandletClass=GatherTextFromSource
SearchDirectoryPaths=<plugin-source-dir>/
FileNameFilters=*.cpp
FileNameFilters=*.h
ShouldGatherFromEditorOnlyData=true

; reflected metadata the editor displays (namespaces and key shapes must match the engine)
[GatherTextStep1]
CommandletClass=GatherTextFromMetaData
ModulesToPreload=<ModuleName>
IncludePathFilters=%LOCPROJECTROOT%<plugin-source-dir>/*
ExcludePathFilters=*/ThirdParty/*
InputKeys=Category
OutputNamespaces=UObjectCategory
OutputKeys="{MetaDataValue}"
InputKeys=DisplayName
OutputNamespaces=UObjectDisplayNames
OutputKeys="{FieldPath}"
InputKeys=ToolTip
OutputNamespaces=UObjectToolTips
OutputKeys="{FieldPath}"
InputKeys=ShortTooltip
OutputNamespaces=UObjectShortTooltips
OutputKeys="{FieldPath}"
ShouldGatherFromEditorOnlyData=true

[GatherTextStep2]
CommandletClass=GenerateGatherManifest

[GatherTextStep3]
CommandletClass=GenerateGatherArchive
bPurgeOldEmptyEntries=true
```

The remaining stages are separate configs with the same `[CommonSettings]`:

```ini
; _Import.ini  — merge the translated .po files into the archive
[GatherTextStep0]
CommandletClass=InternationalizationExport
bImportLoc=true

; _Compile.ini — archive -> .locres + .locmeta
[GatherTextStep0]
CommandletClass=GenerateTextLocalizationResource
ResourceName=<Target>.locres

; _Export.ini  — archive -> .po (also refreshes the source texts after a gather)
[GatherTextStep0]
CommandletClass=InternationalizationExport
bExportLoc=true
```

The engine's own targets are usable as templates:
`Engine/Config/Localization/{Category,ToolTips,PropertyNames,Editor}.ini`. Their metadata
steps carry the canonical namespace/key pairs; a tooltip-less target such as `Category`
shows the `{MetaDataValue}` shape for category keys, `ToolTips.ini` the `{FieldPath}`
shape for tooltips and short tooltips.

## 2. Stage semantics

| Step class | Notes |
|---|---|
| `GatherTextFromSource` | Harvests `LOCTEXT` / `NSLOCTEXT` / `LOCTABLE*` / `UI_COMMAND` / `UE_LOGFMT_LOC`; `#if WITH_EDITOR` blocks only with `ShouldGatherFromEditorOnlyData=true` |
| `GatherTextFromAssets` | Harvests text inside assets; needs package path filters |
| `GatherTextFromMetaData` | Harvests reflected metadata; `IncludePathFilters` match the **source header's absolute path** (resolved through source-code navigation), and the owning modules must be loaded (`ModulesToPreload`) — a binary-only plugin yields nothing |
| `GenerateGatherManifest` / `GenerateGatherArchive` | Write the manifest and the per-culture archives; `bPurgeOldEmptyEntries=true` drops stale entries |
| `InternationalizationExport` | `bExportLoc=true` writes `.po`; `bImportLoc=true` reads them back |
| `GenerateTextLocalizationResource` | Compiles archives into `.locres` and writes `<Target>.locmeta` |
| `GenerateTextLocalizationReport` | Word-count / conflict reports (optional) |

## 3. Commands

```bash
<engine-install-path>/Binaries/<Platform>/UnrealEditor-<Platform>-<Config>-Cmd.exe \
  "<project-dir>/<Project>.uproject" \
  -run=GatherText \
  -config="<plugin-dir>/Config/Localization/<Target>_Gather.ini" \
  -unattended -nullrhi -log
```

| Switch | Effect |
|---|---|
| `-Preview` | Runs the steps without writing the real artifacts (the manifest is written as `<Target>_Preview.manifest`). Implies no SCC submit |
| `-GatherType=All\|Source\|Asset\|Metadata` | Restricts a preview run to one gather kind |
| `-ConfigList=<file>` | Runs several config files listed in a text file |
| `-EnableSCC` / `-DisableSCCSubmit` | Checkout / submit control for the generated files |

Wrapper scripts that run all four stages in order are worth adding next to the configs:
the pipeline is idempotent, so the loop *gather → export → translate → import → compile*
can be re-run wholesale.

## 4. Loading at runtime

| Fact | Source |
|---|---|
| A plugin's data is registered only when its descriptor has `LocalizationTargets`; the path is `<plugin>/Content/Localization/<Name>` | `Runtime/Projects/Private/PluginManager.cpp` |
| Loaded file layout is `<path>/<Culture>/<Target>.locres` (plus an optional platform subfolder); `<path>/<Target>.locmeta` records the native culture and native `.locres` | `Runtime/Core/Private/Internationalization/LocalizationResourceTextSource.cpp` |
| Plugin data joins the load as *additional* paths, after game → editor → engine | same file; broadcast by `FCoreDelegates::GatherAdditionalLocResPathsCallback` |
| Editor-visible metadata resolves through the live display-string table, which a culture change refreshes after reloading every text source | `Runtime/Core/Private/Internationalization/TextLocalizationManager.cpp` |
| Loading policies: `Editor`/`ToolTips` are editor-only; `Always`/`Game` are the only ones staged into packaged builds; `PropertyNames` is gated by an editor preference | `Runtime/Projects/Public/LocalizationDescriptor.h` |
| Conflicts keep the first entry at equal priority, so a plugin cannot shadow an engine or project translation | `Runtime/Core/Private/Internationalization/TextLocalizationResource.cpp` |

## 5. Who defines what

| Concern | Owner |
|---|---|
| Plugin target + shipped data | the plugin (`.uplugin` + `Content/Localization`) |
| Project target (game/editor text, asset text) | the project's localization settings and dashboard |
| Gather configs for a plugin target | hand-written; the engine's dashboard manages project targets only |
| Translation content | the `.po` files; the manifest is an input for external pipelines (see `rem-ue-localization` §7) |
