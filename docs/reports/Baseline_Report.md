# Baseline Report

- Date: 2026-03-05
- Git hash: `f9f998754c5b22e4b6b3528eddb9019220890113`
- Branch: `codex/stems-demucs-env-config`
- Canonical execution command:

```bash
cd backend && uv run python - <<'PY'
import json
from pathlib import Path
from app.stems import split_to_stems
from app.services.tab_pipeline import TabPipeline

repo = Path(__file__).resolve().parent.parent
audio = Path('/Users/wojciechgula/Downloads/Clara Luciani - La grenade (Clip officiel) [85m-Qgo9_nE].mp3')
out_dir = repo / 'docs' / 'reports'
out_dir.mkdir(parents=True, exist_ok=True)
stems_dir = repo / 'backend' / 'stems' / 'baseline_la_grenade'

stems = split_to_stems(str(audio), stems_dir)
bass = next(s.relative_path for s in stems if s.stem_key == 'bass')
drums = next(s.relative_path for s in stems if s.stem_key == 'drums')

pipeline = TabPipeline()
result = pipeline.run(
    Path(bass),
    Path(drums),
    tab_generation_quality_mode='high_accuracy_aggressive',
)

(out_dir / 'baseline_output.alphatex').write_text(result.alphatex)
(out_dir / 'baseline_debug.json').write_text(json.dumps(result.debug_info, indent=2, sort_keys=True))
metrics = {
    'track': str(audio),
    'tempo_used': result.tempo_used,
    'raw_note_count': result.debug_info.get('raw_note_count'),
    'cleaned_note_count': result.debug_info.get('cleaned_note_count'),
    'quantized_note_count': result.debug_info.get('quantized_note_count'),
    'fingered_note_count': result.debug_info.get('fingered_note_count'),
    'suspect_silence_bars_count': result.debug_info.get('suspect_silence_bars_count', 0),
    'notes_added_second_pass': result.debug_info.get('notes_added_second_pass', 0),
    'grid_correction_applied': result.debug_info.get('grid_correction_applied'),
}
(out_dir / 'baseline_metrics.json').write_text(json.dumps(metrics, indent=2, sort_keys=True))
print(json.dumps(metrics, indent=2))
PY
```

## Baseline Artifacts

- `docs/reports/baseline_metrics.json`
- `docs/reports/baseline_debug.json`
- `docs/reports/baseline_output.alphatex`

## Note

`backend/scripts/evaluate_tab_quality.py` is not present in this branch. The baseline above uses the production TabPipeline path directly and keeps artifacts in the same report directory.
