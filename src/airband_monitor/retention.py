from __future__ import annotations

from pathlib import Path
import shutil


class WatermarkRetention:
    def __init__(self, artifact_root: Path, start_percent: int, stop_percent: int) -> None:
        if stop_percent >= start_percent:
            raise ValueError("stop_percent must be less than start_percent")
        self.artifact_root = artifact_root
        self.start_percent = start_percent
        self.stop_percent = stop_percent

    def _usage_percent(self) -> float:
        usage = shutil.disk_usage(self.artifact_root)
        return usage.used / usage.total * 100

    def run_cleanup(self) -> list[Path]:
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        if self._usage_percent() < self.start_percent:
            return []

        deleted: list[Path] = []
        candidates = sorted(
            [p for p in self.artifact_root.iterdir() if p.is_dir()],
            key=lambda p: p.stat().st_mtime,
        )

        for directory in candidates:
            shutil.rmtree(directory, ignore_errors=True)
            deleted.append(directory)
            if self._usage_percent() <= self.stop_percent:
                break

        return deleted
