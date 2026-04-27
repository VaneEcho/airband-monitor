from pathlib import Path

from airband_monitor.storage import EventRecord, EventStore


def test_list_recent_returns_desc_order(tmp_path: Path) -> None:
    store = EventStore(tmp_path / "events.db")
    store.insert(
        EventRecord(
            id="evt-old",
            site_id="site-gz-001",
            freq_mhz=119.6,
            start_time_utc="2026-01-01T00:00:00+00:00",
            end_time_utc="2026-01-01T00:02:00+00:00",
            duration_sec=120,
            music_score_max=0.71,
            labels_json='{"music": 0.71}',
            iq_path="/tmp/a.iq",
            audio_path="/tmp/a.wav",
            spectrum_png_path="/tmp/a.png",
            meta_json_path="/tmp/a.json",
            alert_status="sent",
        )
    )
    store.insert(
        EventRecord(
            id="evt-new",
            site_id="site-gz-001",
            freq_mhz=121.5,
            start_time_utc="2026-01-02T00:00:00+00:00",
            end_time_utc="2026-01-02T00:02:00+00:00",
            duration_sec=120,
            music_score_max=0.91,
            labels_json='{"music": 0.91}',
            iq_path="/tmp/b.iq",
            audio_path="/tmp/b.wav",
            spectrum_png_path="/tmp/b.png",
            meta_json_path="/tmp/b.json",
            alert_status="sent",
        )
    )

    recents = store.list_recent(limit=2)
    assert recents[0].id == "evt-new"
    assert recents[1].id == "evt-old"
