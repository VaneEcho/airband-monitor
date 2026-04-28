from __future__ import annotations

import struct
import zlib


def tiny_png(width: int = 64, height: int = 32, level: float = 0.5) -> bytes:
    """Generate a small valid grayscale PNG as placeholder spectrum image."""
    width = max(1, int(width))
    height = max(1, int(height))
    level = max(0.0, min(1.0, float(level)))

    pixels = []
    peak_col = int((width - 1) * level)
    for _ in range(height):
        row = bytearray([0])  # filter type 0
        for x in range(width):
            # simple ridge-like intensity profile around peak_col
            dist = abs(x - peak_col)
            val = max(0, 255 - dist * 16)
            row.append(val)
        pixels.append(bytes(row))

    raw = b"".join(pixels)
    compressed = zlib.compress(raw, level=9)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)
        ) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")
