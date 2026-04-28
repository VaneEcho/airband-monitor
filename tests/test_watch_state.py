from pathlib import Path

from airband_monitor.watch_state import WatchSeenStore


def test_watch_state_persist_roundtrip(tmp_path: Path) -> None:
    state = tmp_path / "seen.txt"
    store = WatchSeenStore(state)

    loaded = store.load()
    assert loaded == set()

    store.add_many(["/a.wav", "/b.wav"])
    store.save()

    store2 = WatchSeenStore(state)
    loaded2 = store2.load()
    assert "/a.wav" in loaded2
    assert "/b.wav" in loaded2
