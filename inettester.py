"""Измерение скорости интернета.

Единственный бэкенд — пакет ``speedtest-cli`` (pip install speedtest-cli).
Ookla Speedtest CLI намеренно не используется: в России он недоступен.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Optional

from PySide6.QtCore import QThread, Signal

MEGABIT = 1_000_000.0


def _ensure_standard_streams() -> None:
    """В windowed-exe из PyInstaller sys.stdout/stderr = None, а speedtest-cli их использует."""
    for name in ("stdout", "stderr"):
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))


_ensure_standard_streams()


class INetTestError(RuntimeError):
    """Не удалось выполнить измерение."""


# --------------------------------------------------------------------- speedtest-cli
def _run_speedtest_cli() -> dict[str, Any]:
    try:
        import speedtest  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - зависит от окружения
        raise INetTestError(
            "Не установлен пакет speedtest-cli (pip install speedtest-cli)"
        ) from exc

    client = speedtest.Speedtest(secure=True)
    client.get_best_server()
    download_bps = float(client.download())
    upload_bps = float(client.upload())
    info = client.results.dict()
    server_info = info.get("server") or {}

    name = (server_info.get("name") or "").strip()
    country = (server_info.get("country") or "").strip()
    server = " — ".join(part for part in (name, country) if part)

    # speedtest-cli подставляет 3600 с при недоступном latency.txt; такие значения бесполезны.
    ping = info.get("ping")
    ping_ms: Optional[float] = None
    if ping is not None:
        candidate = float(ping)
        if 0 < candidate < 10_000:
            ping_ms = round(candidate, 1)

    return {
        "download_mbps": round(download_bps / MEGABIT, 2),
        "upload_mbps": round(upload_bps / MEGABIT, 2),
        "ping_ms": ping_ms,
        "server": server,
        "isp": (info.get("client") or {}).get("isp") or "",
        "backend": "speedtest-cli",
    }


# --------------------------------------------------------------------- публичный API
def run_inet_test() -> dict[str, Any]:
    """Выполняет замер. При неудаче бросает INetTestError с текстом причины."""
    try:
        return _run_speedtest_cli()
    except INetTestError:
        raise
    except Exception as exc:  # noqa: BLE001 - нужен максимально широкий перехват
        raise INetTestError(str(exc) or exc.__class__.__name__) from exc


class INetTestThread(QThread):
    """Выполняет замер в фоновом потоке, чтобы не блокировать интерфейс."""

    result_ready = Signal(dict)

    def run(self) -> None:  # noqa: D401 - метод Qt
        try:
            result = run_inet_test()
        except Exception as exc:  # noqa: BLE001
            result = {"error": str(exc) or exc.__class__.__name__}
        self.result_ready.emit(result)
