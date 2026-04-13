"""Legacy snapshot-based backup engine.

This module is no longer used by `main.py`, but kept for reference and possible
future revival of database-backed snapshot mode.
"""

import hashlib
import os
import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Optional

try:
    from .index_db import IndexDB
    from .logger_utils import finalize_report, init_report, setup_logger, write_json_report
except ImportError:
    from legacy.index_db import IndexDB
    from legacy.logger_utils import finalize_report, init_report, setup_logger, write_json_report


@dataclass
class BackupResult:
    """Summary returned after legacy backup run."""

    snapshot_tag: str
    copied_count: int
    removed_count: int
    skipped_count: int
    report_path: Path


class BackupEngine:
    def __init__(self, db: IndexDB, log_root: Path) -> None:
        """Create legacy engine bound to index DB and report directory."""
        self.db = db
        self.log_root = Path(log_root)

    @staticmethod
    def _snapshot_tag() -> str:
        return datetime.now().strftime("snapshot_%Y%m%d_%H%M%S_%f")

    @staticmethod
    def _safe_rel(path: Path, root: Path) -> str:
        return str(path.relative_to(root)).replace("\\", "/")

    @staticmethod
    def _sha256(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _scan_source(self, source_root: Path) -> Dict[str, Dict]:
        """Collect source files metadata by relative path."""
        index: Dict[str, Dict] = {}
        for root, _, files in os.walk(source_root):
            for name in files:
                full = Path(root) / name
                rel = self._safe_rel(full, source_root)
                try:
                    st = full.stat()
                    index[rel] = {
                        "path": full,
                        "size": int(st.st_size),
                        "mtime": float(st.st_mtime),
                    }
                except OSError:
                    continue
        return index

    def run_backup(
        self,
        profile_name: str,
        source_root: str,
        backup_root: str,
        mode: str,
        progress_callback: Optional[Callable[[Dict], None]] = None,
    ) -> BackupResult:
        """Run full/incremental snapshot backup and write DB + JSON report."""
        source = Path(source_root)
        backup = Path(backup_root)
        if not source.exists():
            raise FileNotFoundError(f"Source path not found: {source}")

        backup.mkdir(parents=True, exist_ok=True)
        snapshot_tag = self._snapshot_tag()
        snapshot_dir = backup / snapshot_tag
        files_dir = snapshot_dir / "files"
        files_dir.mkdir(parents=True, exist_ok=True)

        logger = setup_logger(self.log_root, profile_name)
        report = init_report(profile_name, mode, str(source), str(backup))
        copied, removed, skipped, errors = [], [], [], []

        current_files = self._scan_source(source)
        previous = self.db.get_last_snapshot(profile_name) if mode == "incremental" else None
        previous_files = self.db.get_snapshot_files(previous["id"]) if previous else {}
        removed_paths = set(previous_files.keys()) - set(current_files.keys()) if mode == "incremental" else set()
        total_ops = max(1, len(current_files) + len(removed_paths))
        total_bytes = max(1, sum(meta["size"] for meta in current_files.values()))
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

        snapshot_id = self.db.create_snapshot(
            profile_name=profile_name,
            snapshot_tag=snapshot_tag,
            mode=mode,
            created_at=datetime.now().isoformat(timespec="seconds"),
            source_root=str(source),
            backup_root=str(backup),
        )

        for rel_path, meta in current_files.items():
            should_copy = mode == "full"
            prev = previous_files.get(rel_path)

            if mode == "incremental" and prev:
                if int(prev["file_size"]) != meta["size"] or float(prev["mtime"]) != meta["mtime"]:
                    should_copy = True
                else:
                    should_copy = False
            elif mode == "incremental" and not prev:
                should_copy = True

            src_file = meta["path"]
            dst_file = files_dir / rel_path
            dst_file.parent.mkdir(parents=True, exist_ok=True)

            if should_copy:
                try:
                    shutil.copy2(src_file, dst_file)
                    file_hash = self._sha256(dst_file)
                    copied.append(rel_path)
                    logger.info("COPIED %s", rel_path)
                    self.db.add_file_record(
                        snapshot_id=snapshot_id,
                        relative_path=rel_path,
                        file_size=meta["size"],
                        mtime=meta["mtime"],
                        sha256=file_hash,
                        status="copied",
                        backup_rel_path=f"{snapshot_tag}/files/{rel_path}",
                    )
                except OSError as e:
                    errors.append(f"{rel_path}: {e}")
                    logger.error("ERROR %s: %s", rel_path, e)
            else:
                skipped.append(rel_path)
                logger.info("SKIPPED %s", rel_path)
                self.db.add_file_record(
                    snapshot_id=snapshot_id,
                    relative_path=rel_path,
                    file_size=meta["size"],
                    mtime=meta["mtime"],
                    sha256=prev["sha256"] if prev else None,
                    status="skipped",
                    backup_rel_path=prev["backup_rel_path"] if prev else None,
                )
            done_ops += 1
            done_bytes += meta["size"]
            emit_progress(rel_path)

        if mode == "incremental":
            for rel_path in sorted(removed_paths):
                removed.append(rel_path)
                logger.info("REMOVED %s", rel_path)
                self.db.add_file_record(
                    snapshot_id=snapshot_id,
                    relative_path=rel_path,
                    file_size=0,
                    mtime=0,
                    sha256=None,
                    status="deleted",
                    backup_rel_path=None,
                )
                done_ops += 1
                emit_progress(rel_path)

        self.db.finalize_snapshot(snapshot_id, len(copied), len(removed), len(skipped))
        report = finalize_report(report, copied, removed, skipped, errors)
        report["snapshot_tag"] = snapshot_tag
        report_path = write_json_report(self.log_root, profile_name, report)

        return BackupResult(
            snapshot_tag=snapshot_tag,
            copied_count=len(copied),
            removed_count=len(removed),
            skipped_count=len(skipped),
            report_path=report_path,
        )
