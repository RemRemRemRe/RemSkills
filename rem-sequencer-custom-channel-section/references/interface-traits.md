# Channel Interface Traits & Free Functions

Detail moved out of `SKILL.md` so the mandatory-rules step stays scannable: the
traits specialization, the `EvaluateChannel` overload, and the
`CopyKeys`/`PasteKeys` no-op overrides. Read this while implementing the channel
interface — the rules and failure symptoms live in `../SKILL.md`.

---

## `TMovieSceneChannelTraits` specialization

```cpp
template<>
struct TMovieSceneChannelTraits<FFooChannel>
    : TMovieSceneChannelTraitsBase<FFooChannel>
{
    enum { SupportsDefaults = false };
};
```

## `EvaluateChannel` overload

```cpp
inline bool EvaluateChannel(const FFooChannel* InChannel,
    FFrameTime InTime, FFooKeyData& OutValue)
{
    return false;   // discrete — not evaluatable via interpolation
}
```

## `CopyKeys` / `PasteKeys` overrides

```cpp
#if WITH_EDITOR
namespace Sequencer
{
    inline void CopyKeys(
        FFooChannel* InChannel,
        const UMovieSceneSection* InSection,
        FName KeyAreaName,
        FMovieSceneClipboardBuilder& ClipboardBuilder,
        TArrayView<const FKeyHandle> InHandles)
    {
        // clipboard not supported for this channel type
    }

    inline void PasteKeys(
        FFooChannel* InChannel,
        UMovieSceneSection* InSection,
        const FMovieSceneClipboardKeyTrack& KeyTrack,
        const FMovieSceneClipboardEnvironment& SrcEnvironment,
        const FSequencerPasteEnvironment& DstEnvironment,
        TArray<FKeyHandle>& OutPastedKeys)
    {
        // clipboard not supported for this channel type
    }
}
#endif
```
