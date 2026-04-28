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

## Current Implementation Status

This repository now includes a runnable v0.1 scaffold:

- Config loader (`configs/default.yaml` + env override for `WECOM_WEBHOOK`)
- Temporal music scoring with hold-time and cooldown
- SQLite event persistence
- Artifact recorder (`audio/iq/spectrum/meta`)
- WeCom notifier (dry-run supported)
- Multiple runtime sources: simulate / JSONL file / STDIN JSONL / WAV directory fallback / rtl_airband recordings
- Event query mode: list recent events from SQLite

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e . --no-build-isolation

# Dry-run simulated pipeline (no SDR required)
python -m airband_monitor.main --simulate

# Replay model output frames from file
python -m airband_monitor.main --input-jsonl examples/frames.jsonl

# Query recent events
python -m airband_monitor.main --list-events 10

# Classify existing WAV chunks (fallback heuristic)
python -m airband_monitor.main --input-wav-dir /path/to/wav --wav-freq 121.5

# Ingest rtl_airband recording directory (freq inferred from filename if possible)
python -m airband_monitor.main --input-rtl-dir /path/to/rtl_recordings --rtl-default-freq 121.5

# Watch mode for continuous ingest (new files only)
python -m airband_monitor.main --input-rtl-dir /path/to/rtl_recordings --watch --poll-interval 2 --watch-state-file data/watch_seen_files.txt --classifier-backend auto
```

The pipeline persists events to `data/events.db` and artifacts to `data/artifacts/`.

## Runtime Input Contract (JSONL)

Each line should be one JSON object:

```json
{"ts_utc":"2026-04-27T14:30:00+00:00","freq_mhz":121.5,"music_prob":0.83,"labels":{"music":0.83},"audio_path":"/path/chunk.wav","iq_path":"/path/chunk.iq"}
```

This makes it easy to bridge external inference pipelines (rtl_airband + classifier sidecar) into this eventing core.



## rtl_airband Recording Mode

`--input-rtl-dir` scans WAV recordings (recursive) and tries to infer frequency from filename patterns:

- decimal MHz: `121.500`
- Hz integer: `121500000`

If frequency cannot be inferred, it uses `--rtl-default-freq` when provided.

Watch mode details:
- `--watch` works with `--input-wav-dir` or `--input-rtl-dir`
- only newly discovered WAV files are processed per poll
- `--max-loops N` can be used for bounded runs in testing
- seen file persistence avoids duplicate processing across restarts (`--watch-state-file`)
- each loop prints summary logs: total files, new files, triggered events

## WAV Directory Fallback Mode

For early rtl_airband integration (before YAMNet sidecar wiring), you can point the pipeline to a WAV directory.
Each `*.wav` file is heuristically scored and converted into ingestion frames automatically.

This mode is for bring-up only; YAMNet should replace it for production detection quality.

Classifier backend options:
- `--classifier-backend auto` (default): use YAMNet if available, else fallback heuristic
- `--classifier-backend yamnet`: force YAMNet (requires tensorflow/tensorflow_hub/scipy)
- `--classifier-backend heuristic`: force lightweight fallback

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
