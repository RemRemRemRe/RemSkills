# Complete Custom Factory Template

Detail moved out of `SKILL.md` so the routing rules stay scannable: the complete
`UFactory` subclass with custom category routing. Read this while writing the
factory — the rules live in `../SKILL.md`.

---

## Template: complete custom factory with custom category routing

```cpp
// --- FooFactory.h ---
#pragma once

#include "Factories/Factory.h"
#include "FooFactory.generated.h"

UCLASS(hidecategories=Object)
class UFooFactory : public UFactory
{
    GENERATED_BODY()

public:
    UFooFactory(const FObjectInitializer& ObjectInitializer);

    virtual UObject* FactoryCreateNew(UClass* Class, UObject* InParent,
        FName Name, EObjectFlags Flags, UObject* Context,
        FFeedbackContext* Warn) override;
    virtual bool ShouldShowInNewMenu() const override;

    virtual uint32 GetMenuCategories() const override;
    virtual FText GetDisplayName() const override;
    virtual TArray<FAssetCategoryPath> GetAssetMenuPathsForCategory(
        FName InCategory) const override;
};

// --- FooFactory.cpp ---
#include "FooFactory.h"
#include "AssetTypeCategories.h"
#include "AssetDefinition.h"

#define LOCTEXT_NAMESPACE "FooFactory"

UFooFactory::UFooFactory(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer)
{
    bCreateNew = true;
    bEditAfterNew = true;
    SupportedClass = UBarAssetType::StaticClass();
}

UObject* UFooFactory::FactoryCreateNew(UClass* Class, UObject* InParent,
    FName Name, EObjectFlags Flags, UObject* Context, FFeedbackContext* Warn)
{
    return NewObject<UBarAssetType>(InParent, Class, Name,
        Flags | RF_Transactional);
}

bool UFooFactory::ShouldShowInNewMenu() const
{
    return true;
}

uint32 UFooFactory::GetMenuCategories() const
{
    return Super::GetMenuCategories() | EAssetTypeCategories::Gameplay;
}

FText UFooFactory::GetDisplayName() const
{
    return LOCTEXT("FooFactory_DisplayName", "Your Asset (Custom)");
}

TArray<FAssetCategoryPath> UFooFactory::GetAssetMenuPathsForCategory(
    FName) const
{
    static const TArray Categories
    {
        FAssetCategoryPath(EAssetCategoryPaths::Gameplay,
            LOCTEXT("FooSection", "Foo"), ECategoryMenuType::Section)
    };
    return Categories;
}

#undef LOCTEXT_NAMESPACE
```
