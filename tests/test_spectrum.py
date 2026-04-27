from airband_monitor.spectrum import tiny_png


def test_tiny_png_header() -> None:
    data = tiny_png(width=16, height=8, level=0.7)
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(data) > 40
