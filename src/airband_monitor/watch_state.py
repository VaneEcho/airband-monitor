from __future__ import annotations

from pathlib import Path


class WatchSeenStore:
    """Persistent seen-file tracker for watch mode restarts."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._seen: set[str] = set()

    def load(self) -> set[str]:
        if not self.path.exists():
            self._seen = set()
            return self._seen

        lines = self.path.read_text(encoding="utf-8").splitlines()
        self._seen = {line.strip() for line in lines if line.strip()}
        return self._seen

    def add_many(self, files: list[str]) -> None:
        self._seen.update(files)

    def save(self) -> None:
        content = "\n".join(sorted(self._seen))
        self.path.write_text(content + ("\n" if content else ""), encoding="utf-8")

    @property
    def seen(self) -> set[str]:
        return self._seen
