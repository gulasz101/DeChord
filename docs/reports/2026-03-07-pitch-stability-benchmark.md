# 2026-03-07 Pitch Stability Benchmark

## What Was Implemented

- Added a typed `PitchStabilityConfig` in `backend/app/midi.py` with env-backed controls for enabling the stabilizer, confidence gating, transition hysteresis, octave penalties, note duration, gap merging, smoothing window, and harmonic recheck behavior.
- Added `stabilize_bass_pitch_track(...)` in `backend/app/midi.py` to smooth framewise bass pitch tracks with:
  - confidence-aware continuity preference
  - octave remapping against the current stable state
  - harmonic/octave recheck against spectral energy
  - short-transition suppression
  - short weak-gap bridging
  - stable-region note segmentation
- Integrated the stabilizer into the fallback monophonic pitch path in `backend/app/midi.py`.
- Extended `BasicPitchTranscriber` in `backend/app/services/bass_transcriber.py` with a note-event stability pass so the benchmarked production path also uses pitch-stability logic when `DECHORD_PITCH_STABILITY_ENABLE=1`.

## Songs Evaluated

- `Muse - Hysteria`
- `Iron Maiden - The Trooper`

Ground truth came from local `test songs/*.gp5`.

## Commands Run

- `cd /Users/wojciechgula/Projects/DeChord/backend && DECHORD_PITCH_STABILITY_ENABLE=0 uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Muse - Hysteria" --quality standard --config refinement --phase pitch_stability_off_refinement`
- `cd /Users/wojciechgula/Projects/DeChord/backend && DECHORD_PITCH_STABILITY_ENABLE=1 uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Muse - Hysteria" --quality standard --config refinement --phase pitch_stability_on_refinement`
- `cd /Users/wojciechgula/Projects/DeChord/backend && DECHORD_PITCH_STABILITY_ENABLE=1 uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Muse - Hysteria" --quality standard --config full --phase pitch_stability_on_full`
- `cd /Users/wojciechgula/Projects/DeChord/backend && DECHORD_PITCH_STABILITY_ENABLE=0 uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Iron Maiden - The Trooper" --quality standard --config refinement --phase pitch_stability_off_refinement`
- `cd /Users/wojciechgula/Projects/DeChord/backend && DECHORD_PITCH_STABILITY_ENABLE=1 uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Iron Maiden - The Trooper" --quality standard --config refinement --phase pitch_stability_on_refinement`
- `cd /Users/wojciechgula/Projects/DeChord/backend && DECHORD_PITCH_STABILITY_ENABLE=1 uv run python scripts/evaluate_tab_quality.py --song-dir "../test songs" --song "Iron Maiden - The Trooper" --quality standard --config full --phase pitch_stability_on_full`

## Compared Configurations

- `refinement + pitch stability disabled`
- `refinement + pitch stability enabled`
- `full + pitch stability enabled`

## Top-Line Results

### Muse - Hysteria

| Config | F1 | Pitch Acc | Note Diff | Avg Bar Diff | Pitch Mismatch | Onset Mismatch | Octave Errors | Generated Notes | Runtime (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| refinement, stability off | 0.0509 | 0.3143 | -1303 | 14.98 | 24 | 1304 | 7 | 36 | 118.18 |
| refinement, stability on | 0.0635 | 0.2500 | -1293 | 14.86 | 33 | 1295 | 7 | 46 | 117.37 |
| full, stability on | 0.0635 | 0.2500 | -1293 | 14.86 | 33 | 1295 | 7 | 46 | 224.23 |

Interpretation:

- Hysteria improved in recall-oriented metrics with stability enabled: F1 `+0.0126`, note diff `+10`, onset mismatches `-9`, and generated notes `+10`.
- The gain came from producing more notes, not cleaner note selection: pitch mismatches rose from `24` to `33`, and pitch accuracy fell from `0.3143` to `0.2500`.
- `full` matched `refinement` exactly for Hysteria while costing about `+106.86s`, so the extra ensemble pass did not buy anything for this change.

### Iron Maiden - The Trooper

| Config | F1 | Pitch Acc | Note Diff | Avg Bar Diff | Pitch Mismatch | Onset Mismatch | Octave Errors | Generated Notes | Runtime (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| refinement, stability off | 0.2110 | 0.7487 | -1352 | 8.10 | 50 | 1420 | 4 | 267 | 136.88 |
| refinement, stability on | 0.2838 | 0.6633 | -1166 | 7.00 | 99 | 1325 | 10 | 453 | 137.05 |
| full, stability on | 0.2779 | 0.6228 | -1158 | 6.94 | 109 | 1330 | 26 | 461 | 263.21 |

Interpretation:

- Trooper also improved in recall/density terms with stability enabled: F1 `+0.0728`, note diff `+186`, avg bar diff `-1.10`, onset mismatches `-95`, and generated notes `+186`.
- The cost was clear pitch precision regression: pitch mismatches almost doubled (`50` -> `99`) and octave errors rose (`4` -> `10`).
- `full` made density slightly better again, but it further worsened pitch mismatch and octave error counts while adding about `+126.16s`.

## Observed Remaining Failure Modes

- The stabilizer is still too willing to admit extra notes on both songs, especially short bursts under `0.1s`. That increased recall, but it also introduced more false note entries.
- Hysteria remains heavily recall-limited even after the gain: `-1293` note difference is still the dominant problem.
- Trooper shows the main regression risk: note continuity improved, but the current thresholds are not conservative enough to stop extra pitch changes and octave slips from being committed.
- In benchmark reality, the transcription path is still dominated by `basic_pitch`, so the biggest remaining tuning surface is the note-event stabilizer in `BasicPitchTranscriber`, not the fallback spectral path.

## Song-Specific Answer

- Did Hysteria improve: Yes, modestly. F1, note count, and onset mismatch improved, but pitch precision did not.
- Did The Trooper remain stable or improve: It improved on F1 and note-density recall, but it did not remain pitch-stable; pitch mismatch and octave errors worsened enough that this still needs tuning before default enablement.

## Recommended Next Tuning Step

- Tighten admission of new notes in the `basic_pitch` note-event stability pass:
  - require stronger evidence before accepting a short pitch change
  - aggressively suppress sub-`100ms` intrusions unless adjacent context supports them
  - add a stronger octave-specific rejection rule when a new note is both short and `±12` from the local anchor

This should preserve the recall gains while pulling back the current false-positive surge.
