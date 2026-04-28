from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Iterable

UTC = timezone.utc


@dataclass(slots=True)
class InferenceFrame:
    ts_utc: datetime
    freq_mhz: float
    music_prob: float
    labels: dict[str, float]
    audio_path: str = ""
    iq_path: str = ""


class JsonlInferenceSource:
    """Reads inference frames from JSONL.

    Expected line format:
    {
      "ts_utc": "2026-04-27T14:30:00+00:00",
      "freq_mhz": 121.5,
      "music_prob": 0.83,
      "labels": {"music": 0.83, "speech": 0.02},
      "audio_path": "/tmp/chunk.wav",
      "iq_path": "/tmp/chunk.iq"
    }
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self) -> Iterable[InferenceFrame]:
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                yield _parse_line(line)


class StdinInferenceSource:
    def read(self) -> Iterable[InferenceFrame]:
        import sys

        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            yield _parse_line(line)



def _parse_line(line: str) -> InferenceFrame:
    payload = json.loads(line)
    ts = datetime.fromisoformat(payload["ts_utc"])
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)

    labels = payload.get("labels") or {"music": float(payload["music_prob"])}
    return InferenceFrame(
        ts_utc=ts.astimezone(UTC),
        freq_mhz=float(payload["freq_mhz"]),
        music_prob=float(payload["music_prob"]),
        labels={str(k): float(v) for k, v in labels.items()},
        audio_path=str(payload.get("audio_path", "")),
        iq_path=str(payload.get("iq_path", "")),
    )
