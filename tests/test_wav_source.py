from pathlib import Path
import math
import wave

from airband_monitor.wav_source import WavDirectorySource


def _write_tone(path: Path, freq_hz: float, sr: int = 8000) -> None:
    n = sr // 4
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        frames = bytearray()
        for i in range(n):
            v = int(0.5 * 32767 * math.sin(2 * math.pi * freq_hz * i / sr))
            frames.extend(int(v).to_bytes(2, "little", signed=True))
        wf.writeframes(bytes(frames))


def test_wav_source_reads_frames(tmp_path: Path) -> None:
    _write_tone(tmp_path / "a.wav", 300.0)
    _write_tone(tmp_path / "b.wav", 600.0)

    source = WavDirectorySource(tmp_path, freq_mhz=121.5)
    frames = list(source.read())

    assert len(frames) == 2
    assert all(f.freq_mhz == 121.5 for f in frames)
    assert all(0.0 <= f.music_prob <= 1.0 for f in frames)
