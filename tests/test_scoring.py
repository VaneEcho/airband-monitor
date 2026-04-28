from datetime import datetime, timedelta, timezone

from airband_monitor.scoring import ScoringInput, TemporalScorer


UTC = timezone.utc


def test_triggers_after_min_duration_and_respects_cooldown() -> None:
    scorer = TemporalScorer(threshold=0.7, min_duration_sec=5, cooldown_sec=10)
    t0 = datetime(2026, 1, 1, tzinfo=UTC)

    out = None
    for i in range(6):
        out = scorer.update(ScoringInput(freq_mhz=121.5, ts_utc=t0 + timedelta(seconds=i), music_prob=0.8))
    assert out is not None

    blocked = scorer.update(ScoringInput(freq_mhz=121.5, ts_utc=t0 + timedelta(seconds=8), music_prob=0.9))
    assert blocked is None
