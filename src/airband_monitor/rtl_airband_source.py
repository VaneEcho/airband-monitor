from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Iterable

from .classifier import HeuristicAudioClassifier
from .ingest import InferenceFrame

UTC = timezone.utc


class RtlAirbandRecordingSource:
    """Read rtl_airband WAV recording outputs and emit inference frames."""

    # examples matched: 121.500, 121500000, 119600000
    _freq_decimal = re.compile(r"(?<!\d)(1\d{2}\.\d{1,3})(?!\d)")
    _freq_hz = re.compile(r"(?<!\d)(1\d{8})(?!\d)")

    def __init__(
        self,
        directory: Path,
        default_freq_mhz: float | None = None,
        recursive: bool = True,
        classifier: HeuristicAudioClassifier | None = None,
    ) -> None:
        self.directory = directory
        self.default_freq_mhz = default_freq_mhz
        self.recursive = recursive
        self.classifier = classifier or HeuristicAudioClassifier()

    @classmethod
    def infer_frequency_from_name(cls, name: str) -> float | None:
        m = cls._freq_decimal.search(name)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                return None

        mhz = cls._freq_hz.search(name)
        if mhz:
            return int(mhz.group(1)) / 1_000_000.0

        return None

    def list_files(self) -> list[Path]:
        if not self.directory.exists():
            return []
        pattern = "**/*.wav" if self.recursive else "*.wav"
        return sorted(self.directory.glob(pattern), key=lambda p: p.stat().st_mtime)

    def frames_from_files(self, files: Iterable[Path]) -> Iterable[InferenceFrame]:
        for wav_path in files:
            if wav_path.stat().st_size <= 44:  # empty wav header-ish
                continue

            freq = self.infer_frequency_from_name(wav_path.name)
            if freq is None:
                freq = self.default_freq_mhz
            if freq is None:
                continue

            prob, labels = self.classifier.classify_music_probability(wav_path)
            ts = datetime.fromtimestamp(wav_path.stat().st_mtime, tz=UTC)
            yield InferenceFrame(
                ts_utc=ts,
                freq_mhz=freq,
                music_prob=prob,
                labels=labels,
                audio_path=str(wav_path),
                iq_path="",
            )

    def read(self) -> Iterable[InferenceFrame]:
        return self.frames_from_files(self.list_files())
