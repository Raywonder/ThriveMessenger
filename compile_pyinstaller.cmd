@echo off
uv run python versionfile.py
uv run pyinstaller --clean --noconfirm thrive_messenger.spec
