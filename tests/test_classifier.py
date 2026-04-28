from pathlib import Path
import math
import wave

from airband_monitor.classifier import HeuristicAudioClassifier


def _write_sine(path: Path, freq_hz: float = 440.0, duration_s: float = 0.5, sr: int = 8000) -> None:
    n = int(duration_s * sr)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        frames = bytearray()
        for i in range(n):
            v = int(0.6 * 32767 * math.sin(2 * math.pi * freq_hz * i / sr))
            frames.extend(int(v).to_bytes(2, "little", signed=True))
        wf.writeframes(bytes(frames))


def test_classifier_returns_bounded_probability(tmp_path: Path) -> None:
    wav = tmp_path / "tone.wav"
    _write_sine(wav)

    clf = HeuristicAudioClassifier()
    prob, labels = clf.classify_music_probability(wav)

    assert 0.0 <= prob <= 1.0
    assert set(labels.keys()) == {"music", "speech"}
