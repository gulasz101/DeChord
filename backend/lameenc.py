class Encoder:
    """Fallback stub for environments without binary lameenc wheels.

    Demucs imports `lameenc` unconditionally, but this app writes WAV stems only.
    MP3 encoding is not used in DeChord stem flow.
    """

    def set_bit_rate(self, _bitrate: int) -> None:
        return None

    def set_in_sample_rate(self, _samplerate: int) -> None:
        return None

    def set_channels(self, _channels: int) -> None:
        return None

    def set_quality(self, _quality: int) -> None:
        return None

    def silence(self) -> None:
        return None

    def encode(self, _pcm_bytes: bytes) -> bytes:
        raise RuntimeError("MP3 encoding is unavailable in this environment.")

    def flush(self) -> bytes:
        return b""
