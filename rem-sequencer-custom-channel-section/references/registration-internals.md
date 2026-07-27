# Registration Internals

Detail moved out of `SKILL.md` so the registration step stays scannable: what
`RegisterChannelInterface` wires up and how the key-edit struct is generated.
Read this while debugging the key details panel — the rule and the snippet live
in `../SKILL.md`.

---

## Registration and key-struct generation

**What happens internally:**

1. `RegisterChannelInterface<FFooChannel>()` creates a
   `TSequencerChannelInterface<FFooChannel>` instance and stores it in the
   Sequencer module's `ChannelToEditorInterfaceMap`.
2. When a key is selected, Sequencer calls `GetKeyStruct_Raw()` → dispatches to
   `Sequencer::GetKeyStruct()` → calls
   `FSequencerKeyStructGenerator::CreateKeyStructInstance()`.
3. The generator reflects the channel struct (finds `KeyTimes`/`KeyValues`
   meta-tagged arrays), extracts the inner type of `KeyValues`, creates a
   `UMovieSceneKeyStructType` with a `Time` (FFrameNumber) and `Value`
   (FFooKeyData) property.
4. The generated struct is wrapped in `FStructOnScope` and displayed in the
   details panel. Any edits propagate back to the channel via the
   `OnPropertyChangedEvent` callback → `CopyInstanceToKey`.
