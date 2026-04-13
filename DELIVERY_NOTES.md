# DELIVERY NOTES

Версия поставки: `0.1.0`

## Содержимое клиентского архива

- `source/` — исходный код проекта, ресурсы, конфигурация и документация для разработчика.
- `release/USBBackupApp_v0.1.0/USBBackupApp.exe` — готовый исполняемый файл для Windows.
- `docs/` — пользовательская документация и лицензии.

## Запуск для клиента

1. Откройте папку `release/USBBackupApp_v0.1.0/`.
2. Запустите `USBBackupApp.exe`.
3. Руководство пользователя: `docs/USER_GUIDE.md`.

## Сборка из исходников

Все команды выполняются из папки `source/`.

Установка зависимостей:

```powershell
pip install -r requirements.txt
```

Сборка через spec-файл:

```powershell
pyinstaller --noconfirm USBBackupApp.spec
```

Готовый exe будет в `source/dist/USBBackupApp.exe`.

## Что сознательно исключено из поставки

- Локальные/временные артефакты: `build/`, `dist/`, `__pycache__/`, `*.pyc`.
- Диагностические логи: `*.log` (в релизной версии не создаются).
- Локальное состояние клиента: `config/app_state.json`.
- Персональные настройки профилей в `config/profiles.json` заменены на пустой шаблон.
