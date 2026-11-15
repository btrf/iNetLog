"""Хранение результатов измерений скорости в SQLite."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS measurements (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    measured_at   TEXT    NOT NULL,
    download_mbps REAL,
    upload_mbps   REAL,
    ping_ms       REAL,
    server        TEXT,
    isp           TEXT,
    backend       TEXT,
    error         TEXT
);

CREATE INDEX IF NOT EXISTS idx_measurements_measured_at
    ON measurements (measured_at);
"""


@dataclass(frozen=True)
class Measurement:
    """Одна запись измерения (время хранится в UTC)."""

    id: int
    measured_at: datetime
    download_mbps: Optional[float]
    upload_mbps: Optional[float]
    ping_ms: Optional[float]
    server: str
    isp: str
    backend: str
    error: Optional[str]

    @property
    def local_time(self) -> datetime:
        return self.measured_at.astimezone()

    @property
    def succeeded(self) -> bool:
        return self.error is None and self.download_mbps is not None


class INetDatabase:
    """Небольшая обёртка над sqlite3 для истории замеров."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ------------------------------------------------------------------ запись
    def add(self, result: Mapping[str, Any]) -> Measurement:
        """Сохраняет результат замера (в том числе неудачный) и возвращает запись."""
        measured_at = datetime.now(timezone.utc).replace(microsecond=0)
        cursor = self._conn.execute(
            """
            INSERT INTO measurements
                (measured_at, download_mbps, upload_mbps, ping_ms, server, isp, backend, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                measured_at.isoformat(),
                result.get("download_mbps"),
                result.get("upload_mbps"),
                result.get("ping_ms"),
                result.get("server") or "",
                result.get("isp") or "",
                result.get("backend") or "",
                result.get("error"),
            ),
        )
        self._conn.commit()
        return Measurement(
            id=int(cursor.lastrowid),
            measured_at=measured_at,
            download_mbps=result.get("download_mbps"),
            upload_mbps=result.get("upload_mbps"),
            ping_ms=result.get("ping_ms"),
            server=result.get("server") or "",
            isp=result.get("isp") or "",
            backend=result.get("backend") or "",
            error=result.get("error"),
        )

    # ------------------------------------------------------------------ чтение
    def measurements(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> list[Measurement]:
        """Замеры (по возрастанию времени) в интервале ``since`` … ``until``."""
        query = "SELECT * FROM measurements"
        clauses: list[str] = []
        params: list[Any] = []
        if since is not None:
            clauses.append("measured_at >= ?")
            params.append(since.astimezone(timezone.utc).isoformat())
        if until is not None:
            clauses.append("measured_at <= ?")
            params.append(until.astimezone(timezone.utc).isoformat())
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY measured_at ASC, id ASC"
        return [self._row_to_measurement(row) for row in self._conn.execute(query, params)]

    def recent(self, limit: int = 30) -> list[Measurement]:
        """Последние ``limit`` замеров (по убыванию времени)."""
        rows = self._conn.execute(
            "SELECT * FROM measurements ORDER BY measured_at DESC, id DESC LIMIT ?",
            (int(limit),),
        )
        return [self._row_to_measurement(row) for row in rows]

    def last_successful(self) -> Optional[Measurement]:
        row = self._conn.execute(
            """
            SELECT * FROM measurements
            WHERE error IS NULL AND download_mbps IS NOT NULL
            ORDER BY measured_at DESC, id DESC
            LIMIT 1
            """
        ).fetchone()
        return self._row_to_measurement(row) if row is not None else None

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS n FROM measurements").fetchone()
        return int(row["n"]) if row is not None else 0

    # ------------------------------------------------------------------ прочее
    def clear(self) -> None:
        self._conn.execute("DELETE FROM measurements")
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    @staticmethod
    def _row_to_measurement(row: sqlite3.Row) -> Measurement:
        return Measurement(
            id=int(row["id"]),
            measured_at=datetime.fromisoformat(row["measured_at"]),
            download_mbps=row["download_mbps"],
            upload_mbps=row["upload_mbps"],
            ping_ms=row["ping_ms"],
            server=row["server"] or "",
            isp=row["isp"] or "",
            backend=row["backend"] or "",
            error=row["error"],
        )
