from pathlib import Path

from airband_monitor.storage import EventRecord, EventStore


def test_store_insert_and_count(tmp_path: Path) -> None:
    db = tmp_path / "events.db"
    store = EventStore(db)

    store.insert(
        EventRecord(
            id="evt-1",
            site_id="site-gz-001",
            freq_mhz=121.5,
            start_time_utc="2026-01-01T00:00:00+00:00",
            end_time_utc="2026-01-01T00:02:00+00:00",
            duration_sec=120.0,
            music_score_max=0.9,
            labels_json='{"music": 0.9}',
            iq_path="/tmp/evt-1.iq",
            audio_path="/tmp/evt-1.wav",
            spectrum_png_path="/tmp/evt-1.png",
            meta_json_path="/tmp/evt-1.json",
            alert_status="sent",
        )
    )

    assert store.count() == 1
