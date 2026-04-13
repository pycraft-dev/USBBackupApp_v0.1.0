"""Utilities for detecting source drives on Windows.

This module isolates OS-specific logic (ctypes/PowerShell) so UI code can work
with a simple `DeviceInfo` structure.
"""

import ctypes
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List


DRIVE_REMOVABLE = 2
DRIVE_FIXED = 3


@dataclass
class DeviceInfo:
    """Normalized info about a selectable source drive."""

    drive: str
    volume_label: str
    device_id: str
    drive_kind: str


class DeviceDetector:
    @staticmethod
    def list_source_devices() -> List[DeviceInfo]:
        """Return removable/fixed drives available for backup source selection."""

        drives: List[DeviceInfo] = []
        system_drive = os.environ.get("SystemDrive", "C:").upper() + "\\"
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for i in range(26):
            if not (bitmask & (1 << i)):
                continue
            drive_letter = f"{chr(65 + i)}:\\"
            drive_type = ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(drive_letter))
            if drive_type not in (DRIVE_REMOVABLE, DRIVE_FIXED):
                continue
            if drive_type == DRIVE_FIXED and drive_letter.upper() == system_drive:
                # Hide Windows system disk from source selection to prevent accidental full scans.
                continue

            label_buffer = ctypes.create_unicode_buffer(261)
            fs_buffer = ctypes.create_unicode_buffer(261)
            serial_num = ctypes.c_ulong()
            max_comp_len = ctypes.c_ulong()
            fs_flags = ctypes.c_ulong()

            success = ctypes.windll.kernel32.GetVolumeInformationW(
                ctypes.c_wchar_p(drive_letter),
                label_buffer,
                ctypes.sizeof(label_buffer),
                ctypes.byref(serial_num),
                ctypes.byref(max_comp_len),
                ctypes.byref(fs_flags),
                fs_buffer,
                ctypes.sizeof(fs_buffer),
            )

            label = label_buffer.value if success else "UNKNOWN"
            device_id = f"{drive_letter}_{serial_num.value if success else '0'}"
            kind = "USB" if drive_type == DRIVE_REMOVABLE else "DISK"
            drives.append(DeviceInfo(drive=drive_letter, volume_label=label, device_id=device_id, drive_kind=kind))
        return drives

    @staticmethod
    def drive_exists(drive: str) -> bool:
        """Fast existence check for drive root like `E:\\`."""
        return Path(drive).exists()

    @staticmethod
    def get_device_instance_path(drive_letter: str) -> str:
        """
        Return Windows PNP Device Instance Path for the physical device behind a drive letter.
        Example: USB\\VID_8644&PID_8003\\052073000000031D
        """
        dl = drive_letter.rstrip(":").upper() + ":"

        # More reliable mapping:
        # LogicalDisk (E:) -> associated DiskPartition -> associated DiskDrive -> PNPDeviceID
        ps = rf"""
$dl = "{dl}"
$ld = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$dl'" | Select-Object -First 1
if (-not $ld) {{ throw "Logical disk not found for drive letter $dl" }}
$part = $ld | Get-CimAssociatedInstance -ResultClassName Win32_DiskPartition | Select-Object -First 1
if (-not $part) {{ throw "No partition found for drive letter $dl" }}
$disk = $part | Get-CimAssociatedInstance -ResultClassName Win32_DiskDrive | Select-Object -First 1
if (-not $disk) {{ throw "No disk drive found for drive letter $dl" }}
$disk.PNPDeviceID
""".strip()

        completed = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if completed.returncode != 0:
            raise RuntimeError((completed.stderr or completed.stdout or "").strip() or f"PowerShell error: {completed.returncode}")

        out = (completed.stdout or "").strip()
        if not out:
            raise RuntimeError("Empty PNPDeviceID returned")
        return out
