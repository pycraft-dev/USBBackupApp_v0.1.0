# USB Backup App — user guide (English)

## What this application does

**USB Backup App** compares your selected USB drive (or disk) with a backup folder on your PC and guides you through the right action: full backup to disk, updating the backup folder from the USB, or copying differences back to the USB. Progress and logs stay in a single main window during normal operation.

## System requirements

- **OS:** Windows 10 or Windows 11 (64-bit recommended).
- **Administrator rights:** required **only** to configure **USB autostart** (Task Scheduler). Regular scanning and copying do not need elevation.
- **Internet:** not required.
- **Python:** not required — use the provided `USBBackupApp.exe`.

## Optional installer (Inno Setup)

The default delivery is a **ZIP** with portable `USBBackupApp.exe`. Extract it anywhere and run the executable.

If you build an **installer** yourself (for IT or a store page), install [Inno Setup](https://jrsoftware.org/isinfo.php) and run from the developer repository root:

```text
ISCC.exe USBBackupApp.iss
```

The compiled setup will appear under `installer_output\` (see `USBBackupApp.iss`). End users only need the sale ZIP described in the developer documentation.

## Quick path: download → run → configure → done

1. **Download** `USBBackupApp_Sale_vX.Y.zip` and extract it (e.g. to `Documents\USBBackupApp`).
2. **Run** `USBBackupApp.exe`. On first launch, Windows SmartScreen may warn about an unknown publisher — use “More info” → “Run anyway” if you trust the source.
3. **Configure:**
   - under **Source**, pick your USB drive (use **Refresh** if it is missing);
   - under **Settings**, choose the **Backup folder** (**Browse**);
   - click **Scan folder** and wait until analysis finishes;
   - click the highlighted action (**FULL BACKUP**, **UPDATE BACKUP FOLDER**, or **PUSH DIFFERENCES TO USB**).
4. **Done:** wait until copying finishes; you can **stop** the operation from the bottom panel if needed.

When using the EXE build, settings are stored automatically in `%APPDATA%\USBBackupApp\app_state.json` (last backup folder). A non-personal template is included as `config\app_state.json.example`.

## Screenshots

Captions for files in the `screenshots\` folder:

| File | Description |
|------|-------------|
| [screenshots/01_main_window.png](screenshots/01_main_window.png) | Main window: source drive, backup path, scan control. |
| [screenshots/02_progress.png](screenshots/02_progress.png) | Bottom panel: copy progress, current file, ETA and speed. |
| [screenshots/03_settings.png](screenshots/03_settings.png) | Settings and mode block (action buttons after analysis). |

> Replace the PNG files under `screenshots\` with final marketplace screenshots if the archive still contains draft images.

## FAQ

### The app will not start

Check SmartScreen and antivirus. Run the EXE from an extracted folder, not from inside the ZIP. Confirm Windows 10/11.

### Scanning seems slow

After file enumeration, **difference analysis** runs — this is expected. Watch the bottom status line.

### Some files were skipped

Files may be locked by another app or cloud sync (e.g. OneDrive). A warning dialog may list skipped paths — close locking apps and retry.

### How do I disable autostart?

1. Run **USB Backup App as Administrator**.
2. Under **Autostart for this USB**, click **Disable autostart**.
3. Wait for the success confirmation.

Alternatively, open **Windows Task Scheduler** and remove the task created by the app (task name is defined in developer docs / sources — typically related to `USBBackupApp`).

### Is internet required?

No.

### Does the app delete files from the USB?

The main workflow is **copying and syncing** according to the selected mode. Test on copies of important data first.

## License and files

- MIT license: `LICENSE.txt` in the package.
- Release notes: `CHANGELOG.md`.
- Support contacts: `SUPPORT.md`.

Russian user guide (repository): [README_RU.md](README_RU.md). In the sale ZIP the same text is shipped as `README_КЛИЕНТУ.md`.
