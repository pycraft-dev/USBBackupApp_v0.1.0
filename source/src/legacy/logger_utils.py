"""Legacy logging/report helpers for snapshot engine.

These helpers create per-run text logs and JSON summary reports.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List


def _safe_name(name: str) -> str:
    """Sanitize profile name so it is safe for file names."""
    safe = re.sub(r'[<>:"/\\|?*]', "_", name).strip(" .")
    return safe or "backup"


def setup_logger(log_root: Path, profile_name: str) -> logging.Logger:
    """Create dedicated file logger for one legacy backup run."""
    log_root.mkdir(parents=True, exist_ok=True)
    safe_profile = _safe_name(profile_name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_root / f"{safe_profile}_{timestamp}.log"

    logger = logging.getLogger(f"usb_backup_{safe_profile}_{timestamp}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def write_json_report(log_root: Path, profile_name: str, report: Dict) -> Path:
    """Write final report as UTF-8 JSON file and return its path."""
    log_root.mkdir(parents=True, exist_ok=True)
    safe_profile = _safe_name(profile_name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = log_root / f"{safe_profile}_{timestamp}.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report_path


def init_report(profile_name: str, mode: str, source_root: str, backup_root: str) -> Dict:
    """Initialize report payload before copy starts."""
    return {
        "profile_name": profile_name,
        "mode": mode,
        "source_root": source_root,
        "backup_root": backup_root,
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "copied": [],
        "removed": [],
        "skipped": [],
        "errors": [],
    }


def finalize_report(report: Dict, copied: List[str], removed: List[str], skipped: List[str], errors: List[str]) -> Dict:
    """Attach final stats and timestamps to report payload."""
    report["copied"] = copied
    report["removed"] = removed
    report["skipped"] = skipped
    report["errors"] = errors
    report["finished_at"] = datetime.now().isoformat(timespec="seconds")
    report["stats"] = {
        "copied_count": len(copied),
        "removed_count": len(removed),
        "skipped_count": len(skipped),
        "error_count": len(errors),
    }
    return report
