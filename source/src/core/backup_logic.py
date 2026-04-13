"""Core backup operations independent from UI widgets.

`BackupLogic` contains filesystem scanning, hashing, copy streaming and
difference analysis. Keeping this module UI-agnostic makes it easier to test.
"""

import hashlib
import os
import shutil
import threading
import time
from pathlib import Path
from typing import Callable


class BackupLogic:
    @staticmethod
    def should_skip_dir(dirname: str) -> bool:
        """Filter Windows/system folders that should not be scanned."""
        n = (dirname or "").strip().lower()
        return n in ("system volume information", "$recycle.bin", "recycler")

    @staticmethod
    def scan_files_progress(
        root: Path,
        on_progress: Callable | None = None,
        cancel_event: threading.Event | None = None,
    ) -> dict:
        """Scan folder recursively and return metadata keyed by relative path."""
        data = {}
        scanned = 0
        total = 0
        last_update = 0.0

        if on_progress:
            on_progress(0, 0, f"Папка «{root.name}»: сканирование...")

        def on_walk_error(_err: OSError) -> None:
            return

        for dirpath, dirnames, files in os.walk(root, onerror=on_walk_error, followlinks=False):
            if cancel_event and cancel_event.is_set():
                return data
            try:
                dirnames[:] = [d for d in dirnames if not BackupLogic.should_skip_dir(d)]
            except Exception:
                pass
            for file_name in files:
                full = Path(dirpath) / file_name
                rel = str(full.relative_to(root)).replace("\\", "/")
                try:
                    st = full.stat()
                    data[rel] = {"path": full, "size": int(st.st_size), "mtime": float(st.st_mtime)}
                    scanned += 1
                    if on_progress and time.monotonic() - last_update > 0.15:
                        on_progress(scanned, total, rel)
                        last_update = time.monotonic()
                except OSError:
                    continue
        if on_progress:
            on_progress(scanned, total, f"Папка «{root.name}»: сканирование завершено")
        return data

    @staticmethod
    def file_hash(path: Path, cancel_event: threading.Event | None = None) -> str:
        """Compute sha256 hash with cooperative cancellation support."""
        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Operation cancelled")
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
                if cancel_event and cancel_event.is_set():
                    raise RuntimeError("Operation cancelled")
        return h.hexdigest()

    @staticmethod
    def copy_file_streaming(
        src: Path,
        dst: Path,
        on_chunk_progress: Callable[[int], None] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> int:
        """Copy file by chunks and report copied bytes for live progress UI."""
        chunk_size = 1024 * 1024
        copied = 0
        last_ui = 0.0
        dst.parent.mkdir(parents=True, exist_ok=True)

        with src.open("rb") as fsrc, dst.open("wb") as fdst:
            while True:
                if cancel_event and cancel_event.is_set():
                    raise RuntimeError("Operation cancelled")
                buf = fsrc.read(chunk_size)
                if not buf:
                    break
                fdst.write(buf)
                copied += len(buf)
                if on_chunk_progress:
                    now = time.monotonic()
                    if now - last_ui > 0.2:
                        on_chunk_progress(copied)
                        last_ui = now

        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Operation cancelled")
        try:
            shutil.copystat(src, dst)
        except OSError:
            pass

        return copied

    @staticmethod
    def analyze_differences(
        src_files: dict,
        dst_files: dict,
        source_root: Path,
        backup_root: Path,
        file_hash_fn: Callable[[Path, threading.Event | None], str] | None = None,
        cancel_event: threading.Event | None = None,
        on_progress: Callable[[int, int, str], None] | None = None,
    ) -> dict:
        """Build sync plan between source (USB) and backup folder states."""
        hash_fn = file_hash_fn or BackupLogic.file_hash
        dst_lookup = {k.lower(): v for k, v in dst_files.items()}

        copy_to_backup_ops = []
        copy_to_usb_ops = []
        matched = 0
        new_on_usb = 0
        changed_on_usb = 0
        changed_on_backup = 0
        common_paths = 0

        total_items = len(src_files)
        processed = 0

        for rel, src in src_files.items():
            if cancel_event and cancel_event.is_set():
                raise RuntimeError("Operation cancelled")

            processed += 1
            if on_progress:
                on_progress(processed, total_items, rel)

            dst = dst_lookup.get(rel.lower())
            if not dst:
                new_on_usb += 1
                copy_to_backup_ops.append((src["path"], backup_root / rel, src["size"], rel))
                continue

            common_paths += 1
            same_size = dst["size"] == src["size"]
            same_mtime = abs(dst["mtime"] - src["mtime"]) < 0.001
            if same_size and same_mtime:
                matched += 1
                continue

            if same_size:
                try:
                    src_hash = hash_fn(src["path"], cancel_event)
                    dst_hash = hash_fn(dst["path"], cancel_event)
                    if src_hash == dst_hash:
                        matched += 1
                        continue
                except (OSError, RuntimeError):
                    pass

            if src["mtime"] >= dst["mtime"]:
                changed_on_usb += 1
                copy_to_backup_ops.append((src["path"], backup_root / rel, src["size"], rel))
            else:
                changed_on_backup += 1
                copy_to_usb_ops.append((dst["path"], source_root / rel, dst["size"], rel))

        src_lower = {k.lower() for k in src_files}
        extra_in_backup = sorted(k for k in dst_files if k.lower() not in src_lower)
        extra_on_usb = sorted(k for k in src_files if k.lower() not in dst_lookup)
        for rel in extra_in_backup:
            b = dst_files[rel]
            copy_to_usb_ops.append((b["path"], source_root / rel, b["size"], rel))

        similarity = common_paths / max(1, len(src_files))
        if not dst_files or similarity < 0.5:
            mode = "full"
            copy_to_backup_ops = [(v["path"], backup_root / k, v["size"], k) for k, v in src_files.items()]
        elif copy_to_backup_ops or copy_to_usb_ops:
            mode = "sync"
        else:
            mode = "none"

        return {
            "mode": mode,
            "ops_to_backup": copy_to_backup_ops,
            "ops_to_usb": copy_to_usb_ops,
            "bytes_to_backup": sum(item[2] for item in copy_to_backup_ops),
            "bytes_to_usb": sum(item[2] for item in copy_to_usb_ops),
            "extra_in_backup": extra_in_backup,
            "extra_on_usb": extra_on_usb,
            "matched": matched,
            "new_on_usb": new_on_usb,
            "changed_on_usb": changed_on_usb,
            "changed_on_backup": changed_on_backup,
            "common_paths": common_paths,
        }
