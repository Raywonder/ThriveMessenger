# Thrive Messenger Recovery

Last verified: 2026-08-20

## Account-management deployment

- Previous Git revision: recorded in `git-head.before.txt` in the backup directory.
- Backup directory: `/mnt/backups/ThriveMessenger/2026-08-20-account-management-ffc8a4d`
- Files: a consistent SQLite backup, the previous `srv/server.py`, Git revision receipt, and SHA-256 checksums.

## Rollback outline

1. Stop `thrive-messenger.service`.
2. Verify the exact backup path and its `SHA256SUMS`.
3. Restore the recorded previous Git revision and the SQLite backup only if rollback is required.
4. Start `thrive-messenger.service`.
5. Confirm the service is active and port 2005 is listening.

Do not restore over a running database. Preserve any post-deployment user data before a rollback decision.

