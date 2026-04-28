from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3


SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    site_id TEXT NOT NULL,
    freq_mhz REAL NOT NULL,
    start_time_utc TEXT NOT NULL,
    end_time_utc TEXT NOT NULL,
    duration_sec REAL NOT NULL,
    music_score_max REAL NOT NULL,
    labels_json TEXT NOT NULL,
    iq_path TEXT NOT NULL,
    audio_path TEXT NOT NULL,
    spectrum_png_path TEXT NOT NULL,
    meta_json_path TEXT NOT NULL,
    alert_status TEXT NOT NULL
);
"""


@dataclass(slots=True)
class EventRecord:
    id: str
    site_id: str
    freq_mhz: float
    start_time_utc: str
    end_time_utc: str
    duration_sec: float
    music_score_max: float
    labels_json: str
    iq_path: str
    audio_path: str
    spectrum_png_path: str
    meta_json_path: str
    alert_status: str


class EventStore:
    def __init__(self, sqlite_path: Path) -> None:
        self.sqlite_path = sqlite_path
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as con:
            con.execute(SCHEMA)

    def connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.sqlite_path)

    def insert(self, event: EventRecord) -> None:
        with self.connect() as con:
            con.execute(
                """
                INSERT INTO events (
                    id, site_id, freq_mhz, start_time_utc, end_time_utc, duration_sec,
                    music_score_max, labels_json, iq_path, audio_path,
                    spectrum_png_path, meta_json_path, alert_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.site_id,
                    event.freq_mhz,
                    event.start_time_utc,
                    event.end_time_utc,
                    event.duration_sec,
                    event.music_score_max,
                    event.labels_json,
                    event.iq_path,
                    event.audio_path,
                    event.spectrum_png_path,
                    event.meta_json_path,
                    event.alert_status,
                ),
            )

    def count(self) -> int:
        with self.connect() as con:
            row = con.execute("SELECT COUNT(*) FROM events").fetchone()
            return int(row[0])

    def list_recent(self, limit: int = 20) -> list[EventRecord]:
        with self.connect() as con:
            rows = con.execute(
                """
                SELECT id, site_id, freq_mhz, start_time_utc, end_time_utc, duration_sec,
                       music_score_max, labels_json, iq_path, audio_path,
                       spectrum_png_path, meta_json_path, alert_status
                FROM events
                ORDER BY start_time_utc DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [EventRecord(*row) for row in rows]
