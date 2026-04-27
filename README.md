# airband-monitor

Detect anomalous music/broadcast intrusion on civil aviation VHF channels.

## Problem

In normal ATC VHF AM communications, sustained music or broadcast-like content is highly abnormal. This project builds a practical, low-cost monitoring pipeline to detect those events and preserve evidence automatically.

## Scope (v0.1 PoC)

- Fixed-frequency monitoring (no scanning in v0.1)
- Single SDR device for initial validation (`RTL-SDR`)
- AM demodulation via `rtl_airband`
- Audio classification via `YAMNet`
- WeCom webhook alerting
- Evidence capture: audio + IQ + spectrum PNG + metadata JSON
- Local metadata DB: SQLite
- Retention: keep forever until disk watermark-based cleanup

## Target Frequencies (v0.1)

- 119.600 MHz
- 119.700 MHz
- 119.900 MHz
- 120.350 MHz
- 120.400 MHz
- 121.500 MHz

## Architecture

```text
SDR (RTL-SDR in PoC; pluggable backend later)
  -> rtl_airband (multi-channel AM demod)
  -> audio ingest
  -> energy/VAD gate
  -> YAMNet classifier
  -> event scorer & suppressor
  -> evidence recorder (IQ/audio/spectrum/metadata)
  -> WeCom alert
  -> SQLite + file storage
```

## Detection Strategy (v0.1 defaults)

1. Light pre-gate by energy/VAD.
2. Run YAMNet inference on active audio windows.
3. Trigger event when `music_like_prob >= 0.70` continuously for `>= 5s`.
4. De-duplicate alerts per frequency in a 120s cooldown window.

Design preference: **prefer false positives over misses** in early stage.

## Evidence Policy

- IQ ring buffer: 120s
- Event save window: pre-trigger 30s + post-trigger 90s
- Spectrum output: one static PNG per event
- Metadata fields (minimum):
  - site_id
  - frequency
  - trigger_time_utc
  - trigger_time_local (UTC+8)
  - duration_sec
  - top_labels/probabilities
  - artifact paths

## Storage & Retention

- SQLite for metadata index.
- Filesystem for IQ/audio/PNG/JSON artifacts.
- Retention rule (default):
  - Start cleanup when disk usage > 85%
  - Stop cleanup when disk usage < 75%
  - Delete oldest events first

## Environments

- Development PoC: Windows + WSL
- Production target: Linux x86_64 (N100 mini PC preferred)
- ARM64 (e.g., Orange Pi) supported later as secondary target

## Roadmap

- v0.1: RTL-SDR + rtl_airband + YAMNet + WeCom + evidence capture
- v0.2: Add carrier-offset and duty-cycle signal heuristics
- v0.3: Add FM correlation enhancement and improved suppression
- v1.0: Multi-node deployment and event federation

See implementation plan in [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md).
