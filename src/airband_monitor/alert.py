from __future__ import annotations

from dataclasses import dataclass
import json
from urllib import request


@dataclass(slots=True)
class AlertMessage:
    title: str
    body: str


class WeComNotifier:
    def __init__(self, webhook: str, dry_run: bool = True) -> None:
        self.webhook = webhook
        self.dry_run = dry_run

    def send(self, message: AlertMessage) -> None:
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": f"### {message.title}\n{message.body}",
            },
        }

        if self.dry_run or not self.webhook:
            print("[DRY_RUN] WeCom payload:", json.dumps(payload, ensure_ascii=False))
            return

        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self.webhook,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=10) as resp:  # noqa: S310
            if resp.status >= 300:
                raise RuntimeError(f"WeCom webhook failed with HTTP {resp.status}")
