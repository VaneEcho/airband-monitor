from datetime import datetime, timezone
from pathlib import Path

from airband_monitor.recorder import ArtifactRecorder


UTC = timezone.utc


def test_recorder_writes_artifacts_and_meta(tmp_path: Path) -> None:
    recorder = ArtifactRecorder(tmp_path / "artifacts", "site-gz-001")
    bundle = recorder.record(
        event_id="evt-1",
        freq_mhz=121.5,
        trigger_time_utc=datetime(2026, 4, 27, tzinfo=UTC),
        labels={"music": 0.91},
        source_audio_path="",
        source_iq_path="",
    )

    assert bundle.meta_json_path.exists()
    assert bundle.spectrum_png_path.exists()
    assert bundle.audio_path.exists()
    assert bundle.iq_path.exists()
