---
name: rem-create-new-module
description: >
  Create a new runtime module or plugin by copying the RemMyBlank template
  and performing keyword substitution. Covers two scenarios: (a) adding a
  module to an existing plugin, and (b) creating a brand-new standalone plugin.
  Use when the user asks to "create a new module" or "create a new plugin"
  using the project's RemMyBlank boilerplate.
metadata:
  category: meta
  trigger: manual
---

# Create new module or plugin from RemMyBlank template

## Overview

The RemMyBlank plugin is the canonical skeleton for any Rem project module. It contains:

- `IRemMyBlankModule` interface (`Get()` / `IsAvailable()`)
- `FRemMyBlankModule final` implementation in `.cpp`
- `RemMyBlankLog.h/.cpp` — log category
- `RemMyBlankStatics.h/.cpp` — Blueprint function library + `Rem::MyBlank` namespace
- `RemMyBlankStat.h/.cpp` — stats group
- `RemMyBlankTags.h/.cpp` — `URemMyBlankTags : URemMetaTags`
- `RemMyBlank.Build.cs` with `RemSharedModuleRules.Apply(this)` and dependency boilerplate

To create a new module, copy the template source directory and replace all
`RemMyBlank` strings with the new module name. For a standalone plugin, also
copy and rename the `.uplugin` descriptor.

---

## Scenario A: Add a module to an existing plugin

The template is at `{RemMyBlankPath}` (typically `<ProjectRoot>/Plugins/Editor/RemMyBlank`).
Locate it with `glob "**/RemMyBlank"` or by asking the user if the project
layout differs.

### Steps

1. **Copy the template module source directory**

   Use `bash` to recursively copy `Source/RemMyBlank` to the target plugin:

   ```
   cp -r {RemMyBlankPath}/Source/RemMyBlank {TargetPluginPath}/Source/{NewModule}
   ```

   On Windows, PowerShell equivalent:
   ```
   Copy-Item -Recurse -LiteralPath "{RemMyBlankPath}/Source/RemMyBlank" -Destination "{TargetPluginPath}/Source/{NewModule}"
   ```

2. **Rename files containing `RemMyBlank` in their name**

   Use `bash` with `find` + `mv` (works on Linux/macOS/Git Bash on Windows):

   ```bash
   cd {TargetPluginPath}/Source/{NewModule}
   find . -type f -name '*RemMyBlank*' | while read -r f; do
     mv "$f" "$(echo "$f" | sed 's/RemMyBlank/{NewModule}/g')"
   done
   ```

   Or use the `glob` tool to list files, then `bash mv` for each.

3. **Replace `RemMyBlank` and `REMMYBLANK` in all file contents**

   Use `bash` with `sed`:

   ```bash
   cd {TargetPluginPath}/Source/{NewModule}
   find . -type f | while read -r f; do
     sed -i 's/RemMyBlank/{NewModule}/g' "$f"
     sed -i 's/REMMYBLANK/{NEWMODULE}/g' "$f"
   done
   ```

   On macOS, `sed -i ''` instead of `sed -i`.

   If `sed` is unavailable, use the `edit` tool with `replaceAll: true` on each
   file found by `glob`.

   **Case-sensitive substitution table:**

   | Pattern | Replacement | Applies to |
   |---------|-------------|------------|
   | `RemMyBlank` | `{NewModule}` | Class names, file names, module name, namespace, log category, stat group, config name |
   | `REMMYBLANK` | `{NEWMODULE}` | `*_API` export macro, `#define REM_API REMMYBLANK_API` |

4. **Register the module in the plugin's `.uplugin`**

   Use `edit` to add a module entry to `{TargetPluginPath}/{TargetPlugin}.uplugin`
   inside the `"Modules"` array:

   ```json
   {
       "Name": "{NewModule}",
       "Type": "Runtime",
       "LoadingPhase": "Default"
   }
   ```

5. **Verify the `REM_API` alias**

   Confirm every public header has `#define REM_API {NEWMODULE}_API` with the
   correct uppercase module name. UBT auto-generates `{ModuleName}_API`.

---

## Scenario B: Create a brand-new plugin

Same as Scenario A, plus:

1. **Copy the entire RemMyBlank plugin directory**

   ```
   cp -r {RemMyBlankPath} {TargetPluginDir}/{NewPlugin}
   ```

2. **Rename `RemMyBlank.uplugin` to `{NewPlugin}.uplugin`**

3. **Rename the module source directory `Source/RemMyBlank` to `Source/{NewModule}`**

4. **Run the same keyword replacements** across the entire plugin directory
   (both file names and content).

5. **Edit the `.uplugin` descriptor** — update `"FriendlyName"`, `"Category"`,
   and the `"Modules"` `"Name"`. Ensure `"Plugins"` lists any dependencies the
   module requires.

---

## Post-creation checklist

- [ ] `IMPLEMENT_MODULE(F{NewModule}, {NewModule})` uses the correct name
- [ ] `LoadModuleChecked<IRem{NewModule}>("{NewModule}")` string matches
- [ ] `REM_API` alias points to `{NEWMODULE}_API` — `#define REM_API {NEWMODULE}_API`
- [ ] `Rem::{NewModule}` namespace exists in `*Statics.h`
- [ ] `Log{NewModule}` log category is consistent (declare + define)
- [ ] `STATGROUP_{NewModule}` matches across `*Stat.h`
- [ ] `Config = {NewModule}Tags` matches the `*Tags.h` class
- [ ] Module is registered in `.uplugin` `"Modules"` array
- [ ] Build.cs dependencies include all required modules

---

## Module file structure reference

Every public header uses `REM_API` (aliased to `{NEWMODULE}_API`):

| File | Purpose | Key includes |
|------|---------|-------------|
| `*Module.h` | `IModuleInterface` subclass | `Modules/ModuleInterface.h` |
| `*Log.h` | `DECLARE_LOG_CATEGORY_EXTERN` | `Logging/LogMacros.h`, `Macro/RemMacroUtilities.h` |
| `*Statics.h` | `UBlueprintFunctionLibrary` + `Rem::` namespace | `Kismet/BlueprintFunctionLibrary.h`, `UE_INLINE_GENERATED_CPP_BY_NAME` |
| `*Stat.h` | `DECLARE_STATS_GROUP` | `Stats/Stats.h` |
| `*Tags.h` | `URemMetaTags` subclass | `RemMetaTags.h`, `UE_INLINE_GENERATED_CPP_BY_NAME` |

Corresponding `.cpp` files:
- `*Log.cpp` — `DEFINE_LOG_CATEGORY(Log{NewModule})`
- `*Statics.cpp` — includes `UE_INLINE_GENERATED_CPP_BY_NAME`
- `*Stat.cpp` — includes `*Stat.h`
- `*Tags.cpp` — includes `UE_INLINE_GENERATED_CPP_BY_NAME`
