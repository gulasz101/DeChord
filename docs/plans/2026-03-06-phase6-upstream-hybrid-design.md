# Phase 6 Upstream Hybrid Dense-Note Design

**Goal:** Improve dense bass note hypothesis generation upstream of cleanup by augmenting BasicPitch with a targeted, audio-derived dense-note generator and a pre-cleanup hybrid fusion stage.

## Scope

- Keep the deterministic evaluation harness intact.
- Keep cleanup, quantization, fingering, and AlphaTex export largely unchanged.
- Preserve the existing BasicPitch path as the primary source.
- Add a secondary dense-note hypothesis source only for targeted windows.
- Keep the implementation CPU-friendly and dependency-neutral by reusing existing `librosa`, `wave`, and repo utilities.

## Proposed Architecture

### 1. Targeted Dense-Note Generator

Add a lightweight generator that only runs in suspect dense windows identified by existing bar diagnostics:
- dense sparse bars already flagged by Phase 5 logic
- bars with strong onset evidence but low primary note count
- sparse or empty bars with non-trivial RMS and onset support

For each targeted window, derive note candidates from bass audio using:
- onset times from the bass stem
- short provisional durations inferred from neighboring onsets / window end
- local spectral pitch estimation around each onset using short-window `librosa` pitch features
- optional pitch anchoring to nearby accepted BasicPitch context when the local passage looks like a repeated-note ostinato

The generator emits structured candidate rows with onset, end, pitch, confidence, source tag, and local support metadata.

### 2. Upstream Hybrid Fusion Before Cleanup

Fuse BasicPitch raw notes with dense-note candidates before cleanup.

Fusion policy:
- preserve BasicPitch notes by default
- add dense candidates only when they improve onset coverage and clear plausibility gates
- de-duplicate near-identical notes
- prefer local pitch anchors in repeated-note passages to suppress noisy pitch scatter
- record whether retained notes originate from `basic_pitch`, `dense_note_generator`, or merged hybrid logic

This replaces the current assumption that the dense recovery path must come from a second BasicPitch retranscription pass.

### 3. Repeated-Note Specialized Mode

Detect dense repeated-note passages when a local window has:
- high onset density
- low pitch diversity in nearby primary notes
- a strong dominant pitch anchor

In this mode:
- allow denser insertions
- prefer the stable local anchor pitch
- penalize pitch variation unless local support is strong

### 4. Diagnostics and Evaluation

Extend debug/evaluation output to attribute each raw pre-cleanup note by source and track whether it survives cleanup and whether it matches the reference in evaluation mode.

Required artifacts:
- `docs/reports/hysteria_phase6_transcription_sources.json`
- `docs/reports/trooper_phase6_transcription_sources.json`
- `docs/reports/phase6_transcription_source_summary.md`
- `docs/reports/phase6_upstream_hybrid_report.md`

## Alternatives Considered

### A. Replace BasicPitch outright
Rejected for this phase because it violates the scope and introduces larger dependency/runtime risk.

### B. Loosen downstream cleanup further
Rejected because current evidence says the bottleneck is upstream under-generation/noise, not cleanup conservatism.

### C. Re-run BasicPitch with more sensitivity only
Rejected as the primary Phase 6 path because it is still the same source family and does not provide an independent dense-note hypothesis stream.

## Testing Strategy

Use TDD around:
- dense candidate generation in targeted windows
- pre-cleanup hybrid fusion and rejection reasons
- repeated-note anchor behavior
- source attribution propagation into evaluation artifacts

Then run the deterministic Hysteria and Trooper evaluations after `make reset`.
