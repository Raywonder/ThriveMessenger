# Thrive Messenger client parity (2026-09-27, Alpha 15.11)

## What the clients are
- **Windows and macOS share one client**: `main.py` (wxPython).
  - Windows: `scripts/build_windows.ps1` + Inno Setup, built on the win11 VM.
  - macOS: `scripts/build_macos.sh` (PyInstaller .app, ad-hoc signed unless `THRIVE_CODESIGN_IDENTITY` is set), built on the Mac mini.
  - Platform differences are small, guarded blocks in the same file. There is no separate Swift macOS target.
- **iOS is a separate SwiftUI app** in `ios/`, on branches `codex/thrive-ios-foundation` and `codex/passkey-recovery-all-clients`. It is not part of this release and has no feed; it goes through TestFlight when approved.
- `native/windows/` holds the NVDA controller client DLLs, which are only used on Windows.

## Mac-only or branch-only features brought to this release
- [x] **Passkey registration/list/revoke hardening** (from `codex/passkey-recovery-all-clients`, 696d256). Requests are serialized, wait out reconnects, retry once, and are answered through the listener thread. The server returns a normal reply when SQLite is busy. Both desktop platforms get this from the shared client.
- [x] Passkey sign-in ("Login with Passkey") and Register Passkey For This Device were already in the shared client. The device secret is stored in the OS keychain.
- [ ] Windows Hello / WebAuthn passkeys: not implemented. Thrive "passkeys" are server-issued device secrets kept in the keychain, not FIDO credentials. Moving to WebAuthn would mean server changes (a relying-party ID and attestation) and is a separate project.
- [ ] iOS passkey/Keychain flow: it's in the iOS app on its branch; iOS isn't shipped with this release.

## Alpha 15.11 features, per platform
Legend: [x] done and tested, [~] implemented but not yet tested on real hardware with a screen reader.

- **Messages without a time use the receive time**: Windows [x], macOS [x] (same code).
- **Typing announcements** (debounced, and made even with no chat window open): Windows [x] through the NVDA controller. macOS [~] through VoiceOver announcements (AppKit `NSAccessibilityAnnouncementRequestedNotification`), falling back to `say` when VoiceOver is off.
- **Copy (Ctrl/Cmd+C), Edit (own messages, or any for admins), Delete for everyone (sender or admin)**: Windows [x], macOS [~]. On a Mac, Delete is Command+Delete.
- **Chat tabs and keep-the-contact-list-open, with settings**: Windows [x], macOS [~]. The Mac uses Control+Tab or Command+Shift+] and [, because Command+Tab belongs to macOS.
- **Inner tabs** (Messages, Chat Archive, File Transfers), **Get Again**: Windows [x], macOS [~]. On a Mac, Command+Option+Right and Left also switch the inner tabs.
- **Emoji display and the picker (Ctrl/Cmd+E)**: Windows [x], macOS [~].
- **Voice messages and voicemail (record, inline play)**: Windows [x] (MCI playback, sounddevice capture). macOS [~] (NSSound playback, sounddevice capture; NSMicrophoneUsageDescription is in Info.plist).
- **Clawdia's voice replies as voice messages; voice sent to bots is transcribed**: server side, both platforms [x].
- **Live voice calls**: off on every platform. See `docs/VOICE_CALLING_PLAN.md` on the live branch.
- **Sound themes** (default, galaxia, skype, flexpbx; 29 events; FlexPBX for calls): Windows [x], macOS [x] (same files, played with afplay).
- **Saved passwords and passkeys only in the OS keychain**, with the old base64 entries migrated: Windows [x] (Credential Manager). macOS [~] (Keychain through keyring; every call has a timeout so a slow keychain can't freeze startup).
- **Updater**: `win_tag`/`mac_tag` in the feed so each platform only sees its own release.
  - Windows [x]: 15.10 to 15.11 was verified through the installer.
  - macOS [~]: the Mac 15.11 feed entry is only published after its build is verified.

## Still open
- A real VoiceOver pass on the Mac build (Dom). Agents avoid GUI tests on the Mac mini while Dom is using it.
- Signed and notarized Mac builds: the build is ad-hoc signed unless a Developer ID identity is provided.
- The iOS app on the passkey and iOS branches.
