"""Legacy SQLite index for snapshot backup mode.

Not used in the current lightweight app flow, but preserved for compatibility.
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional


class IndexDB:
    def __init__(self, db_path: Path) -> None:
        """Open/create DB file and ensure schema exists."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        """Create sqlite connection with row dict-like access."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_name TEXT UNIQUE NOT NULL,
                    device_id TEXT,
                    source_root TEXT NOT NULL,
                    backup_root TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_name TEXT NOT NULL,
                    snapshot_tag TEXT UNIQUE NOT NULL,
                    mode TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    source_root TEXT NOT NULL,
                    backup_root TEXT NOT NULL,
                    copied_count INTEGER DEFAULT 0,
                    removed_count INTEGER DEFAULT 0,
                    skipped_count INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER NOT NULL,
                    relative_path TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    mtime REAL NOT NULL,
                    sha256 TEXT,
                    status TEXT NOT NULL,
                    backup_rel_path TEXT,
                    UNIQUE(snapshot_id, relative_path),
                    FOREIGN KEY(snapshot_id) REFERENCES snapshots(id) ON DELETE CASCADE
                );
                """
            )

    def upsert_profile(self, profile_name: str, device_id: str, source_root: str, backup_root: str, created_at: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO profiles (profile_name, device_id, source_root, backup_root, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(profile_name) DO UPDATE SET
                    device_id = excluded.device_id,
                    source_root = excluded.source_root,
                    backup_root = excluded.backup_root
                """,
                (profile_name, device_id, source_root, backup_root, created_at),
            )

    def create_snapshot(
        self,
        profile_name: str,
        snapshot_tag: str,
        mode: str,
        created_at: str,
        source_root: str,
        backup_root: str,
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO snapshots (profile_name, snapshot_tag, mode, created_at, source_root, backup_root)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (profile_name, snapshot_tag, mode, created_at, source_root, backup_root),
            )
            return int(cursor.lastrowid)

    def finalize_snapshot(self, snapshot_id: int, copied: int, removed: int, skipped: int) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE snapshots
                SET copied_count = ?, removed_count = ?, skipped_count = ?
                WHERE id = ?
                """,
                (copied, removed, skipped, snapshot_id),
            )

    def add_file_record(
        self,
        snapshot_id: int,
        relative_path: str,
        file_size: int,
        mtime: float,
        sha256: Optional[str],
        status: str,
        backup_rel_path: Optional[str],
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO files
                (snapshot_id, relative_path, file_size, mtime, sha256, status, backup_rel_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (snapshot_id, relative_path, file_size, mtime, sha256, status, backup_rel_path),
            )

    def get_last_snapshot(self, profile_name: str) -> Optional[sqlite3.Row]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM snapshots
                WHERE profile_name = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (profile_name,),
            ).fetchone()
        return row

    def get_snapshot(self, snapshot_tag: str) -> Optional[sqlite3.Row]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM snapshots WHERE snapshot_tag = ?",
                (snapshot_tag,),
            ).fetchone()
        return row

    def get_snapshot_files(self, snapshot_id: int) -> Dict[str, sqlite3.Row]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM files WHERE snapshot_id = ?",
                (snapshot_id,),
            ).fetchall()
        return {row["relative_path"]: row for row in rows}

    def list_snapshots(self, profile_name: str) -> List[sqlite3.Row]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT snapshot_tag, mode, created_at, copied_count, removed_count, skipped_count
                FROM snapshots
                WHERE profile_name = ?
                ORDER BY id DESC
                """,
                (profile_name,),
            ).fetchall()
        return rows
