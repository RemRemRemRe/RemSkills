# Channel Boilerplate

Detail moved out of `SKILL.md` so the channel-definition step stays scannable:
the complete `FMovieSceneChannel` USTRUCT skeleton. Read this while writing the
channel — the `meta` tags and delegation rules live in `../SKILL.md`.

---

## Channel USTRUCT

```cpp
// FooChannel.h
#pragma once

#include "Channels/MovieSceneChannel.h"
#include "Channels/MovieSceneChannelData.h"
#include "Channels/MovieSceneChannelTraits.h"
#include "Misc/FrameTime.h"
#include "FooKeyData.h"

#if WITH_EDITOR
#include "SequencerChannelTraits.h"           // for clipboard type definitions
#endif

#include "FooChannel.generated.h"

USTRUCT()
struct MYMODULE_API FFooChannel : public FMovieSceneChannel
{
    GENERATED_BODY()

    using ValueType = FFooKeyData;

    TMovieSceneChannelData<ValueType> GetData()
    {
        return TMovieSceneChannelData<ValueType>(&KeyTimes, &KeyValues, this, &KeyHandles);
    }

    TMovieSceneChannelData<const ValueType> GetData() const
    {
        return TMovieSceneChannelData<const ValueType>(&KeyTimes, &KeyValues);
    }

    // ~FMovieSceneChannel — delegate everything to GetData()
    virtual void GetKeys(const TRange<FFrameNumber>& WithinRange,
        TArray<FFrameNumber>* OutKeyTimes, TArray<FKeyHandle>* OutKeyHandles) override
    {
        GetData().GetKeys(WithinRange, OutKeyTimes, OutKeyHandles);
    }

    virtual void GetKeyTimes(TArrayView<const FKeyHandle> InHandles,
        TArrayView<FFrameNumber> OutKeyTimes) override
    {
        GetData().GetKeyTimes(InHandles, OutKeyTimes);
    }

    virtual void SetKeyTimes(TArrayView<const FKeyHandle> InHandles,
        TArrayView<const FFrameNumber> InKeyTimes) override
    {
        GetData().SetKeyTimes(InHandles, InKeyTimes);
    }

    virtual void DuplicateKeys(TArrayView<const FKeyHandle> InHandles,
        TArrayView<FKeyHandle> OutNewHandles) override
    {
        GetData().DuplicateKeys(InHandles, OutNewHandles);
    }

    virtual void DeleteKeys(TArrayView<const FKeyHandle> InHandles) override
    {
        GetData().DeleteKeys(InHandles);
    }

    virtual void DeleteKeysFrom(FFrameNumber InTime, bool bDeleteKeysBefore) override
    {
        GetData().DeleteKeysFrom(InTime, bDeleteKeysBefore);
    }

    virtual void RemapTimes(const UE::MovieScene::IRetimingInterface& Retimer) override
    {
        GetData().RemapTimes(Retimer);
    }

    virtual TRange<FFrameNumber> ComputeEffectiveRange() const override
    {
        return GetData().GetTotalRange();
    }

    virtual int32 GetNumKeys() const override { return KeyTimes.Num(); }
    virtual void Reset() override
    {
        KeyTimes.Reset();
        KeyValues.Reset();
        KeyHandles.Reset();
    }
    virtual void Offset(FFrameNumber DeltaPosition) override { GetData().Offset(DeltaPosition); }
    virtual FKeyHandle GetHandle(int32 Index) override { return GetData().GetHandle(Index); }
    virtual int32 GetIndex(FKeyHandle Handle) override { return GetData().GetIndex(Handle); }

private:
    UPROPERTY(meta=(KeyTimes))              // MUST have this meta tag
    TArray<FFrameNumber> KeyTimes;

    UPROPERTY(meta=(KeyValues))             // MUST have this meta tag
    TArray<FFooKeyData> KeyValues;

    UPROPERTY(Transient)
    FMovieSceneKeyHandleMap KeyHandles;
};
```
