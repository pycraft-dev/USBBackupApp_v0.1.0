"""Scan and comparison service for backup mode detection."""

from pathlib import Path
from typing import Callable

from core.backup_logic import BackupLogic


class ScanService:
    """Compute backup mode and operations without UI dependencies."""

    @staticmethod
    def analyze(
        source: Path,
        target: Path,
        scan_files_fn: Callable[[Path, Callable | None, object | None], dict],
        file_hash_fn: Callable[[Path, object | None], str],
        cancel_event,
        on_scan_progress: Callable[[int, int, str], None] | None = None,
        on_compare_progress: Callable[[int, int, str], None] | None = None,
    ) -> tuple[dict, dict]:
        src_files = scan_files_fn(source, on_scan_progress, cancel_event)
        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Operation cancelled")

        dst_files = scan_files_fn(target, on_scan_progress, cancel_event)
        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Operation cancelled")

        if not src_files:
            return {"mode": "none", "ops_to_backup": [], "ops_to_usb": []}, {
                "status_msg": "На флешке нет файлов для бэкапа",
                "src_count": 0,
                "dst_count": len(dst_files),
                "matched": 0,
            }

        compare_result = BackupLogic.analyze_differences(
            src_files=src_files,
            dst_files=dst_files,
            source_root=source,
            backup_root=target,
            file_hash_fn=file_hash_fn,
            cancel_event=cancel_event,
            on_progress=on_compare_progress,
        )

        copy_to_backup_ops = compare_result["ops_to_backup"]
        copy_to_usb_ops = compare_result["ops_to_usb"]
        mode = compare_result["mode"]
        matched = compare_result["matched"]

        result = {
            **compare_result,
            "source_root": str(source),
            "backup_root": str(target),
        }
        return result, {
            "status_msg": "",
            "src_count": len(src_files),
            "dst_count": len(dst_files),
            "matched": matched,
            "mode": mode,
        }
