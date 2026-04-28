from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


_MUSIC_KEYWORDS = (
    "Music",
    "Singing",
    "Choir",
    "Musical instrument",
    "Radio",
    "Jingle",
)


@dataclass(slots=True)
class YAMNetConfig:
    model_url: str = "https://tfhub.dev/google/yamnet/1"


class YAMNetClassifier:
    """YAMNet-based classifier (optional dependency path).

    Requirements (not hard dependency for this repo):
    - tensorflow
    - tensorflow_hub
    - scipy
    """

    def __init__(self, config: YAMNetConfig | None = None) -> None:
        self.config = config or YAMNetConfig()
        try:
            import tensorflow as tf  # type: ignore
            import tensorflow_hub as hub  # type: ignore
            import numpy as np  # type: ignore
            from scipy.io import wavfile  # type: ignore
        except Exception as exc:  # pragma: no cover - env dependent
            raise RuntimeError(
                "YAMNet backend unavailable. Install tensorflow tensorflow_hub scipy."
            ) from exc

        self.tf = tf
        self.hub = hub
        self.np = np
        self.wavfile = wavfile
        self.model = hub.load(self.config.model_url)
        self.class_names = self._load_class_names()

    def _load_class_names(self) -> list[str]:
        class_map_path = self.model.class_map_path().numpy().decode("utf-8")
        lines = Path(class_map_path).read_text(encoding="utf-8").splitlines()
        # CSV header: index,mid,display_name
        out: list[str] = []
        for line in lines[1:]:
            parts = line.split(",")
            if len(parts) >= 3:
                out.append(parts[2].strip().strip('"'))
        return out

    def classify_music_probability(self, wav_path: Path) -> tuple[float, dict[str, float]]:
        sr, wav = self.wavfile.read(str(wav_path))
        wav = wav.astype(self.np.float32)

        if wav.ndim > 1:
            wav = wav.mean(axis=1)

        # normalize int16-like ranges
        if self.np.max(self.np.abs(wav)) > 1.5:
            wav = wav / 32768.0

        # YAMNet expects 16k mono float32
        target_sr = 16000
        if sr != target_sr:
            wav = self.tf.signal.resample(wav, int(len(wav) * target_sr / sr)).numpy()

        scores, _, _ = self.model(wav)
        scores_np = scores.numpy()
        mean_scores = scores_np.mean(axis=0)

        music_idxs = [
            i
            for i, name in enumerate(self.class_names)
            if any(k.lower() in name.lower() for k in _MUSIC_KEYWORDS)
        ]
        speech_idxs = [i for i, name in enumerate(self.class_names) if "speech" in name.lower()]

        music = float(mean_scores[music_idxs].max()) if music_idxs else 0.0
        speech = float(mean_scores[speech_idxs].max()) if speech_idxs else max(0.0, 1.0 - music)

        labels = {
            "music": round(max(0.0, min(1.0, music)), 4),
            "speech": round(max(0.0, min(1.0, speech)), 4),
        }
        return labels["music"], labels
