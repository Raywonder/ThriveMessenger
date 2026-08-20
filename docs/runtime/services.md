# Thrive Messenger Runtime Services

Last verified: 2026-08-20

## Messenger server

- Service unit: `thrive-messenger.service`
- State after account-management deployment: active and running
- Runtime user: `tappedin`
- Working directory: `/home/tappedin/apps/ThriveMessenger`
- Account deletion is authenticated and requires an exact username confirmation.
- Deletion removes local credentials, contacts, access-policy memberships, linked WordPress and Mastodon identity records, and available group-room records. External WordPress or Mastodon accounts are not deleted.

## Transport limitation

The configured certificate was expired when checked on 2026-08-20, so the current server falls back to its existing unencrypted transport mode. Certificate renewal and configuration are required before TLS can be claimed healthy.

