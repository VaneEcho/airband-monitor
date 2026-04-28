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

# 参数说明：
#   -r 168000  : 请求输出采样率。168000 = 1008000/6，是整数因子，不会被
#                rtl_fm 悄悄改成其他值导致 sox 速率不匹配、输出全零。
#                窄带（如 24000）因 DC 尖峰占比过大会污染 AM 解调，需要宽带。
#   -g 0       : 自动增益控制（AGC），比手动固定增益更稳定
#   -E dc      : 直流阻断滤波器，消除 RTL-SDR 中心频率 DC 偏置尖峰
#   sox rate   : 把 168000 Hz 重采样到 48000 Hz，与下游分类器保持一致
rtl_fm -f "${FREQ_MHZ}M" -M am -r 168000 -g 0 -E dc | \
  sox -t raw -r 168000 -e signed -b 16 -c 1 - "$OUTFILE" \
    rate 48000 trim 0 "$DURATION"

echo "Saved: $OUTFILE"
echo "Play with: afplay '$OUTFILE'"
