from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from .spectrum import tiny_png

UTC = timezone.utc


@dataclass(slots=True)
class ArtifactBundle:
    event_dir: Path
    meta_json_path: Path
    spectrum_png_path: Path
    audio_path: Path
    iq_path: Path


class ArtifactRecorder:
    def __init__(self, artifact_root: Path, site_id: str) -> None:
        self.artifact_root = artifact_root
        self.site_id = site_id
        self.artifact_root.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        event_id: str,
        freq_mhz: float,
        trigger_time_utc: datetime,
        labels: dict[str, float],
        source_audio_path: str,
        source_iq_path: str,
    ) -> ArtifactBundle:
        event_dir = self.artifact_root / trigger_time_utc.strftime("%Y%m%d") / event_id
        event_dir.mkdir(parents=True, exist_ok=True)

        copied_audio = event_dir / "audio.wav"
        copied_iq = event_dir / "capture.iq"
        spectrum_png = event_dir / "spectrum.png"
        meta_json = event_dir / "meta.json"

        self._copy_or_placeholder(source_audio_path, copied_audio, b"")
        self._copy_or_placeholder(source_iq_path, copied_iq, b"")

        spectrum_png.write_bytes(tiny_png(level=labels.get("music", 0.5)))

        meta = {
            "event_id": event_id,
            "site_id": self.site_id,
            "freq_mhz": freq_mhz,
            "trigger_time_utc": trigger_time_utc.astimezone(UTC).isoformat(),
            "labels": labels,
            "artifacts": {
                "audio": str(copied_audio),
                "iq": str(copied_iq),
                "spectrum_png": str(spectrum_png),
            },
        }
        meta_json.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        return ArtifactBundle(
            event_dir=event_dir,
            meta_json_path=meta_json,
            spectrum_png_path=spectrum_png,
            audio_path=copied_audio,
            iq_path=copied_iq,
        )

    @staticmethod
    def _copy_or_placeholder(source: str, target: Path, placeholder: bytes) -> None:
        if source:
            src = Path(source)
            if src.exists() and src.is_file():
                shutil.copy2(src, target)
                return
        target.write_bytes(placeholder)
