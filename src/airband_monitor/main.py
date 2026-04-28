from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import time
import uuid

from .alert import AlertMessage, WeComNotifier
from .config import load_config
from .ingest import InferenceFrame, JsonlInferenceSource, StdinInferenceSource
from .recorder import ArtifactRecorder
from .retention import WatermarkRetention
from .rtl_airband_source import RtlAirbandRecordingSource
from .scoring import ScoringInput, TemporalScorer
from .storage import EventRecord, EventStore
from .wav_source import WavDirectorySource
from .watch_state import WatchSeenStore
from .classifier_backend import build_classifier

UTC = timezone.utc


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="airband-monitor v0.1 scaffold")
    parser.add_argument("--config", default="configs/default.yaml", help="Path to yaml config")
    parser.add_argument("--simulate", action="store_true", help="Run built-in simulated score stream")
    parser.add_argument("--input-jsonl", help="Read inference frames from a JSONL file")
    parser.add_argument("--stdin-jsonl", action="store_true", help="Read inference frames from STDIN JSONL")
    parser.add_argument("--list-events", type=int, metavar="N", help="List the most recent N events and exit")
    parser.add_argument("--input-wav-dir", help="Read WAV chunks from a directory and classify via heuristic fallback")
    parser.add_argument("--wav-freq", type=float, help="Frequency MHz used with --input-wav-dir")
    parser.add_argument("--input-rtl-dir", help="Read rtl_airband WAV recordings from directory")
    parser.add_argument("--rtl-default-freq", type=float, help="Fallback frequency when filename does not contain frequency")
    parser.add_argument("--watch", action="store_true", help="Watch input directory mode for newly created WAV files")
    parser.add_argument("--poll-interval", type=float, default=2.0, help="Polling interval seconds for --watch mode")
    parser.add_argument("--max-loops", type=int, default=0, help="Optional max loops for watch mode (0 = infinite)")
    parser.add_argument(
        "--watch-state-file",
        default="data/watch_seen_files.txt",
        help="Persistent watch-mode seen-file state",
    )
    parser.add_argument(
        "--classifier-backend",
        default="auto",
        choices=["auto", "heuristic", "yamnet"],
        help="Audio classifier backend for wav/rtl sources",
    )
    return parser


def _simulate_stream() -> list[InferenceFrame]:
    start = datetime.now(tz=UTC)
    freq = 121.5
    low = [0.2, 0.3, 0.4]
    high = [0.8, 0.82, 0.85, 0.79, 0.81, 0.84]
    values = low + high + low
    return [
        InferenceFrame(
            freq_mhz=freq,
            ts_utc=start + timedelta(seconds=i),
            music_prob=v,
            labels={"music": v},
        )
        for i, v in enumerate(values)
    ]


def _iter_frames(args: argparse.Namespace, classifier) -> list[InferenceFrame] | object:
    if args.simulate:
        return _simulate_stream()
    if args.input_jsonl:
        return JsonlInferenceSource(Path(args.input_jsonl)).read()
    if args.stdin_jsonl:
        return StdinInferenceSource().read()
    if args.input_wav_dir:
        if args.wav_freq is None:
            raise ValueError("--wav-freq is required when using --input-wav-dir")
        return WavDirectorySource(Path(args.input_wav_dir), freq_mhz=args.wav_freq, classifier=classifier).read()
    if args.input_rtl_dir:
        return RtlAirbandRecordingSource(
            directory=Path(args.input_rtl_dir),
            default_freq_mhz=args.rtl_default_freq,
            recursive=True,
            classifier=classifier,
        ).read()
    return []


def _build_source_for_watch(args: argparse.Namespace, classifier) -> WavDirectorySource | RtlAirbandRecordingSource:
    if args.input_wav_dir:
        if args.wav_freq is None:
            raise ValueError("--wav-freq is required when using --input-wav-dir")
        return WavDirectorySource(Path(args.input_wav_dir), freq_mhz=args.wav_freq, classifier=classifier)
    if args.input_rtl_dir:
        return RtlAirbandRecordingSource(
            directory=Path(args.input_rtl_dir),
            default_freq_mhz=args.rtl_default_freq,
            recursive=True,
            classifier=classifier,
        )
    raise ValueError("--watch requires --input-wav-dir or --input-rtl-dir")


def _iter_new_watch_frames(args: argparse.Namespace, seen: set[str], classifier) -> tuple[list[InferenceFrame], int, int]:
    source = _build_source_for_watch(args, classifier)
    files = source.list_files()
    total_files = len(files)

    new_files = [f for f in files if str(f) not in seen]
    new_count = len(new_files)

    for f in new_files:
        seen.add(str(f))

    frames = list(source.frames_from_files(new_files))
    return frames, total_files, new_count


def _print_recent_events(store: EventStore, limit: int) -> None:
    events = store.list_recent(limit=limit)
    if not events:
        print("No events found.")
        return

    for event in events:
        print(
            f"{event.start_time_utc} | {event.freq_mhz:.3f} MHz | "
            f"score={event.music_score_max:.2f} | id={event.id}"
        )


def _process_frames(
    frames: list[InferenceFrame] | object,
    cfg: object,
    store: EventStore,
    recorder: ArtifactRecorder,
    scorer: TemporalScorer,
    notifier: WeComNotifier,
) -> int:
    processed = 0
    for frame in frames:
        triggered = scorer.update(
            ScoringInput(freq_mhz=frame.freq_mhz, ts_utc=frame.ts_utc, music_prob=frame.music_prob)
        )
        if not triggered:
            continue

        event_id = str(uuid.uuid4())
        start_time = triggered.trigger_time_utc - timedelta(seconds=cfg.buffers.pre_trigger_sec)
        end_time = triggered.trigger_time_utc + timedelta(seconds=cfg.buffers.post_trigger_sec)

        artifacts = recorder.record(
            event_id=event_id,
            freq_mhz=triggered.freq_mhz,
            trigger_time_utc=triggered.trigger_time_utc,
            labels=frame.labels,
            source_audio_path=frame.audio_path,
            source_iq_path=frame.iq_path,
        )

        event = EventRecord(
            id=event_id,
            site_id=cfg.site.id,
            freq_mhz=triggered.freq_mhz,
            start_time_utc=start_time.isoformat(),
            end_time_utc=end_time.isoformat(),
            duration_sec=float((end_time - start_time).total_seconds()),
            music_score_max=triggered.music_score,
            labels_json=json.dumps(frame.labels),
            iq_path=str(artifacts.iq_path),
            audio_path=str(artifacts.audio_path),
            spectrum_png_path=str(artifacts.spectrum_png_path),
            meta_json_path=str(artifacts.meta_json_path),
            alert_status="sent",
        )
        store.insert(event)
        processed += 1

        notifier.send(
            AlertMessage(
                title="Airband anomaly",
                body=(
                    f"- site: `{cfg.site.id}`\n"
                    f"- freq: `{triggered.freq_mhz:.3f} MHz`\n"
                    f"- music score: `{triggered.music_score:.2f}`\n"
                    f"- event id: `{event_id}`\n"
                    f"- spectrum: `{artifacts.spectrum_png_path}`"
                ),
            )
        )
    return processed


def main() -> None:
    args = _build_parser().parse_args()
    cfg = load_config(args.config)

    store = EventStore(cfg.storage.sqlite_path)

    if args.list_events:
        _print_recent_events(store, limit=max(1, args.list_events))
        return

    recorder = ArtifactRecorder(cfg.storage.artifact_root, cfg.site.id)
    scorer = TemporalScorer(
        threshold=cfg.detection.music_prob_threshold,
        min_duration_sec=cfg.detection.min_duration_sec,
        cooldown_sec=cfg.detection.duplicate_cooldown_sec,
    )
    notifier = WeComNotifier(cfg.alert.wecom_webhook, dry_run=cfg.alert.dry_run)

    classifier, backend_used = build_classifier(args.classifier_backend)
    print(f"classifier_backend={backend_used}")

    if args.watch:
        state_store = WatchSeenStore(Path(args.watch_state_file))
        seen = state_store.load()

        loops = 0
        while True:
            frames, total_files, new_files = _iter_new_watch_frames(args, seen, classifier)
            triggered = _process_frames(frames, cfg, store, recorder, scorer, notifier)
            state_store.save()

            print(
                f"[watch] loop={loops + 1} total_files={total_files} "
                f"new_files={new_files} triggered_events={triggered}"
            )

            loops += 1
            if args.max_loops > 0 and loops >= args.max_loops:
                break
            time.sleep(max(0.2, args.poll_interval))
    else:
        frames = _iter_frames(args, classifier)
        if not frames:
            print("Scaffold ready. Use --simulate / --input-jsonl / --stdin-jsonl / --input-wav-dir / --input-rtl-dir.")
            return
        _process_frames(frames, cfg, store, recorder, scorer, notifier)

    if cfg.retention.enabled:
        cleanup = WatermarkRetention(
            artifact_root=cfg.storage.artifact_root,
            start_percent=cfg.retention.start_cleanup_percent,
            stop_percent=cfg.retention.stop_cleanup_percent,
        )
        deleted = cleanup.run_cleanup()
        if deleted:
            print(f"Retention cleanup deleted {len(deleted)} event directories.")

    print(f"Run complete. Persisted events: {store.count()}")


if __name__ == "__main__":
    main()
