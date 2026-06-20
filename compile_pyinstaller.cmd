@echo off
where uv >nul 2>nul
if %errorlevel%==0 (
    uv run python -c "import wx, wx.adv, wx.html2, wx.media, keyring, plyer, winotify, accessible_output2, sounddevice"
    uv run python versionfile.py
    uv run pyinstaller --clean --noconfirm thrive_messenger.spec
) else (
    py -3 -c "import wx, wx.adv, wx.html2, wx.media, keyring, plyer, winotify, accessible_output2, sounddevice"
    py -3 versionfile.py
    py -3 -m PyInstaller --clean --noconfirm thrive_messenger.spec
)
