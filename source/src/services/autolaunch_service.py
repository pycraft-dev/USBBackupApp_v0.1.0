"""Windows Task Scheduler helpers for USB auto-launch."""

import ctypes
import subprocess
import sys
from pathlib import Path

from device_detector import DeviceDetector


class AutoLaunchService:
    """Pure service layer for creating/removing USB auto-launch tasks."""

    TASK_NAME = "USBBackupApp_AutoLaunch"
    OPERATIONAL_LOG = "Microsoft-Windows-DriverFrameworks-UserMode/Operational"
    EVENT_XPATH = "*[System[(EventID=2003 or EventID=2100 or EventID=2102)]]"

    @staticmethod
    def is_admin() -> bool:
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    @classmethod
    def current_executable_and_args(cls, autostart_device_id: str, entry_script_path: Path) -> tuple[str, str]:
        arg_tail = ["--autostart-device-id", str(autostart_device_id or "")]
        if getattr(sys, "frozen", False):
            exe = sys.executable
            args = subprocess.list2cmdline(arg_tail)
            return exe, args
        exe = sys.executable
        args = subprocess.list2cmdline([str(entry_script_path)] + arg_tail)
        return exe, args

    @classmethod
    def create_task_for_device(cls, drive_letter: str, autostart_device_id: str, entry_script_path: Path) -> dict:
        normalized_drive = Path(drive_letter).drive.replace(":", "")
        instance_path = DeviceDetector.get_device_instance_path(normalized_drive)
        exe, arguments = cls.current_executable_and_args(autostart_device_id, entry_script_path)

        try:
            subprocess.run(
                ["wevtutil", "sl", cls.OPERATIONAL_LOG, "/e:true"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except Exception:
            pass

        tr = f"\"{exe}\" {arguments}".strip()
        cmd = [
            "schtasks",
            "/Create",
            "/F",
            "/TN",
            cls.TASK_NAME,
            "/SC",
            "ONEVENT",
            "/EC",
            cls.OPERATIONAL_LOG,
            "/MO",
            cls.EVENT_XPATH,
            "/RL",
            "HIGHEST",
            "/TR",
            tr,
        ]
        completed = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        return {
            "instance_path": instance_path,
            "returncode": int(completed.returncode),
            "stdout": (completed.stdout or "").strip(),
            "stderr": (completed.stderr or "").strip(),
        }

    @classmethod
    def delete_task(cls) -> dict:
        completed = subprocess.run(
            ["schtasks", "/Delete", "/TN", cls.TASK_NAME, "/F"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return {
            "returncode": int(completed.returncode),
            "stdout": (completed.stdout or "").strip(),
            "stderr": (completed.stderr or "").strip(),
        }
