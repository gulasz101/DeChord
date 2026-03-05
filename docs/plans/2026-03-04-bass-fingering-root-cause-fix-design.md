# Bass Fingering Root Cause Fix Design

**Date:** 2026-03-04  
**Status:** Approved for implementation planning  
**Scope:** Phase 2 bass tab generation rest-only failure caused by fingering stage octave mismatch and all-or-nothing solver behavior.

---

## Goal

Fix the fingering stage so valid bass notes are preserved and exported as playable AlphaTex notes, with explicit guardrails that prevent silent regressions to rests-only output.

## Approved Decisions

- Apply tuning fix in fingering solver internals (not only AlphaTex output text).
- Use explicit MIDI naming: `STANDARD_BASS_TUNING_MIDI = {4: 28, 3: 33, 2: 38, 1: 43}`.
- Keep string numbering convention: `4 = low E`, `1 = high G` across candidate generation, DP, and exporter expectations.
- Keep optional octave salvage hard-disabled for this change.
- Set default `max_fret` behavior to support modern lines (`24`).

## Architecture Changes

### 1) Fingering core

- Replace octave-high tuning constants in `backend/app/services/fingering.py`.
- Rename tuning constant to include `_MIDI` suffix for clarity.
- Keep candidate generation deterministic and testable as a direct unit.

### 2) Solver robustness

- Remove all-or-nothing return behavior.
- If a note has no candidates, drop only that note and continue solving playable notes.
- Return debug counters for dropped notes and preserved notes.
- Keep octave-salvage path implemented but disabled by configuration default (hard disabled in this scope).

### 3) Pipeline and exporter safety

- Add a pipeline guard: when quantized notes exist but fingering returns none, raise explicit error.
- Include debug details in failure response: stage counters, dropped reasons, tuning map, `max_fret`.
- Do not silently emit rests-only AlphaTex in that failure condition.

### 4) Debug probes

- Add debug-only candidate sanity probe with required checks:
  - `33 -> (3,0)`
  - `34 -> (3,1)`
  - `28 -> (4,0)`
  - `62 -> (1,19)`

## Testing Strategy

- Candidate generation regression tests for octave correctness and out-of-range behavior.
- DP/solver test proving partial unplayable input does not collapse entire output.
- End-to-end pipeline smoke test proving non-rest AlphaTex note tokens and preserved `\\sync` lines.
- Regenerate `DEBUG_REPORT.md` from same debugging flow and include updated counters + sample output.

## Risks and Mitigations

- Risk: accidental mismatch between solver tuning and exporter tuning string.  
  Mitigation: assert tuning map in debug info and test solver candidate probes directly.
- Risk: guardrail errors breaking existing API expectations.  
  Mitigation: add explicit API tests for error payload shape and debug fields.

---

## Brainstorming Task Checklist

- [x] Explore project context and existing phase2 fingering/export behavior.
- [x] Clarify octave-salvage behavior (`hard disabled`).
- [x] Propose and validate solution approaches with recommendation.
- [x] Present and receive approval for architecture, safety, and test strategy.
- [x] Record approved design in `docs/plans`.
