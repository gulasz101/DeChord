# 2026-03-07 Pipeline Stage Analysis

## Run context

- Command mode: `--quality standard --config baseline --trace-pipeline`
- Songs: `Muse - Hysteria`, `Iron Maiden - The Trooper`
- Reference note counts from benchmark metrics:
  - `Muse - Hysteria`: `1339`
  - `Iron Maiden - The Trooper`: `1619`

## Stage counts

| Song | Basic Pitch raw | After stabilization | After admission | Dense candidates | Dense accepted | Final quantized |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Muse - Hysteria | 92 | 92 | 92 | 0 | 0 | 41 |
| Iron Maiden - The Trooper | 337 | 337 | 337 | 0 | 0 | 407 |

## Required answers

1. How many notes are produced by Basic Pitch?
   - `Muse - Hysteria`: `92`
   - `Iron Maiden - The Trooper`: `337`
2. How many survive stabilization?
   - `Muse - Hysteria`: `92`
   - `Iron Maiden - The Trooper`: `337`
3. How many are removed by admission rules?
   - `Muse - Hysteria`: `0`
   - `Iron Maiden - The Trooper`: `0`
4. How many are added by dense-note recovery?
   - `Muse - Hysteria`: `0`
   - `Iron Maiden - The Trooper`: `0`
5. How many final notes reach the tab pipeline?
   - `Muse - Hysteria`: `41`
   - `Iron Maiden - The Trooper`: `407`

## Interpretation

- The benchmark gap is already present at stage 1. Basic Pitch raw output under-generates heavily before any downstream filtering:
  - `Muse - Hysteria`: raw deficit vs reference = `1247` notes (`1339 - 92`)
  - `Iron Maiden - The Trooper`: raw deficit vs reference = `1282` notes (`1619 - 337`)
- Pitch stabilization does not explain the gap on these runs. It preserved the stage-1 note counts for both songs.
- Conservative admission does not explain the gap on these runs. It removed `0` notes for both songs.
- Dense-note recovery does not explain the gap in the benchmark configuration because it was not activated in `standard` mode; both dense stages remained `0`.
- Final cleanup/quantization changes the count downstream, but that happens after the dominant loss is already locked in:
  - `Muse - Hysteria`: `92 -> 41`
  - `Iron Maiden - The Trooper`: `337 -> 407`

## Bottleneck

The single stage responsible for the largest note loss is `basic_pitch_raw`. The benchmark shortfall versus the GP5 references is overwhelmingly upstream of stabilization, admission, dense-note recovery, and tab-generation cleanup.
