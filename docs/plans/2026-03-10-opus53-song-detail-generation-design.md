# Opus 5-3 Song Detail Generation Design

**Date:** 2026-03-10

**Goal:** Turn the dead `Generate Stems` and `Generate Bass Tab` actions in the Opus 5-3 song detail page into real, usable product flows that match the current app architecture and the Opus 5-3 design language.

## Current State

The current `SongDetailPage` in the redesign exposes four stem/tab related actions:
- `Download All Stems`
- `Upload Stem`
- `Generate Stems`
- `Generate Bass Tab`

Only the first two are currently functional.

What already exists in the system:
- Song upload and analysis pipeline
- Optional song upload with automatic stem generation
- Manual song-scoped stem upload
- Song detail loading with stems, notes, playback prefs, and tab metadata
- Song tabs file delivery and metadata read endpoints
- Player support for real tabs and real stems

What does not exist as a user-facing flow today:
- Explicit regeneration of stems from an existing song from the 5-3 shell
- Explicit regeneration of bass MIDI/tab from a selected source from the 5-3 shell
- Version-aware source selection UX for regeneration
- Progress/error handling for those operations in the song detail view

## Product Problem

The redesign currently advertises two important actions that do nothing. That is worse than omission because users will assume the system is broken.

The next step should not be a superficial button hookup. The app now supports both:
- system-generated assets
- user-uploaded stems

That means the generation flows need a clear source-of-truth model.

## Core Design Questions

### 1. What should `Generate Stems` mean?

Recommended meaning:
- Re-run source separation on the song's original uploaded mix.
- It should produce a fresh system-generated set of stems for that song.
- It should not attempt to regenerate stems from a manually uploaded stem.

Reasoning:
- Demucs-style separation is a mix-to-stems operation, not a stem-to-stems operation.
- Manual stems are already an output artifact, not the canonical source mix.
- Supporting "generate stems from a manual stem" would confuse the model and create unclear output semantics.

### 2. What should `Generate Bass Tab` mean?

Recommended meaning:
- Generate bass MIDI/tab from a selected source stem within the song context.
- Default source should be the latest system bass stem if present.
- If no system bass stem exists, allow selecting a user-uploaded stem.

Reasoning:
- Bass tab generation is most credible when grounded in a specific audio source.
- The app now has multiple possible bass sources, so silent auto-selection is risky.
- A source selector keeps the flow understandable and versionable.

## Options Considered

### Option 1: Minimal direct-button execution

Behavior:
- `Generate Stems` immediately regenerates stems from the original mix.
- `Generate Bass Tab` immediately regenerates tab from the current best source.

Pros:
- Fastest to build
- Minimal UX surface

Cons:
- Too much hidden logic
- Ambiguous source choice for bass tab
- Weak foundation for versioning and debugging

### Option 2: Song detail action panels with explicit source selection

Behavior:
- `Generate Stems` opens a small inline or modal panel explaining that stems will be regenerated from the original mix.
- `Generate Bass Tab` opens a source selection panel listing eligible bass stems.
- Both flows show progress, result state, and refresh song detail when complete.

Pros:
- Clear user mental model
- Compatible with the current route-driven Opus 5-3 architecture
- Works with current backend patterns and future versioning

Cons:
- Slightly more UI work
- Requires explicit action state handling

### Option 3: Full asset-jobs workspace in song detail

Behavior:
- Add a larger asset management system with per-job history, retries, lineage, and source trees.

Pros:
- Strongest long-term model

Cons:
- Too much scope for the current need
- Delays removal of the dead-button problem

## Recommendation

Use **Option 2**.

It is the best balance between product clarity and implementation cost. It keeps the Opus 5-3 shell, avoids fake simplicity, and gives the system room to support asset versions later without having to redesign again.

## Recommended Product Behavior

### Generate Stems

Entry point:
- `Generate Stems` button on `SongDetailPage`

Flow:
- Open a compact 5-3-styled confirmation panel
- Explain: "This regenerates system stems from the original uploaded mix. Existing manual stems are preserved."
- User confirms generation
- UI shows in-panel progress and disables repeat submission while active
- On success:
  - refresh song detail
  - refresh song library/project counts if needed
  - show latest generated stems in stem list
- On failure:
  - keep panel open with clear error state

Versioning behavior:
- Manual stems remain as user assets
- Regenerated system stems replace or supersede the prior system-generated set
- No deletion of manual stems

### Generate Bass Tab

Entry point:
- `Generate Bass Tab` button on `SongDetailPage`

Flow:
- Open a 5-3-styled panel
- Show eligible source stems
- Default selection logic:
  - latest system bass stem first
  - otherwise latest user-uploaded stem whose role is clearly bass-like
- User confirms generation
- UI shows progress and result state
- On success:
  - refresh tab metadata and player availability
  - keep selected source visible in the result summary if possible
- On failure:
  - show error message and preserve source selection

Versioning behavior:
- New MIDI/tab should be tied to a chosen source stem
- The app should preserve enough metadata to know which source produced the current tab

## Backend Design Direction

### Generate Stems API

Recommended shape:
- `POST /api/songs/{song_id}/stems/regenerate`

Behavior:
- Load original song audio
- Run existing stem separation pipeline
- Persist new system stems
- Return job id or immediate result depending on implementation constraints

### Generate Bass Tab API

Recommended shape:
- `POST /api/songs/{song_id}/tabs/regenerate`

Payload:
- `source_stem_key`
- optionally later: `source_stem_version` or `source_stem_id`

Behavior:
- Load chosen stem audio
- Transcribe bass MIDI
- Generate tab
- Persist resulting midi/tab records linked to source

## Data Model Direction

Short-term acceptable approach:
- Keep existing tables if current schema can represent source stem provenance clearly enough
- Add minimal metadata if needed to record which stem produced the current MIDI/tab

Likely needed additions:
- explicit source stem reference for generated midi/tab lineage
- possibly a generation type or asset origin field if current `stem_key` semantics are insufficient

## UX Design Direction

Keep Opus 5-3 language:
- small editorial control surfaces
- clear typography
- sharp-cornered action buttons
- strong state cues for processing/success/failure
- no generic dashboard-style drawers

Recommended interaction pattern:
- inline expandable panels in `SongDetailPage`
- one panel open at a time
- progress and error state embedded where the action started

## Testing Strategy

Plan to cover:
- button opens correct generation panel
- source selection defaults correctly for tab generation
- confirmation triggers correct API call
- loading/progress/error/success states render correctly
- refreshed song detail rehydrates stems/tab status after completion
- route-level integration from `App.tsx`

## Success Criteria

This work is successful when:
- `Generate Stems` and `Generate Bass Tab` are no longer dead controls
- users understand what source each operation uses
- manual stems remain preserved
- generated assets refresh into the 5-3 shell without navigation hacks
- the implementation reuses current backend pipelines instead of duplicating them
