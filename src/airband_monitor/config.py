from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import os

try:
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    yaml = None


@dataclass(slots=True)
class SiteConfig:
    id: str


@dataclass(slots=True)
class StorageConfig:
    sqlite_path: Path
    artifact_root: Path


@dataclass(slots=True)
class DetectionConfig:
    music_prob_threshold: float
    min_duration_sec: int
    duplicate_cooldown_sec: int


@dataclass(slots=True)
class BufferConfig:
    iq_ring_sec: int
    pre_trigger_sec: int
    post_trigger_sec: int


@dataclass(slots=True)
class RetentionConfig:
    enabled: bool
    start_cleanup_percent: int
    stop_cleanup_percent: int


@dataclass(slots=True)
class AlertConfig:
    wecom_webhook: str
    dry_run: bool


@dataclass(slots=True)
class AppConfig:
    site: SiteConfig
    storage: StorageConfig
    detection: DetectionConfig
    buffers: BufferConfig
    retention: RetentionConfig
    alert: AlertConfig



def _parse_scalar(value: str) -> Any:
    value = value.strip().strip('"').strip("'")
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if value == "":
        return ""
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value



def _simple_yaml_load(text: str) -> dict[str, Any]:
    """Very small YAML subset loader for offline environments.

    Supports current config style: top-level sections with two-space-indented key/value pairs.
    """

    result: dict[str, Any] = {}
    current_section: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue

        if not line.startswith(" ") and line.endswith(":"):
            current_section = line[:-1].strip()
            result[current_section] = {}
            continue

        if current_section and line.startswith("  ") and ":" in line:
            key, raw_value = line.strip().split(":", 1)
            result[current_section][key.strip()] = _parse_scalar(raw_value)

    return result



def _load_yaml(path: Path) -> dict[str, Any]:
    content = path.read_text(encoding="utf-8")
    if yaml:
        loaded = yaml.safe_load(content)
        if not isinstance(loaded, dict):
            raise ValueError("Configuration root must be a mapping")
        return loaded
    return _simple_yaml_load(content)



def _env_override(config: dict[str, Any]) -> dict[str, Any]:
    webhook = os.getenv("WECOM_WEBHOOK")
    if webhook:
        config.setdefault("alert", {})["wecom_webhook"] = webhook
    return config



def load_config(path: str | Path) -> AppConfig:
    path = Path(path)
    raw = _load_yaml(path)
    raw = _env_override(raw)

    return AppConfig(
        site=SiteConfig(id=raw["site"]["id"]),
        storage=StorageConfig(
            sqlite_path=Path(raw["storage"]["sqlite_path"]),
            artifact_root=Path(raw["storage"]["artifact_root"]),
        ),
        detection=DetectionConfig(
            music_prob_threshold=float(raw["detection"]["music_prob_threshold"]),
            min_duration_sec=int(raw["detection"]["min_duration_sec"]),
            duplicate_cooldown_sec=int(raw["detection"]["duplicate_cooldown_sec"]),
        ),
        buffers=BufferConfig(
            iq_ring_sec=int(raw["buffers"]["iq_ring_sec"]),
            pre_trigger_sec=int(raw["buffers"]["pre_trigger_sec"]),
            post_trigger_sec=int(raw["buffers"]["post_trigger_sec"]),
        ),
        retention=RetentionConfig(
            enabled=bool(raw["retention"]["enabled"]),
            start_cleanup_percent=int(raw["retention"]["start_cleanup_percent"]),
            stop_cleanup_percent=int(raw["retention"]["stop_cleanup_percent"]),
        ),
        alert=AlertConfig(
            wecom_webhook=str(raw["alert"].get("wecom_webhook", "")),
            dry_run=bool(raw["alert"].get("dry_run", True)),
        ),
    )
