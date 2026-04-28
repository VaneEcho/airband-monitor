#!/usr/bin/env bash
# capture_macos.sh — RTL-SDR AM capture helper for macOS PoC
#
# Prerequisites:
#   brew install librtlsdr sox
#
# Usage:
#   ./scripts/capture_macos.sh [FREQ_MHZ] [DURATION_SEC] [OUTPUT_DIR]
#
# Examples:
#   ./scripts/capture_macos.sh 121.5 30 test_audio/live
#   ./scripts/capture_macos.sh 89.0 30 test_audio/music_inject   # FM broadcast for music test

set -euo pipefail

FREQ_MHZ="${1:-121.5}"
DURATION="${2:-30}"
OUTPUT_DIR="${3:-test_audio/live}"

mkdir -p "$OUTPUT_DIR"

OUTFILE="$OUTPUT_DIR/${FREQ_MHZ}_$(date +%s).wav"

echo "Capturing ${FREQ_MHZ} MHz AM for ${DURATION}s → $OUTFILE"
echo "Press Ctrl+C to stop early."

# rtl_fm 请求 48000 Hz，但受限于 RTL-SDR 过采样比，实际输出约 24000 Hz。
# sox 的 -r 参数必须与 rtl_fm 实际输出率一致，否则得到全零静音文件。
# 通过 sox rate 24000→48000 重采样，保证下游管道统一使用 48000 Hz。
rtl_fm -f "${FREQ_MHZ}M" -M am -r 24000 -g 40 -E deemp | \
  sox -t raw -r 24000 -e signed -b 16 -c 1 - "$OUTFILE" \
    rate 48000 trim 0 "$DURATION"

echo "Saved: $OUTFILE"
echo "Play with: afplay '$OUTFILE'"
