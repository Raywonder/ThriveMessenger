# NVDA controller client

`nvdaControllerClient64.dll` / `nvdaControllerClient32.dll` let Thrive Messenger send announcements
(typing, incoming messages, errors) straight to a running NVDA instead of a separate SAPI voice.
They are NV Access's controller client (LGPL 2.1), the same files the VoiceLink Windows build ships.
`scripts/build_windows.ps1` copies them next to `thrive_messenger.exe`. If NVDA isn't running,
the client falls back to its previous speech path.
