# La grenade Tab Comparison (Official PDF vs DeChord Generated)

## 1. Overview
- Goal: Validate DeChord bass-tab output against the official "La grenade" transcription at bar level.
- Official source: `docs/reference/La-grenade-basse.pdf` (used only for extracted density/fret-token summaries).
- Generated source: `docs/reports/la_grenade_generated_output.alphatex` and `docs/reports/la_grenade_generated_diagnostics.json`.
- Pipeline settings: `tab_generation_quality_mode=high_accuracy_aggressive`, `bpm_hint=120`, `time_signature=4/4`, `subdivision=16`.
- Extraction scope: official PDF machine parsing was reliable enough for best-effort bar-note density on bars 11-30 (page 2), but not reliable for full symbolic rhythm/pitch parsing.

## 2. Metrics
- Bars compared: **20** (official bars 11-30)
- Total notes: official **103** vs generated **81**
- Average absolute per-bar note count difference: **3.40**
- Maximum per-bar note count difference: **7**
- Bars with |difference| > 2: **12**

### Pipeline Diagnostics (Generated)
- `beat_bpm_estimate_raw`: 130.4347826086954
- `beat_bpm_estimate_corrected`: 130.4347826086954
- `grid_correction_applied`: none
- `suspect_silence_bars_count`: 4
- `notes_added_second_pass`: 18
- `tab_last_sync_ms`: 194210 (audio_duration_sec=194.65290249433107)

### Bar Table (11-30)
| bar_index | official_note_count | generated_note_count | diff | official_frets (extracted) | generated_notes (string,fret) |
|---:|---:|---:|---:|---|---|
| 11 | 5 | 4 | -1 | 2 2 2 2 2 | (3,9) (3,9) (3,9) (4,8) |
| 12 | 7 | 6 | -1 | 2 2 2 2 2 4 2 | (3,9) (3,9) (3,9) (3,9) (4,6) (1,5) |
| 13 | 1 | 6 | 5 | 7 | (4,6) (4,6) (4,6) (4,6) (2,7) (2,8) |
| 14 | 2 | 6 | 4 | 7 7 | (2,8) (2,9) (2,9) (2,9) (2,11) (2,10) |
| 15 | 1 | 8 | 7 | 5 | (2,7) (4,5) (2,7) (2,7) (4,5) (2,5) (2,6) (2,7) |
| 16 | 2 | 7 | 5 | 5 5 | (2,7) (2,7) (2,7) (2,7) (2,10) (2,8) (2,7) |
| 17 | 3 | 5 | 2 | 7 7 7 | (2,5) (2,5) (2,5) (2,5) (2,4) |
| 18 | 6 | 6 | 0 | 5 7 7 5 7 5 | (2,4) (2,5) (2,5) (2,5) (2,5) (2,4) |
| 19 | 5 | 5 | 0 | 7 5 7 5 7 | (2,4) (2,4) (2,4) (2,4) (1,5) |
| 20 | 7 | 4 | -3 | 7 5 7 7 5 7 5 | (2,4) (2,4) (2,4) (2,4) |
| 21 | 8 | 1 | -7 | 7 9 9 7 9 7 7 9 | (4,6) |
| 22 | 8 | 3 | -5 | 9 7 9 7 9 7 9 7 | (4,6) (1,9) (4,6) |
| 23 | 8 | 6 | -2 | 5 7 5 7 5 7 7 5 | (4,6) (2,7) (4,5) (4,5) (2,7) (4,5) |
| 24 | 8 | 5 | -3 | 5 7 7 5 7 5 5 7 | (4,5) (1,7) (2,7) (2,7) (4,5) |
| 25 | 8 | 2 | -6 | 9 7 9 7 9 7 9 7 | (4,5) (4,6) |
| 26 | 8 | 4 | -4 | 9 7 9 7 9 7 9 7 | (4,6) (1,9) (1,9) (4,6) |
| 27 | 8 | 1 | -7 | 7 5 7 4 7 7 7 5 | (4,6) |
| 28 | 3 | 0 | -3 | 9 7 7 | - |
| 29 | 2 | 0 | -2 | 3 7 | - |
| 30 | 3 | 2 | -1 | 7 5 5 | (1,9) (1,9) |

## 3. Highlights (Largest Differences)
- Bar 15: official=1, generated=8, diff=7; official frets=[5]; generated (string,fret)=['(2,7)', '(4,5)', '(2,7)', '(2,7)', '(4,5)', '(2,5)', '(2,6)', '(2,7)']
- Bar 21: official=8, generated=1, diff=-7; official frets=[7, 9, 9, 7, 9, 7, 7, 9]; generated (string,fret)=['(4,6)']
- Bar 27: official=8, generated=1, diff=-7; official frets=[7, 5, 7, 4, 7, 7, 7, 5]; generated (string,fret)=['(4,6)']
- Bar 25: official=8, generated=2, diff=-6; official frets=[9, 7, 9, 7, 9, 7, 9, 7]; generated (string,fret)=['(4,5)', '(4,6)']
- Bar 13: official=1, generated=6, diff=5; official frets=[7]; generated (string,fret)=['(4,6)', '(4,6)', '(4,6)', '(4,6)', '(2,7)', '(2,8)']
- Bar 16: official=2, generated=7, diff=5; official frets=[5, 5]; generated (string,fret)=['(2,7)', '(2,7)', '(2,7)', '(2,7)', '(2,10)', '(2,8)', '(2,7)']
- Bar 22: official=8, generated=3, diff=-5; official frets=[9, 7, 9, 7, 9, 7, 9, 7]; generated (string,fret)=['(4,6)', '(1,9)', '(4,6)']
- Bar 14: official=2, generated=6, diff=4; official frets=[7, 7]; generated (string,fret)=['(2,8)', '(2,9)', '(2,9)', '(2,9)', '(2,11)', '(2,10)']

## 4. Observations
- In this compared range, generated output is generally sparser than official (81 vs 103 notes total).
- Largest under-density appears around bars 21-27, where official lines show repeated dense patterns while generated bars often contain 1-4 notes.
- The generated tab includes plausible fret/string movement but often collapses repeated ostinato-like note density from the official transcription.
- High-accuracy aggressive diagnostics show second-pass recovery (`suspect_silence_bars_count=4`, `notes_added_second_pass=18`), but remaining density gaps indicate unresolved misses in repeated-note sections.

## 5. Conclusion
- Qualitative alignment is **partial**: the pipeline captures broad tonal movement and section structure, but bar-level note density remains materially below the official transcription in many bars of the tested range.
- Based on this bar-range comparison, generated tab quality is suitable for coarse guidance, not yet a close transcription match for dense rhythmic passages.

## Method Notes
- Official PDF extraction was best-effort from numeric tab tokens; full note-by-note rhythm/pitch reconstruction from PDF glyphs was not reliably automatable in this run.
- To respect copyright, this report includes only minimal extracted tokens and aggregate comparison statistics, not a full reproduction of the official tab.