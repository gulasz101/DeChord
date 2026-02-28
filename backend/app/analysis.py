import hashlib
from pathlib import Path
from dataclasses import dataclass

CACHE_DIR = Path("cache")


@dataclass
class Chord:
    start: float
    end: float
    label: str


@dataclass
class AnalysisResult:
    key: str
    tempo: int
    chords: list[Chord]
    duration: float


def _cache_path(audio_path: str, category: str) -> Path:
    hash_hex = hashlib.md5(audio_path.encode()).hexdigest()
    return CACHE_DIR / category / f"{hash_hex}.txt"


def detect_chords(audio_path: str) -> list[Chord]:
    cache_file = _cache_path(audio_path, "chord")
    cache_file.parent.mkdir(parents=True, exist_ok=True)

    if cache_file.exists():
        chords = []
        for line in cache_file.read_text().strip().split("\n"):
            if not line:
                continue
            start, end, label = line.split(",", 2)
            chords.append(Chord(float(start), float(end), label))
        return chords

    import madmom

    feat_processor = madmom.features.chords.CNNChordFeatureProcessor()
    recog_processor = madmom.features.chords.CRFChordRecognitionProcessor()
    feats = feat_processor(audio_path)
    raw_chords = recog_processor(feats)

    chords = []
    lines = []
    for start_time, end_time, chord_label in raw_chords:
        if ":maj" in chord_label:
            chord_label = chord_label.replace(":maj", "")
        elif ":min" in chord_label:
            chord_label = chord_label.replace(":min", "m")
        chords.append(Chord(start_time, end_time, chord_label))
        lines.append(f"{start_time},{end_time},{chord_label}")

    cache_file.write_text("\n".join(lines) + "\n")
    return chords


def detect_key(audio_path: str) -> str:
    cache_file = _cache_path(audio_path, "key")
    cache_file.parent.mkdir(parents=True, exist_ok=True)

    if cache_file.exists():
        return cache_file.read_text().strip()

    try:
        import madmom

        key_processor = madmom.features.key.CNNKeyRecognitionProcessor()
        key_prediction = key_processor(audio_path)
        key = madmom.features.key.key_prediction_to_label(key_prediction)
        cache_file.write_text(key)
        return key
    except Exception:
        return "Error"


def _adjust_tempo(tempo: float) -> float:
    while tempo < 70:
        tempo *= 2
    while tempo > 190:
        tempo /= 2
    return tempo


def detect_tempo(audio_path: str) -> int:
    cache_file = _cache_path(audio_path, "tempo")
    cache_file.parent.mkdir(parents=True, exist_ok=True)

    if cache_file.exists():
        return int(cache_file.read_text().strip())

    from madmom.features.beats import RNNBeatProcessor
    from madmom.features.tempo import TempoEstimationProcessor

    beat_processor = RNNBeatProcessor()
    beats = beat_processor(audio_path)
    tempo_processor = TempoEstimationProcessor(fps=200)
    tempos = tempo_processor(beats)

    if len(tempos):
        top_tempo = tempos[0][0]
        adjusted = _adjust_tempo(top_tempo)
        result = round(adjusted)
        cache_file.write_text(str(result))
        return result
    return 0


def get_audio_duration(audio_path: str) -> float:
    """Get audio duration in seconds using madmom's Signal."""
    import madmom

    sig = madmom.audio.signal.Signal(audio_path)
    return len(sig) / sig.sample_rate


def analyze_audio(audio_path: str) -> AnalysisResult:
    """Run all three analyses and return combined result."""
    chords = detect_chords(audio_path)
    key = detect_key(audio_path)
    tempo = detect_tempo(audio_path)
    duration = chords[-1].end if chords else get_audio_duration(audio_path)

    return AnalysisResult(
        key=key,
        tempo=tempo,
        chords=chords,
        duration=duration,
    )
