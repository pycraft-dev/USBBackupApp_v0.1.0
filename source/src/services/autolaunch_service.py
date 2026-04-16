"""Windows Task Scheduler helpers for USB auto-launch."""

import ctypes
import subprocess
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from xml.etree import ElementTree as ET


class AutoLaunchService:
    """Pure service layer for creating/removing USB auto-launch tasks."""

    TASK_NAME = "USBBackupApp_WMI_Daemon"
    LEGACY_TASK_NAME = "USBBackupApp_AutoLaunch"

    @staticmethod
    def is_admin() -> bool:
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    @classmethod
    def current_executable_and_args(cls, autostart_device_id: str, entry_script_path: Path) -> tuple[str, str]:
        # Run the WMI daemon at user logon; it will launch the UI when target is inserted.
        arg_tail = ["--wmi-daemon", "--wmi-target-serial", str(autostart_device_id or "").strip().upper()]
        if getattr(sys, "frozen", False):
            exe = sys.executable
            args = subprocess.list2cmdline(arg_tail)
            return exe, args
        exe = sys.executable
        args = subprocess.list2cmdline([str(entry_script_path)] + arg_tail)
        return exe, args

    @classmethod
    def _build_logon_task_xml(cls, command: str, arguments: str) -> str:
        """Генерирует XML задачи Планировщика для демона WMI."""
        # Important: allow running on batteries and keep daemon alive.
        # Use HighestAvailable, InteractiveToken (user context).
        return (
            '<?xml version="1.0" encoding="UTF-16"?>\r\n'
            '<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">\r\n'
            "  <RegistrationInfo>\r\n"
            "    <Date>2026-04-16T00:00:00</Date>\r\n"
            "    <Author>USBBackupApp</Author>\r\n"
            f"    <URI>\\{cls.TASK_NAME}</URI>\r\n"
            "  </RegistrationInfo>\r\n"
            "  <Triggers>\r\n"
            "    <LogonTrigger>\r\n"
            "      <Enabled>true</Enabled>\r\n"
            "    </LogonTrigger>\r\n"
            "  </Triggers>\r\n"
            "  <Principals>\r\n"
            '    <Principal id="Author">\r\n'
            "      <LogonType>InteractiveToken</LogonType>\r\n"
            "      <RunLevel>HighestAvailable</RunLevel>\r\n"
            "    </Principal>\r\n"
            "  </Principals>\r\n"
            "  <Settings>\r\n"
            "    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>\r\n"
            "    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>\r\n"
            "    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>\r\n"
            "    <StartWhenAvailable>true</StartWhenAvailable>\r\n"
            "    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>\r\n"
            "    <IdleSettings>\r\n"
            "      <StopOnIdleEnd>false</StopOnIdleEnd>\r\n"
            "      <RestartOnIdle>false</RestartOnIdle>\r\n"
            "    </IdleSettings>\r\n"
            "    <AllowStartOnDemand>true</AllowStartOnDemand>\r\n"
            "    <Enabled>true</Enabled>\r\n"
            "    <Hidden>false</Hidden>\r\n"
            "    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>\r\n"
            "    <RestartOnFailure>\r\n"
            "      <Interval>PT1M</Interval>\r\n"
            "      <Count>999</Count>\r\n"
            "    </RestartOnFailure>\r\n"
            "  </Settings>\r\n"
            '  <Actions Context="Author">\r\n'
            "    <Exec>\r\n"
            f"      <Command>{command}</Command>\r\n"
            f"      <Arguments>{arguments}</Arguments>\r\n"
            "    </Exec>\r\n"
            "  </Actions>\r\n"
            "</Task>\r\n"
        )

    @classmethod
    def create_task_for_device(cls, drive_letter: str, autostart_device_id: str, entry_script_path: Path) -> dict:
        # Clean legacy task if it exists (older ONEVENT-based autostart).
        try:
            _ = cls._delete_task_by_name(cls.LEGACY_TASK_NAME)
        except Exception:
            pass

        exe, arguments = cls.current_executable_and_args(autostart_device_id, entry_script_path)

        xml_text = cls._build_logon_task_xml(command=str(exe), arguments=str(arguments))
        xml_path = ""
        try:
            with NamedTemporaryFile("wb", delete=False, suffix=".xml") as f:
                xml_path = f.name
                f.write(xml_text.encode("utf-16"))
        except Exception as e:
            raise

        cmd = ["schtasks", "/Create", "/F", "/TN", cls.TASK_NAME, "/XML", xml_path]
        creationflags = 0
        try:
            creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
        except Exception:
            creationflags = 0
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
        )
        try:
            if xml_path:
                Path(xml_path).unlink(missing_ok=True)  # type: ignore[arg-type]
        except Exception:
            pass
        return {
            "instance_path": "",
            "returncode": int(completed.returncode),
            "stdout": (completed.stdout or "").strip(),
            "stderr": (completed.stderr or "").strip(),
        }

    @classmethod
    def delete_task(cls) -> dict:
        main = cls._delete_task_by_name(cls.TASK_NAME)
        legacy = cls._delete_task_by_name(cls.LEGACY_TASK_NAME)
        # Return the main task result, but include legacy outcome in stdout for debugging.
        return {
            "returncode": int(main["returncode"]),
            "stdout": (str(main.get("stdout") or "").strip() + "\n" + str(legacy.get("stdout") or "").strip()).strip(),
            "stderr": (str(main.get("stderr") or "").strip() + "\n" + str(legacy.get("stderr") or "").strip()).strip(),
        }

    @classmethod
    def get_enabled_target_serial_hex(cls) -> str:
        """Возвращает HEX-серийник цели из задачи демона, либо пустую строку."""
        creationflags = 0
        try:
            creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
        except Exception:
            creationflags = 0

        completed = subprocess.run(
            ["schtasks", "/Query", "/TN", cls.TASK_NAME, "/XML"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
        )
        if int(completed.returncode) != 0:
            return ""

        xml_text = (completed.stdout or "").strip()
        args_text = ""
        try:
            root = ET.fromstring(xml_text)
            # Task XML uses namespaces; search by local-name to be robust.
            for el in root.iter():
                if str(getattr(el, "tag", "")).endswith("Arguments"):
                    args_text = str(el.text or "")
                    break
        except Exception as e:
            return ""

        target = cls._extract_target_serial_from_args(args_text)
        return target

    @staticmethod
    def _extract_target_serial_from_args(args_text: str) -> str:
        """Извлекает значение после `--wmi-target-serial` из строки аргументов."""
        try:
            raw = str(args_text or "").strip()
            if not raw:
                return ""
            parts = raw.replace("\r", " ").replace("\n", " ").split()
            for i, p in enumerate(parts):
                if p.strip().lower() == "--wmi-target-serial" and i + 1 < len(parts):
                    return str(parts[i + 1]).strip().strip("\"'").upper()
            return ""
        except Exception:
            return ""

    @classmethod
    def _delete_task_by_name(cls, task_name: str) -> dict:
        creationflags = 0
        try:
            creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
        except Exception:
            creationflags = 0
        completed = subprocess.run(
            ["schtasks", "/Delete", "/TN", str(task_name), "/F"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
        )
        return {
            "returncode": int(completed.returncode),
            "stdout": (completed.stdout or "").strip(),
            "stderr": (completed.stderr or "").strip(),
        }
