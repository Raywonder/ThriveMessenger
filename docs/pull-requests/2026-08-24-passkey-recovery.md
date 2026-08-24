# Passkey recovery across Windows, macOS, and iOS

Status: Ready for review; do not close until owner-facing device checks pass

Branch: `codex/passkey-recovery-all-clients`

Fork review link: https://git.tappedin.fm/tappedinfm/ThriveMessenger/pulls/new/codex/passkey-recovery-all-clients

Commit: `696d256` (`Repair passkey registration across clients`)

## What changed

- Desktop passkey requests are serialized and use the current reconnect-safe socket.
- A request interrupted while the desktop client is replacing its connection gets one safe retry and a human-readable recovery message.
- Passkey registration, listing, and revocation now handle temporary SQLite contention without silently killing the session.
- iOS adds Keychain-backed passkey storage, registration after password sign-in, and saved-passkey sign-in.

## Checks completed

- `python3 -m py_compile main.py srv/server.py`
- `git diff --check`
- Native iOS simulator build on the Mac mini: passed.

## Still required before closing

- Reproduce registration on the real Windows client and verify the 10053 path no longer appears.
- Run the shared desktop build on macOS and verify registration/list/revoke.
- Run the iOS flow on a device or simulator with Keychain state and verify registration followed by saved-passkey sign-in.
- Review the issue and this change through the local fork PR workflow.

The branch has been pushed to the Raywonder Gitea fork and is intentionally
left open for those device checks. GitHub issue/PR creation remains pending
because the available GitHub CLI session is not authenticated.
