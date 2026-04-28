from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


UTC = timezone.utc


@dataclass(slots=True)
class ScoringInput:
    freq_mhz: float
    ts_utc: datetime
    music_prob: float


@dataclass(slots=True)
class TriggerEvent:
    freq_mhz: float
    trigger_time_utc: datetime
    music_score: float


class TemporalScorer:
    """Music trigger state machine with hold-time and per-frequency cooldown."""

    def __init__(self, threshold: float, min_duration_sec: int, cooldown_sec: int) -> None:
        self.threshold = threshold
        self.min_duration = timedelta(seconds=min_duration_sec)
        self.cooldown = timedelta(seconds=cooldown_sec)
        self._started_at: dict[float, datetime] = {}
        self._last_alerted_at: dict[float, datetime] = {}

    def update(self, item: ScoringInput) -> TriggerEvent | None:
        freq = item.freq_mhz
        now = item.ts_utc

        if item.music_prob < self.threshold:
            self._started_at.pop(freq, None)
            return None

        last_alert = self._last_alerted_at.get(freq)
        if last_alert and now - last_alert < self.cooldown:
            return None

        started = self._started_at.get(freq)
        if started is None:
            self._started_at[freq] = now
            return None

        if now - started >= self.min_duration:
            self._started_at.pop(freq, None)
            self._last_alerted_at[freq] = now
            return TriggerEvent(freq_mhz=freq, trigger_time_utc=now, music_score=item.music_prob)
        return None
