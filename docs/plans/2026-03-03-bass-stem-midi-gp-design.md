# Bass Stem -> MIDI -> Guitar Pro Design

**Date:** 2026-03-03  
**Status:** Approved for implementation planning  
**Scope:** Web app backend/frontend, LibSQL persistence, EADG 4-string bass only (v1)

---

## Goal

Add a phased feature pipeline:
1. Parse separated bass stem into MIDI.
2. Convert MIDI into Guitar Pro tabs.
3. Render Guitar Pro tabs in sync with DeChord playback and chord timeline.

All generated artifacts remain portable by persisting binary outputs in LibSQL BLOB storage.

## Product Constraints

- Tuning target for v1: `E1 A1 D2 G2` (4-string only).
- Existing chord/stem playback flows must remain functional if MIDI/tab generation fails.
- Keep implementation modular so transcription and tab engines can be swapped later.

## Architecture

### Data model additions

- `song_midis`
  - `id`
  - `song_id` (FK)
  - `source_stem_key` (`bass`)
  - `midi_blob` (BLOB)
  - `midi_format` (`mid`)
  - `engine` (`basic_pitch` initially)
  - `status` (`complete|failed`)
  - `error_message` (nullable)
  - timestamps

- `song_tabs`
  - `id`
  - `song_id` (FK)
  - `source_midi_id` (FK)
  - `tab_blob` (BLOB)
  - `tab_format` (`gp5`)
  - `tuning` (`E1,A1,D2,G2`)
  - `strings` (`4`)
  - `generator_version`
  - `status` (`complete|failed`)
  - `error_message` (nullable)
  - timestamps

### Phase 1: Bass stem -> MIDI

- Add backend transcription service abstraction:
  - `transcribe_bass_stem_to_midi(input_wav) -> bytes`
- Recommended first engine: `basic-pitch` Python package/CLI adapter.
- Integrate into current analysis/stems job stages:
  - `analyzing_chords -> splitting_stems -> transcribing_bass_midi -> persisting -> complete`
- Store generated MIDI as BLOB in `song_midis`.

### NeuralNote integration options

1. **Recommended now:** `basic-pitch` backend integration (pragmatic path to production).
2. **Later option:** neuralnote-compatible headless adapter if a robust binary/library path is established.
3. **Not recommended:** plugin-host automation for export (fragile and hard to operate in backend runtime).

### Phase 2: MIDI -> Guitar Pro tabs

- Build EADG bass tab-mapping engine:
  - note-to-string/fret assignment under instrument constraints
  - minimize fretboard travel and impossible stretches
  - deterministic first pass (no user interaction needed)
- Export GP5 via `PyGuitarPro`.
- Store generated GP5 as BLOB in `song_tabs`.

### Phase 3: Tab display + synchronized play-along

- Use `alphaTab` in frontend for Guitar Pro rendering and cursor visualization.
- Keep DeChord player as timing master.
- Synchronize tab cursor and chord timeline from the same playback clock.
- Maintain fallback behavior:
  - tabs unavailable -> chords/stems UI still fully usable.

## API surface (planned)

- `GET /api/songs/{song_id}/midi` -> latest MIDI metadata/status
- `GET /api/songs/{song_id}/midi/file` -> MIDI binary stream
- `GET /api/songs/{song_id}/tabs` -> latest GP metadata/status
- `GET /api/songs/{song_id}/tabs/file` -> GP binary stream
- Extend job status payload with:
  - `midi_status`, `midi_error`
  - `tab_status`, `tab_error`

## Error handling

- If bass stem split succeeds but MIDI fails:
  - keep analysis/stems successful
  - set `midi_status=failed` with error details
- If MIDI succeeds but GP generation fails:
  - keep MIDI available
  - set `tab_status=failed` with error details

## Testing strategy

- Backend unit tests:
  - transcription adapter contract and failure modes
  - EADG mapping constraints and deterministic fingering output
  - GP export validity (roundtrip parse where possible)
- Backend integration tests:
  - upload -> stems -> MIDI -> tabs pipeline status transitions
  - DB persistence and retrieval of BLOB artifacts
- Frontend tests:
  - tab viewer render with GP payload
  - sync behavior between player time and tab cursor
  - fallback behavior when tabs unavailable

## Risks and mitigations

- Transcription quality variability:
  - add basic quality heuristics and confidence metadata
  - keep engine abstraction for future replacement/tuning
- Tab fingering quality:
  - deterministic baseline in v1; add correction workflow in later phase
- Runtime cost:
  - isolate heavy steps and preserve partial success behavior

## Phases

1. Phase 1: bass stem -> MIDI + persistence + status/reporting.
2. Phase 2: MIDI -> GP5 tab generation + persistence.
3. Phase 3: GP tab rendering + playback/chord sync.
4. Phase 4: quality improvements and optional manual corrections.

---

## Brainstorming Task Checklist

- [ ] Capture approved design decisions in plan doc.
- [ ] Record implementation-phase boundaries and dependencies.
- [ ] Commit this design document with traceable plan-path reference.

## Brainstorming Task Checklist (Completed)

- [x] Capture approved design decisions in plan doc.
- [x] Record implementation-phase boundaries and dependencies.
- [x] Commit this design document with traceable plan-path reference.
