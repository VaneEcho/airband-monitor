#!/usr/bin/env bash
# capture_macos.sh — RTL-SDR Blog V4 AM 录音脚本（macOS PoC）
#
# 前置条件：
#   brew install librtlsdr sox
#   rtl_biast -d 0 -b 1   # 每次重新插入 USB 后需运行，为 LNA 供电
#
# 用法：
#   ./scripts/capture_macos.sh [频率MHz] [时长秒] [输出目录] [增益dB]
#
# 示例：
#   ./scripts/capture_macos.sh 127.5 60 test_audio/live        # 录民航频率
#   ./scripts/capture_macos.sh 127.5 60 test_audio/live 28     # 增益调低减少互调
#   ./scripts/capture_macos.sh 89.0  30 test_audio/music_inject # FM广播（音乐注入测试）
#
# RTL-SDR Blog V4 / R828D 关键参数说明：
#
#   增益（-g）：
#     - 民航频段建议 28-35 dB（不要超过 40）
#     - 增益过高会因 FM 广播互调（IMD）在民航频段产生大量假信号
#     - V4 文档明确禁止使用 IF AGC（-g 0），须手动设置
#     - 可用值（dB）: 0 0.9 1.4 2.7 3.7 7.7 8.7 12.5 14.4 15.7 16.6
#                     19.7 20.7 22.9 25.4 28.0 29.7 32.8 33.8 36.4 37.2
#                     38.6 40.2 42.1 43.4 43.9 44.5 48.0 49.6
#
#   采样率（-r 168000）：
#     - 168000 = 1008000/6，整数因子，rtl_fm 不会悄悄修改
#     - 非整数因子（如 170000、180000）会被修改导致 sox 速率不匹配、全零输出
#     - 窄带（24000 Hz）时 DC 偏置尖峰占带宽比例过大，污染 AM 解调
#
#   DC 阻断（-E dc）：
#     - 消除 RTL-SDR 本振泄漏在中心频率产生的直流尖峰
#     - R828D 不支持 offset tuning（-E offset 会报错），故用 dc 替代
#
#   去加重（-E deemp）：
#     - 仅用于 FM 广播，会削掉语音高频
#     - 民航 AM 通话不使用，已移除
#
#   Bias-T（rtl_biast）：
#     - V4 输出 4.5V / 最大 180mA，为外接 LNA 供电
#     - 每次拔插 USB 后需重新开启，状态不持久
#     - 带 LNA 时不开 Bias-T 会导致灵敏度严重下降

set -euo pipefail

FREQ_MHZ="${1:-127.5}"
DURATION="${2:-60}"
OUTPUT_DIR="${3:-test_audio/live}"
GAIN="${4:-32}"   # 默认 32 dB，如假信号多则降至 28

mkdir -p "$OUTPUT_DIR"
OUTFILE="$OUTPUT_DIR/${FREQ_MHZ}_$(date +%s).wav"

echo "录制 ${FREQ_MHZ} MHz AM，时长 ${DURATION}s，增益 ${GAIN} dB → $OUTFILE"
echo "Ctrl+C 提前停止"

rtl_fm -f "${FREQ_MHZ}M" -M am -r 168000 -g "$GAIN" -E dc | \
  sox -t raw -r 168000 -e signed -b 16 -c 1 - "$OUTFILE" \
    rate 48000 trim 0 "$DURATION"

echo ""
echo "完成：$OUTFILE"
MAX=$(sox "$OUTFILE" -n stat 2>&1 | awk '/Maximum amplitude/{print $3}')
echo "最大振幅：$MAX（>0.01 说明有内容，<0.005 基本是纯噪底）"
echo "试听：afplay '$OUTFILE'"
