# Portable Python Runtime (Optional)

Place a self-contained Python runtime in this folder for zero-manual-install builds.

## Windows
Put `python.exe` and its runtime files directly under this directory, for example:
- `desktop/runtime/python/python.exe`
- `desktop/runtime/python/python312.dll`
- `desktop/runtime/python/Lib/...` or equivalent portable layout

The app will auto-detect bundled runtime paths from Tauri resources at startup.

## Notes
- If this folder is empty, PhenoAI falls back to app venv/system Python detection.
- For fully offline installers, pre-bundle required packages in this runtime or ensure setup can install them.
