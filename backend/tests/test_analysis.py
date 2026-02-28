import tempfile
from pathlib import Path
from app.analysis import _adjust_tempo, _cache_path, Chord


def test_adjust_tempo_normal():
    assert _adjust_tempo(120) == 120


def test_adjust_tempo_too_slow():
    assert _adjust_tempo(35) == 70  # 35 * 2 = 70


def test_adjust_tempo_too_fast():
    assert _adjust_tempo(240) == 120  # 240 / 2 = 120


def test_cache_path_deterministic():
    p1 = _cache_path("/some/file.mp3", "chord")
    p2 = _cache_path("/some/file.mp3", "chord")
    assert p1 == p2


def test_cache_path_different_categories():
    p1 = _cache_path("/some/file.mp3", "chord")
    p2 = _cache_path("/some/file.mp3", "key")
    assert p1 != p2
    assert "chord" in str(p1)
    assert "key" in str(p2)
