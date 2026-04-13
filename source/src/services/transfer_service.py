"""Transfer execution service (copy loop, cancellation, skip handling)."""

import time
from pathlib import Path
from typing import Callable


class TransferService:
    """Run copy operations independent from UI widgets."""

    @staticmethod
    def run_copy_loop(
        ops: list[tuple[Path, Path, int, str]] | list[tuple[str, str, int, str]],
        action: str,
        bytes_total: int,
        cancel_event,
        copy_streaming_fn: Callable[[Path, Path, str, int, float, str, int, int, int], int],
        on_progress: Callable[[int, int, int, int, str, float, str], None],
        on_cancelled: Callable[[str, int, int], None],
        on_finished: Callable[[str, int, int, list[tuple[str, str]]], None],
        on_error: Callable[[Exception, str], None],
    ) -> None:
        total = len(ops)
        done = 0
        bytes_done = 0
        permission_skipped: list[tuple[str, str]] = []
        start_ts = time.monotonic()
        last_rel = ""

        try:
            for src, dst, size, rel in ops:
                last_rel = rel
                if cancel_event and cancel_event.is_set():
                    on_cancelled(action, done, bytes_done)
                    return

                src_path = Path(src)
                dst_path = Path(dst)
                dst_path.parent.mkdir(parents=True, exist_ok=True)

                try:
                    copied_bytes = copy_streaming_fn(
                        src_path,
                        dst_path,
                        rel,
                        bytes_total,
                        start_ts,
                        action,
                        done,
                        total,
                        bytes_done,
                    )
                except PermissionError as perm_err:
                    permission_skipped.append((rel, str(perm_err)))
                    done += 1
                    bytes_done += int(size or 0)
                    on_progress(done, total, bytes_done, bytes_total, rel, start_ts, action)
                    continue

                done += 1
                bytes_done += int(copied_bytes or size or 0)
                on_progress(done, total, bytes_done, bytes_total, rel, start_ts, action)

            on_finished(action, total, bytes_total, permission_skipped)
        except Exception as exc:
            if str(exc) == "Operation cancelled" or (cancel_event and cancel_event.is_set()):
                on_cancelled(action, done, bytes_done)
                return
            on_error(exc, last_rel)
