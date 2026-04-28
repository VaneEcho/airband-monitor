from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(slots=True)
class EvalSample:
    music_prob: float
    gt_music: bool


@dataclass(slots=True)
class EvalMetrics:
    threshold: float
    tp: int
    fp: int
    fn: int
    tn: int
    precision: float
    recall: float
    f1: float



def load_eval_jsonl(path: Path) -> list[EvalSample]:
    samples: list[EvalSample] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if "music_prob" not in obj or "gt_music" not in obj:
                raise ValueError("Each eval row must include music_prob and gt_music")
            samples.append(
                EvalSample(
                    music_prob=float(obj["music_prob"]),
                    gt_music=bool(obj["gt_music"]),
                )
            )
    return samples



def evaluate_threshold(samples: list[EvalSample], threshold: float) -> EvalMetrics:
    tp = fp = fn = tn = 0
    for s in samples:
        pred = s.music_prob >= threshold
        if pred and s.gt_music:
            tp += 1
        elif pred and not s.gt_music:
            fp += 1
        elif (not pred) and s.gt_music:
            fn += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    return EvalMetrics(
        threshold=threshold,
        tp=tp,
        fp=fp,
        fn=fn,
        tn=tn,
        precision=precision,
        recall=recall,
        f1=f1,
    )



def evaluate_grid(samples: list[EvalSample], thresholds: list[float]) -> list[EvalMetrics]:
    return [evaluate_threshold(samples, t) for t in thresholds]



def best_by_f1(metrics: list[EvalMetrics]) -> EvalMetrics:
    if not metrics:
        raise ValueError("metrics cannot be empty")
    return sorted(metrics, key=lambda m: (m.f1, m.recall, -m.fp), reverse=True)[0]
