@echo off
where uv >nul 2>nul
if %errorlevel%==0 (
    uv run python versionfile.py
    uv run pyinstaller --clean --noconfirm thrive_messenger.spec
) else (
    py -3 versionfile.py
    py -3 -m PyInstaller --clean --noconfirm thrive_messenger.spec
)
