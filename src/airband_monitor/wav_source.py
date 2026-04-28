from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .classifier import HeuristicAudioClassifier
from .ingest import InferenceFrame

UTC = timezone.utc


class WavDirectorySource:
    def __init__(self, directory: Path, freq_mhz: float, classifier: HeuristicAudioClassifier | None = None) -> None:
        self.directory = directory
        self.freq_mhz = freq_mhz
        self.classifier = classifier or HeuristicAudioClassifier()

    def list_files(self) -> list[Path]:
        if not self.directory.exists():
            return []
        return sorted(self.directory.glob("*.wav"), key=lambda p: p.stat().st_mtime)

    def frames_from_files(self, wav_files: Iterable[Path]) -> Iterable[InferenceFrame]:
        for wav_path in wav_files:
            prob, labels = self.classifier.classify_music_probability(wav_path)
            ts = datetime.fromtimestamp(wav_path.stat().st_mtime, tz=UTC)
            yield InferenceFrame(
                ts_utc=ts,
                freq_mhz=self.freq_mhz,
                music_prob=prob,
                labels=labels,
                audio_path=str(wav_path),
                iq_path="",
            )

    def read(self) -> Iterable[InferenceFrame]:
        return self.frames_from_files(self.list_files())
