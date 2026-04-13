"""Formatting helpers for progress, ETA and transfer metrics."""

import math
from datetime import timedelta


class ProgressPresenter:
    """UI-agnostic formatter used by main window progress labels."""

    @staticmethod
    def format_seconds(seconds) -> str:
        if seconds is None:
            return "--:--:--"
        return str(timedelta(seconds=max(0, int(math.ceil(seconds)))))

    @staticmethod
    def format_size(num_bytes: int) -> str:
        units = ["Б", "КБ", "МБ", "ГБ"]
        size = float(max(0, num_bytes))
        idx = 0
        while size >= 1024 and idx < len(units) - 1:
            size /= 1024
            idx += 1
        return f"{size:.1f} {units[idx]}"

    @staticmethod
    def format_speed_and_remaining(speed_bps: float, remaining_items: int, remaining_bytes: int) -> str:
        mbps = speed_bps / (1024 * 1024)
        return (
            f"Скорость: {mbps:.2f} МБ/с | "
            f"Осталось элементов: {max(0, remaining_items)} ({ProgressPresenter.format_size(remaining_bytes)})"
        )
