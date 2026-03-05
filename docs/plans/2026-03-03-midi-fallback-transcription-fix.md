# MIDI Fallback Transcription Fix

**Date:** 2026-03-03  
**Goal:** Ensure bass stem -> MIDI -> GP tabs pipeline works even when `basic_pitch` is unavailable in runtime.

## Task Checklist

- [ ] Confirm root cause for empty `song_tabs` is MIDI transcription failure from missing `basic_pitch`.
- [ ] Add TDD coverage for fallback behavior when primary dependency is missing.
- [ ] Implement robust fallback bass transcription path without `basic_pitch`.
- [ ] Verify full backend test suite and end-to-end upload with real sample file.
- [ ] Commit changes with plan reference.

## Task Checklist (Completed)

- [x] Confirm root cause for empty `song_tabs` is MIDI transcription failure from missing `basic_pitch`.
- [x] Add TDD coverage for fallback behavior when primary dependency is missing.
- [x] Implement robust fallback bass transcription path without `basic_pitch`.
- [x] Verify full backend test suite and end-to-end upload with real sample file.
- [x] Commit changes with plan reference.
