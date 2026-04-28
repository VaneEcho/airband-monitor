from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import wave


@dataclass(slots=True)
class AudioFeatures:
    rms: float
    zero_cross_rate: float
    peak_ratio: float


class HeuristicAudioClassifier:
    """Lightweight fallback classifier used before YAMNet integration.

    It provides a rough music-likeness estimate for WAV chunks so we can run
    end-to-end pipelines against rtl_airband recordings without ML dependencies.
    """

    def extract_features(self, wav_path: Path) -> AudioFeatures:
        with wave.open(str(wav_path), "rb") as wf:
            n_frames = wf.getnframes()
            if n_frames == 0:
                return AudioFeatures(rms=0.0, zero_cross_rate=0.0, peak_ratio=0.0)
            n_channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            if sample_width != 2:
                raise ValueError("Only 16-bit PCM WAV is supported in heuristic classifier")

            frames = wf.readframes(n_frames)

        samples = []
        # little-endian signed int16
        for i in range(0, len(frames), sample_width * n_channels):
            # take first channel
            s = int.from_bytes(frames[i : i + 2], byteorder="little", signed=True)
            samples.append(s / 32768.0)

        if not samples:
            return AudioFeatures(rms=0.0, zero_cross_rate=0.0, peak_ratio=0.0)

        sq = 0.0
        zc = 0
        peak = 0.0
        prev = samples[0]
        peak_threshold = 0.8
        peak_count = 0

        for s in samples:
            sq += s * s
            if abs(s) > peak:
                peak = abs(s)
            if abs(s) >= peak_threshold:
                peak_count += 1
            if (prev >= 0 > s) or (prev < 0 <= s):
                zc += 1
            prev = s

        n = len(samples)
        rms = math.sqrt(sq / n)
        zcr = zc / n
        peak_ratio = peak_count / n
        return AudioFeatures(rms=rms, zero_cross_rate=zcr, peak_ratio=peak_ratio)

    def classify_music_probability(self, wav_path: Path) -> tuple[float, dict[str, float]]:
        feats = self.extract_features(wav_path)

        # Heuristic scoring (empirical fallback):
        # - moderate/high RMS suggests active content
        # - lower ZCR than white-noise-like content
        # - occasional peaks for musical transients
        score = 0.0
        score += min(1.0, feats.rms / 0.25) * 0.45
        score += max(0.0, 1.0 - min(1.0, feats.zero_cross_rate / 0.25)) * 0.35
        score += min(1.0, feats.peak_ratio / 0.02) * 0.20

        music = max(0.0, min(1.0, score))
        speech = max(0.0, min(1.0, 1.0 - music))
        labels = {
            "music": round(music, 4),
            "speech": round(speech, 4),
        }
        return labels["music"], labels
