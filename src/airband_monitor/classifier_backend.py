from __future__ import annotations

from .classifier import HeuristicAudioClassifier
from .yamnet import YAMNetClassifier


def build_classifier(backend: str):
    backend = backend.lower()

    if backend == "heuristic":
        return HeuristicAudioClassifier(), "heuristic"

    if backend == "yamnet":
        return YAMNetClassifier(), "yamnet"

    if backend == "auto":
        try:
            return YAMNetClassifier(), "yamnet"
        except Exception:
            return HeuristicAudioClassifier(), "heuristic"

    raise ValueError("classifier backend must be one of: auto, heuristic, yamnet")
