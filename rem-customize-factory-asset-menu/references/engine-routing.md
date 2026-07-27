# Engine Routing

Detail moved out of `SKILL.md` so the routing rules stay scannable: the engine's
category gate, default implementations, and empty-result fallback, plus the
full call chain and source map. Read this while tracing where a factory lands —
the rules live in `../SKILL.md`.

---

## The `FindFactoriesInCategory` gate

The engine
iterates every registered top-level category and calls
`FindFactoriesInCategory`, which does:

```cpp
// Engine/.../ContentBrowserAssetDataSource/Private/NewAssetContextMenu.cpp:159
const uint32 FactoryCategories = Factory->GetMenuCategories();
if (FactoryCategories & AssetTypeCategory)
{
    // Factory is processed for this top-level category
}
```

## Engine defaults

### Default behavior of `GetMenuCategories()`

The base implementation (see `Engine/Source/Editor/UnrealEd/Private/Factories/Factory.cpp:298`)
delegates to `IAssetTypeActions::GetCategories()` registered for the factory's
`SupportedClass`:

```cpp
uint32 UFactory::GetMenuCategories() const
{
    FAssetToolsModule& AssetToolsModule = FModuleManager::LoadModuleChecked<FAssetToolsModule>("AssetTools");
    UClass* LocalSupportedClass = GetSupportedClass();

    if (LocalSupportedClass)
    {
        TWeakPtr<IAssetTypeActions> Actions =
            AssetToolsModule.Get().GetAssetTypeActionsForClass(LocalSupportedClass);
        if (Actions.IsValid())
        {
            return Actions.Pin()->GetCategories();
        }
    }
    return EAssetTypeCategories::Misc;
}
```

In UE5, `UAssetDefinition` (see `Engine/Source/Editor/AssetDefinition/Public/AssetDefinition.h`)
integrates into the same pipeline; its `GetAssetCategories()` feeds the
`IAssetTypeActions` proxy. For `ULevelSequence` specifically:

```cpp
// Engine/Plugins/MovieScene/LevelSequenceEditor/Source/.../AssetDefinition_LevelSequence.h:22
virtual TConstArrayView<FAssetCategoryPath> GetAssetCategories() const override
{
    static const auto Categories = { EAssetCategoryPaths::Basic, EAssetCategoryPaths::Cinematics };
    return Categories;
}
```

So a factory whose `SupportedClass` is `ULevelSequence` inherits bitmask
`Basic | Cinematics` — it will **never** be called for "Gameplay".

### Default behavior of `GetAssetMenuPathsForCategory()`

The base implementation (see `Engine/Source/Editor/UnrealEd/Private/Factories/Factory.cpp:334`)
delegates to `GetAssetMenuPaths(GetSupportedClass(), InCategory)`, which in
turn routes through `IAssetTypeActions::GetSubMenus()` or
`UAssetDefinition::GetAssetCategories()`.

When the override returns an empty array, the engine falls back to defaults:

```cpp
// Engine/.../ContentBrowserAssetDataSource/Private/NewAssetContextMenu.cpp:458-472
if (CategoryPaths.IsEmpty())
{
    const TArray<FText> SubCategories = Item.Factory.GetMenuCategorySubMenus();
    if (!SubCategories.IsEmpty())
    {
        for (const FText& SubCategory : SubCategories)
        {
            CategoryPaths.Add(FAssetCategoryPath(
                FText::FromName(CategoryName), SubCategory));
        }
    }
    else
    {
        CategoryPaths.Add(FAssetCategoryPath(
            FText::FromName(CategoryName)));
    }
}
```

## Full call chain

```
ContentBrowser Add Menu
  → CreateNewAssetMenu()
    → Iterate all AdvancedAssetCategories (Gameplay, Cinematics, Basic, ...)
    → For each: FindFactoriesInCategory(CategoryType)
        → Factory->GetMenuCategories() & CategoryType     ← TIER 1: gate
        → Only matching factories proceed
    → CreateNewAssetMenuCategory(CategoryType)
      → For each matched factory:
          → factory->GetAssetMenuPathsForCategory(CategoryName)  ← TIER 2: path
          → Build sub-menu tree from returned FAssetCategoryPath[]
          → Place factory entry in leaf menu
```

## Key engine source files

| File | What's there |
|------|-------------|
| `Engine/Source/Editor/UnrealEd/Classes/Factories/Factory.h:160-178` | Virtual methods: `GetMenuCategories`, `GetAssetMenuPathsForCategory`, `GetDisplayName`, `GetMenuCategorySubMenus` |
| `Engine/Source/Editor/UnrealEd/Private/Factories/Factory.cpp:298-337` | Default implementations delegating to `IAssetTypeActions` |
| `Engine/Plugins/Editor/ContentBrowser/ContentBrowserAssetDataSource/Source/.../NewAssetContextMenu.cpp:149-173` | `FindFactoriesInCategory` — bitmask check |
| `Engine/Plugins/Editor/ContentBrowser/ContentBrowserAssetDataSource/Source/.../NewAssetContextMenu.cpp:424-540` | `CreateNewAssetMenuCategory` — builds sub-menu tree from `FAssetCategoryPath` |
| `Engine/Source/Developer/AssetTools/Private/AssetTools.cpp:1414` | Standard category registration (Basic, Gameplay, Cinematics, Misc) |
| `Engine/Source/Developer/AssetTools/Public/AssetTypeCategories.h` | `EAssetCategoryPaths` pre-defined `FText` constants |
| `Engine/Source/Editor/AssetDefinition/Public/AssetDefinition.h` | `UAssetDefinition::GetAssetCategories()` — UE5 category source |
