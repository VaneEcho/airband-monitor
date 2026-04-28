from pathlib import Path
import math
import wave

from airband_monitor.rtl_airband_source import RtlAirbandRecordingSource


def _write_tone(path: Path, freq_hz: float = 440.0, sr: int = 8000) -> None:
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


def test_infer_frequency_from_filename() -> None:
    assert RtlAirbandRecordingSource.infer_frequency_from_name("tower_121.500_foo.wav") == 121.5
    assert RtlAirbandRecordingSource.infer_frequency_from_name("chan_119600000.wav") == 119.6
    assert RtlAirbandRecordingSource.infer_frequency_from_name("no_freq.wav") is None


def test_rtl_source_reads_wav_and_uses_default_freq(tmp_path: Path) -> None:
    _write_tone(tmp_path / "unknown_name.wav")
    src = RtlAirbandRecordingSource(tmp_path, default_freq_mhz=120.35)
    frames = list(src.read())

    assert len(frames) == 1
    assert frames[0].freq_mhz == 120.35
