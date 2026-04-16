"""WMI-демон: отслеживание вставки USB и запуск UI по серийнику."""

from __future__ import annotations

import ctypes
import subprocess
import sys
import time
from pathlib import Path


def _debug_log(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    """Заглушка: отладочный лог отключён."""
    _ = (hypothesis_id, location, message, data)
    return


def _get_volume_serial_hex(drive_letter: str) -> str | None:
    """Возвращает серийник тома в HEX (8 символов) для буквы диска."""
    try:
        root = drive_letter.rstrip(":").upper() + ":\\"
        serial = ctypes.c_ulong()
        max_comp_len = ctypes.c_ulong()
        fs_flags = ctypes.c_ulong()
        label_buf = ctypes.create_unicode_buffer(261)
        fs_buf = ctypes.create_unicode_buffer(261)
        ok = ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(root),
            label_buf,
            ctypes.sizeof(label_buf),
            ctypes.byref(serial),
            ctypes.byref(max_comp_len),
            ctypes.byref(fs_flags),
            fs_buf,
            ctypes.sizeof(fs_buf),
        )
        if not ok:
            return None
        return format(int(serial.value), "08X")
    except Exception:
        return None


def _get_event_drive_serial_hex(drive_name: str) -> str | None:
    """Возвращает серийник тома для буквы диска из WMI-события."""
    try:
        value = str(drive_name or "").strip()
        if len(value) < 2 or value[1] != ":":
            return None
        return _get_volume_serial_hex(value[0])
    except Exception:
        return None


def _is_target_drive_connected(target_serial_hex: str) -> bool:
    """Проверяет наличие целевой флешки по серийному номеру тома (HEX)."""
    try:
        target = (target_serial_hex or "").strip().upper()
        if not target:
            return False
        get_drive_type = ctypes.windll.kernel32.GetDriveTypeW
        for i in range(26):
            letter = chr(65 + i)
            root = f"{letter}:\\"
            try:
                if int(get_drive_type(ctypes.c_wchar_p(root))) != 2:  # DRIVE_REMOVABLE
                    continue
                serial_hex = _get_volume_serial_hex(letter)
                if serial_hex and serial_hex.upper() == target:
                    return True
            except Exception:
                continue
        return False
    except Exception:
        return False


def _launch_ui() -> None:
    """Запускает UI-экземпляр приложения без консольного окна."""
    try:
        creationflags = 0
        try:
            creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
        except Exception:
            creationflags = 0

        if getattr(sys, "frozen", False):
            exe = str(Path(sys.executable).resolve())
            subprocess.Popen([exe], creationflags=creationflags)
            return

        # dev mode: run python script
        entry = str((Path(__file__).resolve().parents[1] / "main.py").resolve())
        subprocess.Popen([sys.executable, entry], creationflags=creationflags)
    except Exception:
        return


def run_wmi_daemon(target_serial_hex: str) -> int:
    """Запускает WMI-демон и блокирует поток до завершения."""
    target = (target_serial_hex or "").strip().upper()
    if not target:
        return 2

    try:
        import win32com.client  # type: ignore[import-not-found]
    except Exception:
        return 3

    try:
        locator = win32com.client.Dispatch("WbemScripting.SWbemLocator")
        svc = locator.ConnectServer(".", "root\\cimv2")
        # EventType=2 => Device arrival
        q = "SELECT * FROM Win32_VolumeChangeEvent WHERE EventType = 2"
        watcher = svc.ExecNotificationQuery(q)
    except Exception:
        return 4

    last_launch_ts_ms = 0
    while True:
        try:
            evt = watcher.NextEvent()
            drive_name = ""
            try:
                drive_name = str(getattr(evt, "DriveName", "") or "")
            except Exception:
                drive_name = ""

            now_ms = int(time.time() * 1000)
            event_serial_hex = _get_event_drive_serial_hex(drive_name)

            # Debounce burst events
            if now_ms - last_launch_ts_ms < 800:
                continue

            connected = _is_target_drive_connected(target)
            event_matches_target = bool(event_serial_hex and event_serial_hex.upper() == target)
            _ = connected
            # Launch ONLY when the inserted volume matches the target.
            # Otherwise inserting any other USB while target is connected would launch UI.
            if event_matches_target:
                last_launch_ts_ms = now_ms
                _launch_ui()
        except Exception:
            continue

