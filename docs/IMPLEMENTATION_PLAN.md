# airband-monitor Implementation Plan

## 1) Objectives

Build a practical and maintainable civil aviation VHF interference monitor focused on detecting music/broadcast-like intrusion in ATC channels.

## 2) Frozen v0.1 Decisions

- Device: single RTL-SDR for PoC
- Fixed frequencies:
  - 119.6 / 119.7 / 119.9 / 120.35 / 120.4 / 121.5 MHz
- Primary anomaly: `music`
- Secondary best-effort: `broadcast/radio-like` classes
- Alert channel: WeCom webhook
- Runtime preference: high recall (allow more false positives)
- Ring buffer and clip policy:
  - IQ ring: 120s
  - event export: -30s to +90s
- Storage:
  - metadata: SQLite
  - artifacts: filesystem
  - retention: watermark cleanup (85% -> 75%)
- Dev env: WSL
- Deploy target: N100 Linux first, ARM later

## 3) Non-Goals (v0.1)

- Full-band scan orchestration
- TDoA multi-node localization
- High-fidelity interference source attribution
- Rich front-end dashboard

## 4) Proposed Repository Layout

```text
airband-monitor/
├── ingest/
│   ├── rtl_airband/
│   └── iq_buffer/
├── classifier/
│   ├── yamnet/
│   └── scoring/
├── events/
│   ├── recorder/
│   └── retention/
├── alert/
│   └── wecom/
├── api/
│   └── fastapi/
├── storage/
│   ├── sqlite/
│   └── artifacts/
├── configs/
└── docs/
```

## 5) Event State Machine (v0.1)

1. **idle**: no active audio above gate.
2. **candidate**: active audio + YAMNet music-like probability rising.
3. **confirmed**: threshold satisfied (`>=0.7` for 5s).
4. **recording**: export IQ/audio/spectrum/metadata.
5. **alerted**: send WeCom payload, then cooldown.
6. **cooldown**: same frequency no duplicate alert for 120s.

## 6) Minimal Data Model

### SQLite table `events`

- `id` (TEXT/UUID)
- `site_id` (TEXT)
- `freq_mhz` (REAL)
- `start_time_utc` (TEXT)
- `end_time_utc` (TEXT)
- `duration_sec` (REAL)
- `music_score_max` (REAL)
- `labels_json` (TEXT)
- `iq_path` (TEXT)
- `audio_path` (TEXT)
- `spectrum_png_path` (TEXT)
- `meta_json_path` (TEXT)
- `alert_status` (TEXT)

## 7) Suggested Milestones

### Milestone A: Ingest skeleton

- Integrate rtl_airband process and channel config
- Verify stable audio stream consumption

### Milestone B: Classifier and eventing

- Integrate YAMNet inference
- Add gate + temporal scorer + cooldown

### Milestone C: Evidence recorder

- Implement ring buffer management
- Export artifacts with deterministic naming

### Milestone D: Alerting + persistence

- WeCom webhook sender
- SQLite insert/query and retention job

## 8) Risks and Mitigations

- **WSL USB/radio stability**: use WSL for PoC only, migrate to native Linux for 24/7 service.
- **False positives in noisy channels**: keep aggressive logging, tune thresholds with replayable clips.
- **IQ storage growth**: enforce disk watermark cleanup and aging policies.

## 9) Config Defaults (to implement)

```yaml
site:
  id: site-gz-001

detection:
  energy_gate: true
  music_prob_threshold: 0.70
  min_duration_sec: 5
  duplicate_cooldown_sec: 120

buffers:
  iq_ring_sec: 120
  pre_trigger_sec: 30
  post_trigger_sec: 90

retention:
  enabled: true
  start_cleanup_percent: 85
  stop_cleanup_percent: 75

alert:
  wecom_webhook: "${WECOM_WEBHOOK}"
```

## 10) Progress Update (implemented)

- Added runnable event core with CLI modes:
  - `--simulate`
  - `--input-jsonl <file>`
  - `--stdin-jsonl`
- Added JSONL ingestion contract for classifier sidecar integration.
- Added artifact recorder for per-event `audio.wav`, `capture.iq`, `spectrum.png`, `meta.json` (valid PNG placeholder).
- Added baseline tests for ingestion and recorder modules.
- Added SQLite query mode for recent event inspection (`--list-events`).
- Added WAV directory fallback ingestion with heuristic audio classifier for rtl_airband bring-up.
- Added rtl_airband recording directory ingest with filename-based frequency inference.
- Added watch mode for incremental ingest of newly created WAV files.
- Added persistent watch seen-file state to avoid duplicate processing after restart.
- Added per-loop watch logging (total/new/triggered counters).
- Added classifier backend selection (`auto`/`heuristic`/`yamnet`) with optional YAMNet runtime path.
