"""Regression tests for folder difference analysis in `BackupLogic`."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.backup_logic import BackupLogic


def _write_file(path: Path, content: str, mtime: int) -> None:
    """Create file with deterministic timestamp for comparison scenarios."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    os.utime(path, (mtime, mtime))


def _op_paths(ops: list[tuple[Path, Path, int, str]]) -> set[str]:
    """Extract relative paths from planned operations list."""
    return {item[3] for item in ops}


def test_analyze_differences_detects_changed_and_missing_files(tmp_path: Path) -> None:
    source_root = tmp_path / "usb"
    backup_root = tmp_path / "backup"

    _write_file(source_root / "same.txt", "same", 1000)
    _write_file(backup_root / "same.txt", "same", 1000)

    _write_file(source_root / "new_on_usb.txt", "new", 1001)

    _write_file(source_root / "changed_by_usb.txt", "usb-version", 1003)
    _write_file(backup_root / "changed_by_usb.txt", "backup-version", 1002)

    _write_file(source_root / "changed_by_backup.txt", "usb-old", 1002)
    _write_file(backup_root / "changed_by_backup.txt", "backup-new", 1005)

    _write_file(source_root / "same_content_diff_mtime.txt", "hash-same", 1001)
    _write_file(backup_root / "same_content_diff_mtime.txt", "hash-same", 1010)

    _write_file(backup_root / "only_in_backup.txt", "backup-only", 1004)

    src_files = BackupLogic.scan_files_progress(source_root)
    dst_files = BackupLogic.scan_files_progress(backup_root)
    result = BackupLogic.analyze_differences(src_files, dst_files, source_root, backup_root)

    assert result["mode"] == "sync"
    assert _op_paths(result["ops_to_backup"]) == {"new_on_usb.txt", "changed_by_usb.txt"}
    assert _op_paths(result["ops_to_usb"]) == {"changed_by_backup.txt", "only_in_backup.txt"}
    assert "same_content_diff_mtime.txt" not in _op_paths(result["ops_to_backup"])
    assert "same_content_diff_mtime.txt" not in _op_paths(result["ops_to_usb"])


def test_analyze_differences_case_insensitive_matching(tmp_path: Path) -> None:
    """Files whose names differ only in case must not appear in extra_in_backup / ops_to_usb."""
    source_root = tmp_path / "usb"
    backup_root = tmp_path / "backup"

    # USB has "README.txt", backup has "readme.txt" — same content, same size.
    # On Windows these are the same file; must be treated as matched.
    _write_file(source_root / "README.txt", "content", 1000)
    _write_file(backup_root / "readme.txt", "content", 1000)

    # A truly new file only on USB.
    _write_file(source_root / "new.txt", "new", 1001)

    src_files = BackupLogic.scan_files_progress(source_root)
    dst_files = BackupLogic.scan_files_progress(backup_root)
    result = BackupLogic.analyze_differences(src_files, dst_files, source_root, backup_root)

    # "readme.txt" (backup) must NOT appear in extra_in_backup — it matches "README.txt" (usb).
    assert "readme.txt" not in result["extra_in_backup"]
    assert "README.txt" not in result["extra_in_backup"]

    # No copy-to-usb ops for the case-differing pair.
    usb_op_paths = _op_paths(result["ops_to_usb"])
    assert "readme.txt" not in usb_op_paths
    assert "README.txt" not in usb_op_paths

    # The genuinely new file should be queued for backup.
    assert "new.txt" in _op_paths(result["ops_to_backup"])


def test_analyze_differences_falls_back_to_full_backup_on_low_similarity(tmp_path: Path) -> None:
    source_root = tmp_path / "usb"
    backup_root = tmp_path / "backup"

    _write_file(source_root / "a.txt", "A", 1000)
    _write_file(source_root / "b.txt", "B", 1001)
    _write_file(backup_root / "other.txt", "X", 1002)

    src_files = BackupLogic.scan_files_progress(source_root)
    dst_files = BackupLogic.scan_files_progress(backup_root)
    result = BackupLogic.analyze_differences(src_files, dst_files, source_root, backup_root)

    assert result["mode"] == "full"
    assert _op_paths(result["ops_to_backup"]) == {"a.txt", "b.txt"}
