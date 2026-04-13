"""Legacy restore service for snapshot-based backups.

Reads file list from legacy DB and copies snapshot files to target folder.
"""

import shutil
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional

try:
    from .index_db import IndexDB
except ImportError:
    from legacy.index_db import IndexDB


class RestoreService:
    def __init__(self, db: IndexDB) -> None:
        """Create restore service bound to legacy index DB."""
        self.db = db

    def restore_snapshot(
        self,
        snapshot_tag: str,
        target_dir: str,
        progress_callback: Optional[Callable[[Dict], None]] = None,
    ) -> List[str]:
        """Restore all non-deleted files from selected snapshot tag."""
        snapshot = self.db.get_snapshot(snapshot_tag)
        if not snapshot:
            raise ValueError(f"Snapshot not found: {snapshot_tag}")

        backup_root = Path(snapshot["backup_root"])
        snapshot_id = int(snapshot["id"])
        files = self.db.get_snapshot_files(snapshot_id)
        restored: List[str] = []
        target = Path(target_dir)
        target.mkdir(parents=True, exist_ok=True)
        restore_rows = [(rel_path, row) for rel_path, row in files.items() if row["status"] != "deleted" and row["backup_rel_path"]]
        total_ops = max(1, len(restore_rows))
        total_bytes = max(1, sum(int(row["file_size"]) for _, row in restore_rows))
        done_ops = 0
        done_bytes = 0
        started_at = time.monotonic()

        def emit_progress(current: str) -> None:
            if not progress_callback:
                return
            elapsed = time.monotonic() - started_at
            rate = done_ops / elapsed if elapsed > 0 else 0.0
            remaining = total_ops - done_ops
            eta = (remaining / rate) if rate > 0 else None
            progress_callback(
                {
                    "done": done_ops,
                    "total": total_ops,
                    "percent": int((done_ops / total_ops) * 100),
                    "current": current,
                    "elapsed_seconds": elapsed,
                    "eta_seconds": eta,
                    "bytes_done": done_bytes,
                    "bytes_total": total_bytes,
                    "speed_bps": (done_bytes / elapsed) if elapsed > 0 else 0.0,
                }
            )

        for rel_path, row in restore_rows:
            backup_rel_path = row["backup_rel_path"]
            src = backup_root / backup_rel_path
            dst = target / rel_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.exists():
                shutil.copy2(src, dst)
                restored.append(rel_path)
            done_ops += 1
            done_bytes += int(row["file_size"])
            emit_progress(rel_path)
        return restored
