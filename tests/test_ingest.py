from pathlib import Path

from airband_monitor.ingest import JsonlInferenceSource


def test_jsonl_ingest_parses_labels(tmp_path: Path) -> None:
    src = tmp_path / "frames.jsonl"
    src.write_text(
        '{"ts_utc":"2026-04-27T12:00:00+00:00","freq_mhz":121.5,"music_prob":0.9,"labels":{"music":0.9}}\n',
        encoding="utf-8",
    )

    frames = list(JsonlInferenceSource(src).read())
    assert len(frames) == 1
    assert frames[0].freq_mhz == 121.5
    assert frames[0].labels["music"] == 0.9
