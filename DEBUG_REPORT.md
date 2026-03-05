# DEBUG_REPORT.md

## Debug Workflow Rerun (2026-03-04)

This report was regenerated after the fingering root-cause fix using the same debug-track workflow shape as before (single-bar controlled track with known in-range + one unplayable note) through `TabPipeline.run(...)`.

## 1) Updated Tuning + Candidate Sanity

`STANDARD_BASS_TUNING_MIDI`:

| String | Open MIDI |
|---|---:|
| 4 (E1) | 28 |
| 3 (A1) | 33 |
| 2 (D2) | 38 |
| 1 (G2) | 43 |

Candidate sanity probe (`max_fret=24`) now passes:

```json
{
  "all_ok": true,
  "candidate_map": {
    "34": [[3, 1], [4, 6]],
    "33": [[3, 0], [4, 5]],
    "40": [[2, 2], [3, 7], [4, 12]],
    "62": [[1, 19], [2, 24]]
  },
  "failures": {}
}
```

## 2) Stage Counters (Post-Fix)

```json
{
  "stage_counts": {
    "raw": 4,
    "cleaned": 4,
    "quantized": 4,
    "fingered": 3,
    "exported": 3
  },
  "after_fingering": 3,
  "exported_notes": 3,
  "fingering": {
    "dropped_reasons": {
      "no_fingering_candidate": 1
    },
    "dropped_note_count": 1,
    "playable_note_count": 3,
    "octave_salvage_enabled": false,
    "octave_salvaged_notes": 0,
    "max_fret": 24
  }
}
```

## 3) Sample Fingered Notes (`string,fret`)

From the generated AlphaTex note line:

- `1.3.4` => fret `1`, string `3`
- `2.2.4` => fret `2`, string `2`
- `2.1.4` => fret `2`, string `1`

## 4) AlphaTex Excerpt (Contains Notes, Not Rests-Only)

```alphatex
\tempo 120
\ts 4 4
\tuning E1 A1 D2 G2
\sync(0 0 0 0)
1.3.4 2.2.4 2.1.4
```

## 5) Guardrail Evidence (No Silent Rests-Only Success)

When `quantized > 0` and `fingered == 0`, pipeline now raises `FingeringCollapseError` and API returns structured 422 payload including:

- `error: "fingering_collapse"`
- `debug_info.stage_counts`
- `debug_info.fingering.dropped_reasons`
- `debug_info.fingering.tuning_midi`

This prevents silent rests-only exports.
