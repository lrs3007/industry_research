from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from app.models import MarketSnapshot

DEFAULT_DB_PATH = Path("data/sentiment.db")


def connect(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    init_db(connection)
    return connection


def init_db(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            market_id TEXT NOT NULL,
            event_id TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            category TEXT NOT NULL,
            probability REAL NOT NULL,
            yes_bid REAL,
            yes_ask REAL,
            volume REAL NOT NULL,
            open_interest REAL NOT NULL,
            liquidity REAL NOT NULL,
            close_time TEXT,
            observed_at TEXT NOT NULL,
            raw_json TEXT NOT NULL,
            change_24h REAL NOT NULL DEFAULT 0,
            change_7d REAL NOT NULL DEFAULT 0
        )
        """
    )
    _ensure_column(connection, "snapshots", "change_24h", "REAL NOT NULL DEFAULT 0")
    _ensure_column(connection, "snapshots", "change_7d", "REAL NOT NULL DEFAULT 0")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_market_time ON snapshots(platform, market_id, observed_at)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_time ON snapshots(observed_at)")
    connection.commit()


def save_snapshots(connection: sqlite3.Connection, snapshots: Iterable[MarketSnapshot]) -> int:
    rows = list(snapshots)
    connection.executemany(
        """
        INSERT INTO snapshots (
            platform, market_id, event_id, title, url, category, probability,
            yes_bid, yes_ask, volume, open_interest, liquidity, close_time,
            observed_at, raw_json, change_24h, change_7d
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                item.platform,
                item.market_id,
                item.event_id,
                item.title,
                item.url,
                item.category,
                item.probability,
                item.yes_bid,
                item.yes_ask,
                item.volume,
                item.open_interest,
                item.liquidity,
                item.close_time,
                item.observed_at,
                json.dumps(item.raw, ensure_ascii=True),
                item.change_24h,
                item.change_7d,
            )
            for item in rows
        ],
    )
    connection.commit()
    return len(rows)


def latest_snapshots(connection: sqlite3.Connection) -> list[MarketSnapshot]:
    rows = connection.execute(
        """
        WITH ranked AS (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY platform, market_id
                    ORDER BY observed_at DESC, id DESC
                ) AS row_num
            FROM snapshots
        )
        SELECT * FROM ranked WHERE row_num = 1
        """
    ).fetchall()
    return [_row_to_snapshot(row) for row in rows]


def attach_history_changes(connection: sqlite3.Connection, snapshots: Iterable[MarketSnapshot]) -> list[MarketSnapshot]:
    return [_with_history(connection, snapshot) for snapshot in snapshots]


def _with_history(connection: sqlite3.Connection, snapshot: MarketSnapshot) -> MarketSnapshot:
    day = _probability_before(connection, snapshot, "-24 hours")
    week = _probability_before(connection, snapshot, "-7 days")
    return MarketSnapshot(
        platform=snapshot.platform,
        market_id=snapshot.market_id,
        event_id=snapshot.event_id,
        title=snapshot.title,
        url=snapshot.url,
        category=snapshot.category,
        probability=snapshot.probability,
        yes_bid=snapshot.yes_bid,
        yes_ask=snapshot.yes_ask,
        volume=snapshot.volume,
        open_interest=snapshot.open_interest,
        liquidity=snapshot.liquidity,
        close_time=snapshot.close_time,
        observed_at=snapshot.observed_at,
        raw=snapshot.raw,
        change_24h=snapshot.change_24h if day is None else snapshot.probability - day,
        change_7d=snapshot.change_7d if week is None else snapshot.probability - week,
    )


def _probability_before(connection: sqlite3.Connection, snapshot: MarketSnapshot, modifier: str) -> float | None:
    row = connection.execute(
        """
        SELECT probability
        FROM snapshots
        WHERE platform = ?
          AND market_id = ?
          AND observed_at <= datetime(?, ?)
        ORDER BY observed_at DESC, id DESC
        LIMIT 1
        """,
        (snapshot.platform, snapshot.market_id, snapshot.observed_at, modifier),
    ).fetchone()
    return None if row is None else float(row["probability"])


def _row_to_snapshot(row: sqlite3.Row) -> MarketSnapshot:
    raw = json.loads(row["raw_json"]) if row["raw_json"] else {}
    return MarketSnapshot(
        platform=row["platform"],
        market_id=row["market_id"],
        event_id=row["event_id"],
        title=row["title"],
        url=row["url"],
        category=row["category"],
        probability=float(row["probability"]),
        yes_bid=row["yes_bid"],
        yes_ask=row["yes_ask"],
        volume=float(row["volume"]),
        open_interest=float(row["open_interest"]),
        liquidity=float(row["liquidity"]),
        close_time=row["close_time"],
        observed_at=row["observed_at"],
        raw=raw,
        change_24h=float(row["change_24h"]),
        change_7d=float(row["change_7d"]),
    )


def _ensure_column(connection: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
