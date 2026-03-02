from dataclasses import dataclass
from typing import Literal

ProcessMode = Literal["analysis_only", "analysis_and_stems"]


@dataclass
class Song:
    id: int
    user_id: int
    title: str
    original_filename: str | None
    mime_type: str | None


@dataclass
class Note:
    id: int
    song_id: int
    type: str
    text: str
    timestamp_sec: float | None = None
    chord_index: int | None = None
    toast_duration_sec: float | None = None
