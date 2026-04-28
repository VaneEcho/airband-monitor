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

# rtl_fm decodes AM audio as raw signed 16-bit PCM at 48 kHz mono
# sox wraps it into a proper WAV file and trims to DURATION seconds
rtl_fm -f "${FREQ_MHZ}M" -M am -r 48000 -g 40 -E deemp | \
  sox -t raw -r 48000 -e signed -b 16 -c 1 - "$OUTFILE" trim 0 "$DURATION"

echo "Saved: $OUTFILE"
echo "Play with: afplay '$OUTFILE'"
