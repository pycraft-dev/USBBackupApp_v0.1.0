"""Thin application entrypoint."""

import argparse
import ctypes
import subprocess
import sys
from pathlib import Path

import customtkinter as ctk

from ui.main_window import BackupApp
from services.wmi_daemon import run_wmi_daemon

ERROR_ALREADY_EXISTS = 183
_SINGLE_INSTANCE_MUTEX = None


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


def main() -> None:
    """Parse CLI args, enforce single-instance/elevation, then start UI loop."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--autostart-device-id", default="")
    parser.add_argument("--autostart-volume-label", default="")
    parser.add_argument("--wmi-daemon", action="store_true")
    parser.add_argument("--wmi-target-serial", default="")
    parser.add_argument("--elevated", action="store_true")
    args, _unknown = parser.parse_known_args()

    if bool(args.wmi_daemon):
        # Background daemon mode: no UI, just watch for target and launch UI.
        # Note: this should be started by Task Scheduler "At log on".
        _ = run_wmi_daemon(str(args.wmi_target_serial or "").strip())
        return

    if args.autostart_device_id:
        if not _is_target_drive_connected(str(args.autostart_device_id).strip()):
            sys.exit(0)

    # Task Scheduler can emit several arrival events quickly.
    # Avoid multiple app windows for one USB insert.
    if args.autostart_device_id:
        try:
            global _SINGLE_INSTANCE_MUTEX
            _SINGLE_INSTANCE_MUTEX = ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\USBBackupApp_Autostart")
            if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
                return
        except Exception:
            pass

    # Auto-elevate to admin (UAC prompt) when needed.
    # Many operations (diskpart, task scheduler, enabling logs) require admin rights.
    is_admin = BackupApp._is_admin()
    if not is_admin and not args.elevated:
        # Autostart should not depend on UAC; Task Scheduler launch can fail to show prompt.
        try:
            tail = [a for a in sys.argv[1:] if a != "--elevated"]
            if getattr(sys, "frozen", False):
                exe_path = str(Path(sys.executable).resolve())
                cwd = str(Path(sys.executable).resolve().parent)
                params = subprocess.list2cmdline(tail + ["--elevated"])
                ctypes.windll.shell32.ShellExecuteW(None, "runas", exe_path, params, cwd, 1)
            else:
                script_path = str(Path(__file__).resolve())
                cwd = str(Path(__file__).resolve().parents[1])
                params = subprocess.list2cmdline([script_path] + tail + ["--elevated"])
                ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, cwd, 1)
        except Exception:
            pass
        if not args.autostart_device_id:
            return

    root = ctk.CTk()
    app = BackupApp(
        root,
        autostart_device_id=args.autostart_device_id,
        autostart_volume_label=args.autostart_volume_label,
    )
    _ = app
    root.mainloop()


if __name__ == "__main__":
    main()

