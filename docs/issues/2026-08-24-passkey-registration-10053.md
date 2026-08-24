# Passkey registration can abort during a desktop reconnect

Status: In progress

## Report

On the Windows client, choosing “Register Passkey For This Device” can show:

> Could not register passkey: [WinError 10053] An established connection was aborted by the software in your host machine.

The same shared desktop client serves Windows and macOS, so both platforms need the recovery behavior covered. The iOS client also needs an equivalent registration and saved-passkey sign-in path.

## Acceptance checks

- A passkey request waits for an active session when reconnect is already underway.
- A transient socket replacement is retried once without creating duplicate credentials.
- Server-side SQLite failures return a normal passkey response instead of dropping the client connection.
- Windows and macOS desktop flows remain available through the shared client.
- iOS stores the device secret in Keychain and can sign in with it later.
- The issue stays open until native Windows, macOS, and iOS checks are recorded.
