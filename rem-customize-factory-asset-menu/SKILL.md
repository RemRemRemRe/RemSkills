---
name: rem-customize-factory-asset-menu
description: >
  Place a custom UFactory in specific categories and sub-menus of the Content
  Browser's "Add / New Asset" menu. Covers the two-tier category system
  (GetMenuCategories bitmask gate + GetAssetMenuPathsForCategory sub-path),
  the relationship between UAssetDefinition, IAssetTypeActions, and UFactory,
  and how to route a factory to a different top-level category than its
  SupportedClass's default. Use when a factory isn't showing in the expected
  menu category, needs to appear in multiple top-level categories, or when
  GetAssetMenuPathsForCategory seems to be ignored.
  Last verified: 2026-07, UE 5.8.
metadata:
  category: meta
  trigger: manual
---

# Customize UFactory placement in the Content Browser asset menu

## Overview

The Content Browser "Add" menu groups factories by **top-level category**
(Gameplay, Cinematics, Basic, etc.), then drills into **sub-menus** within
each category. Both layers must be configured for a factory — missing either
one means the factory either appears in the wrong place or doesn't appear at
all.

---

## The two-tier category system

| Tier | Method | Type | Purpose |
|------|--------|------|---------|
| 1 — Gate | `UFactory::GetMenuCategories()` | `uint32` bitmask | Decides which **top-level** categories the factory participates in |
| 2 — Path | `UFactory::GetAssetMenuPathsForCategory(FName)` | `TArray<FAssetCategoryPath>` | Decides **where** within that category the factory appears (sub-menu, section) |

Both methods are `virtual` and can be overridden.

---

## Tier 1: `GetMenuCategories()` — the bitmask gate

```cpp
// Engine/Source/Editor/UnrealEd/Classes/Factories/Factory.h:168
UNREALED_API virtual uint32 GetMenuCategories() const;
```

Returns a `uint32` bitmask over `EAssetTypeCategories::Type`.

Only factories whose bitmask includes the current category bit will have
`GetAssetMenuPathsForCategory` called for that category.

### Override to add categories

```cpp
// In FooFactory.h
virtual uint32 GetMenuCategories() const override;

// In FooFactory.cpp
uint32 UFooFactory::GetMenuCategories() const
{
    // OR in the extra category you want; keep the parent's existing bits
    return Super::GetMenuCategories() | EAssetTypeCategories::Gameplay;
}
```

### Standard pre-registered categories

Defined in `Engine/Source/Developer/AssetTools/Private/AssetTools.cpp:1414+`:

| Category | Enum value | Default label |
|----------|-----------|---------------|
| Basic | `EAssetTypeCategories::Basic` | "Basic" |
| Gameplay | `EAssetTypeCategories::Gameplay` | "Gameplay" |
| Cinematics | `EAssetTypeCategories::Cinematics` | "Cinematics" |
| Misc | `EAssetTypeCategories::Misc` | "Misc" |

Custom categories can be registered via
`IAssetTools::RegisterAdvancedAssetCategory`.

Default `GetMenuCategories()` behavior, the category-iteration gate, and the
`UAssetDefinition` category source: `references/engine-routing.md`.

---

## Tier 2: `GetAssetMenuPathsForCategory()` — sub-menu routing

```cpp
// Engine/Source/Editor/UnrealEd/Classes/Factories/Factory.h:174
UNREALED_API virtual TArray<FAssetCategoryPath> GetAssetMenuPathsForCategory(
    FName InCategory) const;
```

Called **for every category** where the factory's `GetMenuCategories()`
bitmask matched. The `InCategory` parameter is the display name of the
top-level category (e.g., `"Gameplay"`, `"Cinematics"`), not the enum value.

Returns a list of `FAssetCategoryPath` structs. Each path specifies:

| Field | Type | Purpose |
|-------|------|---------|
| `Category` | `FText` | The top-level category display name (e.g., `EAssetCategoryPaths::Gameplay`) |
| `SubCategory` | `FText` | Label within that category — acts as a section header or sub-menu name |
| `MenuType` | `ECategoryMenuType` | `Section` (collapsible header) or `Menu` (sub-menu entry) |

### Example: route to "Gameplay > Foo" with a section header

```cpp
TArray<FAssetCategoryPath> UFooFactory::GetAssetMenuPathsForCategory(FName) const
{
    static const TArray Categories
    {
        FAssetCategoryPath(EAssetCategoryPaths::Gameplay,
            LOCTEXT("Foo", "Foo"), ECategoryMenuType::Section)
    };
    return Categories;
}
```

Results in the menu: `Add → Gameplay → [Foo heading] → Your Display Name`

### Example: appear in multiple top-level categories with different sub-paths

```cpp
TArray<FAssetCategoryPath> UFooFactory::GetAssetMenuPathsForCategory(FName InCategory) const
{
    if (InCategory == FName(TEXT("Gameplay")))
    {
        static const TArray GameplayPaths
        {
            FAssetCategoryPath(EAssetCategoryPaths::Gameplay,
                LOCTEXT("Foo", "Foo"), ECategoryMenuType::Section)
        };
        return GameplayPaths;
    }
    if (InCategory == FName(TEXT("Cinematics")))
    {
        static const TArray CinematicsPaths
        {
            FAssetCategoryPath(EAssetCategoryPaths::Cinematics)
        };
        return CinematicsPaths;
    }
    return Super::GetAssetMenuPathsForCategory(InCategory);
}
```

Base `GetAssetMenuPathsForCategory()` delegation and the empty-result sub-menu
fallback: `references/engine-routing.md`.

---

## Common pitfalls

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Factory doesn't show in "Gameplay" at all | `GetMenuCategories()` bitmask doesn't include `Gameplay` | Override `GetMenuCategories()` to `\| EAssetTypeCategories::Gameplay` |
| `GetAssetMenuPathsForCategory` override is never called | Same as above — bitmask gate filters it out before path routing | Add the category bit in `GetMenuCategories()` |
| Factory shows in "Cinematics" but you also want it in "Gameplay" | The factory's `SupportedClass`'s `UAssetDefinition` only returns `Cinematics` | Override `GetMenuCategories()` to also OR in `Gameplay` |
| Returned `FAssetCategoryPath` seems ignored | The `Category` field (first arg) doesn't match a registered top-level category name | Use `EAssetCategoryPaths::Gameplay` etc. — these are pre-defined `FText` constants |

---

## Reference files

| File | When to load |
|------|--------------|
| `references/engine-routing.md` | Tracing the routing: the `FindFactoriesInCategory` gate, the default `GetMenuCategories()` / `GetAssetMenuPathsForCategory()` behaviour, the full call chain, the engine source map |
| `references/factory-template.md` | Writing the factory: the complete `UFactory` subclass template |

---

## Checklist

Before considering a factory menu placement complete:

- [ ] `GetMenuCategories()` bitmask includes every top-level category the factory should appear in
- [ ] `GetAssetMenuPathsForCategory()` returns non-empty paths for each category in the bitmask
- [ ] `FAssetCategoryPath` uses pre-defined `EAssetCategoryPaths::Xxx` constants as the `Category` field (not raw strings)
- [ ] `ShouldShowInNewMenu()` returns `true`
- [ ] `GetDisplayName()` returns the desired menu label
- [ ] If the factory creates a known `SupportedClass`, `Super::GetMenuCategories()` already has the base categories — use `|` not `=` to add extra bits
- [ ] Module has `"AssetTools"` in its `.Build.cs` dependency list (for `EAssetTypeCategories` and `FAssetCategoryPath`)
