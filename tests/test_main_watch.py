from argparse import Namespace
from pathlib import Path
import math
import wave

from airband_monitor.main import _iter_new_watch_frames


def _write_tone(path: Path, hz: float = 440.0, sr: int = 8000) -> None:
    n = sr // 4
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        frames = bytearray()
        for i in range(n):
            v = int(0.5 * 32767 * math.sin(2 * math.pi * hz * i / sr))
            frames.extend(int(v).to_bytes(2, "little", signed=True))
        wf.writeframes(bytes(frames))


def test_watch_only_returns_new_files(tmp_path: Path) -> None:
    args = Namespace(
        input_wav_dir=str(tmp_path),
        wav_freq=121.5,
        input_rtl_dir=None,
        rtl_default_freq=None,
    )
    seen: set[str] = set()

    _write_tone(tmp_path / "a.wav", 300.0)
    frames1, total1, new1 = _iter_new_watch_frames(args, seen)
    assert len(frames1) == 1
    assert total1 == 1
    assert new1 == 1

    frames2, total2, new2 = _iter_new_watch_frames(args, seen)
    assert len(frames2) == 0
    assert total2 == 1
    assert new2 == 0

    _write_tone(tmp_path / "b.wav", 600.0)
    frames3, total3, new3 = _iter_new_watch_frames(args, seen)
    assert len(frames3) == 1
    assert total3 == 2
    assert new3 == 1
