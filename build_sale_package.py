#!/usr/bin/env python3
"""Сборка ZIP-пакета USBBackupApp_Sale_v* для передачи клиенту."""

from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

# Имя русской инструкции в ZIP (кириллица через escapes — надёжно на всех кодировках исходника .py).
RU_README_SALE_NAME = "README_\u041a\u041b\u0418\u0415\u041d\u0422\u0423.md"


def _parse_args() -> argparse.Namespace:
    """Разбор аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description="Собирает папку USBBackupApp_Sale_v* и архивирует её в ZIP.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Корень репозитория (по умолчанию — каталог этого скрипта).",
    )
    parser.add_argument(
        "--version",
        default="1.0",
        help='Версия продажного пакета, например "1.0" (имя папки и ZIP).',
    )
    parser.add_argument(
        "--exe",
        type=Path,
        default=None,
        help="Путь к USBBackupApp.exe (по умолчанию source/dist/USBBackupApp.exe).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Куда положить ZIP (по умолчанию — корень репозитория).",
    )
    parser.add_argument(
        "--staging-dir",
        type=Path,
        default=None,
        help="Базовая папка для временной сборки (по умолчанию sale_staging в корне).",
    )
    parser.add_argument(
        "--skip-inno",
        action="store_true",
        help="Зарезервировано: компиляция Inno Setup не вызывается из этого скрипта.",
    )
    return parser.parse_args()


def _copy_file(src: Path, dst: Path) -> None:
    """Копирует один файл с созданием родительских каталогов."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _copy_tree(src: Path, dst: Path) -> None:
    """Копирует каталог целиком."""
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def _write_license_txt(repo: Path, dst: Path) -> None:
    """Формирует LICENSE.txt из корневого LICENSE."""
    license_src = repo / "LICENSE"
    if not license_src.is_file():
        raise FileNotFoundError(f"Не найден файл лицензии: {license_src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(license_src.read_text(encoding="utf-8"), encoding="utf-8")


def _zip_datetime_from_mtime(path: Path) -> tuple[int, ...]:
    """Возвращает поля date_time для ZipInfo из mtime файла."""
    ts = path.stat().st_mtime
    dt = datetime.fromtimestamp(ts)
    return (dt.year, dt.month, dt.day, dt.hour, dt.minute, int(dt.second))


def _zip_directory(folder: Path, zip_path: Path) -> None:
    """Упаковывает каталог так, чтобы в архиве был один корневой каталог с именем folder.name."""
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in folder.rglob("*"):
            if not path.is_file():
                continue
            arcname = path.relative_to(folder.parent).as_posix()
            zinfo = zipfile.ZipInfo(arcname, _zip_datetime_from_mtime(path))
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            zinfo.flag_bits |= 0x800
            zinfo.external_attr = 0o644 << 16
            payload = path.read_bytes()
            zf.writestr(zinfo, payload)


def main() -> int:
    """Точка входа: проверки, копирование, ZIP."""
    args = _parse_args()
    _ = args.skip_inno  # флаг оставлен для совместимости с планом

    repo = (args.root or Path(__file__).resolve().parent).resolve()
    out_dir = (args.out_dir or repo).resolve()
    staging_base = (args.staging_dir or (repo / "sale_staging")).resolve()
    version = (args.version or "1.0").strip()
    package_name = f"USBBackupApp_Sale_v{version}"
    staging = staging_base / package_name

    exe_default = repo / "source" / "dist" / "USBBackupApp.exe"
    exe_path = (args.exe or exe_default).resolve()

    required_docs = [
        repo / "README_RU.md",
        repo / "README_CLIENT.md",
        repo / "SUPPORT.md",
        repo / "docs" / "CHANGELOG.md",
        repo / "config" / "app_state.json.example",
    ]
    shots_src = repo / "screenshots"

    if not exe_path.is_file():
        print(
            f"Ошибка: не найден exe: {exe_path}\n"
            "Соберите проект: из папки source выполните\n"
            "  pyinstaller --noconfirm USBBackupApp.spec",
            file=sys.stderr,
        )
        return 1

    missing = [p for p in required_docs if not p.is_file()]
    if missing:
        print("Ошибка: не хватает файлов для пакета:", file=sys.stderr)
        for p in missing:
            print(f"  - {p}", file=sys.stderr)
        return 1

    if not shots_src.is_dir() or not any(shots_src.iterdir()):
        print(f"Ошибка: папка скриншотов пуста или отсутствует: {shots_src}", file=sys.stderr)
        return 1

    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    _copy_file(exe_path, staging / "USBBackupApp.exe")
    _copy_file(required_docs[0], staging / RU_README_SALE_NAME)
    _copy_file(required_docs[1], staging / "README_CLIENT.md")
    _copy_file(required_docs[2], staging / "SUPPORT.md")
    _copy_file(required_docs[3], staging / "CHANGELOG.md")
    _write_license_txt(repo, staging / "LICENSE.txt")
    _copy_tree(shots_src, staging / "screenshots")
    staging_config = staging / "config"
    staging_config.mkdir(parents=True, exist_ok=True)
    _copy_file(required_docs[4], staging_config / "app_state.json.example")

    zip_name = f"{package_name}.zip"
    zip_path = out_dir / zip_name
    out_dir.mkdir(parents=True, exist_ok=True)
    _zip_directory(staging, zip_path)

    print(f"Готово: {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
