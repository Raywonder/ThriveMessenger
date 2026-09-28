# Your own Thrive server: create, host, export, import

Status: design only (2026-09-28). Nothing here is built yet; Dom decides when to start.
Tracker: "Create your own Thrive server (hosted or self-hosted) with export/import".

## Goal

Like Discord's "create a server", but each community really is its own Thrive server:

- Anyone can create a server (a community) from the Thrive app on Windows, Mac or iPhone, either **hosted by us** or
  **self-hosted** on their own machine.
- The owner can **export everything** (users, rooms, history, files, settings) and **import** it into another Thrive
  server, ours or theirs, without losing history or membership.
- Every client, **including the iPhone app natively**, can join, switch between and stay connected to any number of
  Thrive servers. Our infrastructure brokers what an iPhone can't do alone: push notifications, discovery and
  background reconnect.

## Words

- **Server**: one running Thrive server (today's `srv/server.py` process with its own `thrive.db`).
- **Community**: what a user creates in the app. Each community is one server (hosted: an isolated instance we run; self-hosted: theirs).
- **Home server**: the server an account signed up on. People can be members of many servers.
- **Directory**: our service that lists public servers and resolves a server's address and keys.
- **Relay**: our service that carries push notifications and wakes iPhones (and optionally carries the connection for
  servers that can't be reached directly).

## Data model (per server)

What's already there stays the source of truth: `users`, `contacts`, `direct_message_history`, `group_rooms`,
`group_room_members`, `group_room_messages`, `group_room_bans`, `message_reactions`, `feature_policies`, voice files
in `voice_messages/`, room files, and `srv.conf` settings.

New tables:

- `server_identity`: server_id (a random 128-bit id, stable forever, also through export/import), display name,
  icon, owner account, created_at, the server's signing key pair (Ed25519; the public key is published to the directory), and
  `origin_server_id` when imported.
- `server_membership`: which accounts belong to this server and how they sign in (local password, passkey, or
  "federated" through their home server; see Auth).
- `export_jobs`: id, requested_by, scope, state, file path, checksum, expires_at.
- `server_invites`: invite links for joining this server (existing invite tokens are extended with a server_id).

## Creating a server from the app

1. The client adds a **"Create a server"** action (desktop: File menu and the Groups tab; iPhone: the server
   switcher).
2. The user picks a name and icon, public or private, and **Hosted by Thrive** or **I'll host it myself**.
3. **Hosted:** the client calls our provisioning API (`POST /api/servers`, authenticated with the user's Thrive
   account). We create an isolated instance: its own process or container, its own database and storage quota, and a
   subdomain like `name.thrive.tappedin.fm` with TLS. It returns the address and a one-time owner claim token.
4. **Self-hosted:** the app shows a one-line installer (Linux/Mac/Windows) or a Docker command that starts a server
   pre-linked to the owner. The server registers itself with the directory (if public) and the relay.
5. The client adds the new server to its server list and signs the owner in.

## Joining and switching (all clients)

- **Server list and switcher**: every client keeps a list of servers (name, icon, address, server_id, unread
  counts). Desktop: Server Manager plus a switcher (Ctrl+Shift+S) that reads "name, unread count". iPhone: a server
  switcher at the top level, one tap or VoiceOver rotor item per server.
- A client can stay **signed in to several servers at once** (desktop: one connection per server; iPhone: see
  below). Contacts, rooms and chats are grouped per server.
- **Per-server sign-in**: each server has its own session token, kept in the OS keychain under the server_id, so
  switching never needs retyping. Passkeys work per server (relying party = the server's domain).
- **Join by link**: `thrive://join/<server_id>?invite=...` or `https://thrive.tappedin.fm/join/...`; the directory
  resolves the address, the client verifies the server's public key and joins.

## iPhone (native, no web view)

iOS doesn't let apps keep sockets open in the background, so our side does the brokering:

- **Server switcher and multi-server state**: the app stores the server list and a keychain item per server. Only the
  server on screen keeps a live TLS connection; the others are refreshed on switch (history since the last seen id).
- **Push through our relay (APNs)**:
  - Each server that wants iPhone push registers with our relay (`POST /relay/servers`, signed with its server key).
    The app registers its APNs device token with the relay once, together with the list of servers and accounts it's
    signed in to (signed per server, so the relay can't sign in as anyone).
  - When a message, mention, call or voicemail arrives for an iPhone user, the server sends the relay a minimal
    notification: server_id, room or chat, sender display name, and a preview only if the user allows previews.
    The relay forwards it to APNs.
  - The **message content is not stored** by the relay. Previews can be end-to-end encrypted to the device, using a
    Notification Service Extension that decrypts them.
- **Background reconnect**: a notification (or background app refresh) wakes the app, which reconnects to that
  server, fetches what's new, marks delivery, and updates the badge. The same reconnect rules as desktop 15.17 apply:
  retry forever, backoff capped at 30 seconds, a fresh TLS connection every time, and a heartbeat.
- **Servers behind NAT (self-hosted)**: the server keeps an outbound connection to our relay, and the app connects
  through the relay (a TLS tunnel, so the relay only sees encrypted bytes). Servers with a public address are reached
  directly.
- **Calls** (when voice calling is on): CallKit plus VoIP push through the same relay.
- All of this is designed in from the first iOS release: the iPhone app's data layer is keyed by server_id from day
  one, even while it only shows one server.

## Export and import

**Format** (`.thrive-export`, a zip):

- `manifest.json`: `format: "thrive-export"`, `format_version: 1`, the exporting server version, server_id,
  created_at, counts, a list of files with SHA-256, and the export scope.
- `data/*.jsonl`: one JSON object per line per table (users without password hashes by default, contacts, direct
  messages, rooms, members, messages, bans, reactions, feature policies, server settings without secrets).
- `files/`: voice messages and room files, named by content hash.
- `signature`: the manifest signed with the server's Ed25519 key, so an import can prove where it came from.

**Versioning:** the importer reads any `format_version` up to its own and upgrades older ones step by step. It
refuses newer ones with a clear message ("This export is from a newer Thrive. Update the server first.").

**What moves:** server identity (name, icon, server_id), rooms, membership and roles, all history (direct messages
between members, rooms, reactions, read points), files and voice messages, invites that haven't been used yet, and
settings.

**What doesn't move:**
- Passwords and passkeys. Members sign in again: a one-time "claim your account" link is emailed or shown, or they
  sign in through their home server.
- Server secrets: TLS keys, SMTP and bot tokens, OpenClaw keys.
- Push registrations, which re-register automatically.
- Other servers' data.

**Privacy options at export:** the owner can leave out direct messages. Members' private DMs aren't exported unless
both people are members of the exporting server and the owner confirms. Members can be told an export happened.

**Import:** creates a new server (or fills an empty one) from the file. The server_id is kept, so the directory
entry, invite links and clients' saved servers move to the new address automatically. Members get a notice:
"<server> moved to a new host."

## Auth and ownership

- The owner is the account that created the server. Ownership can be handed over, as with rooms today, and admins are
  per server.
- **Federated sign-in** (phase 3): a member can sign in with their home-server account. The home server issues a
  short-lived signed assertion, which the other server verifies against the directory's published key. That means one
  account for many servers.
- **Hosted servers**: we can suspend a hosted server for abuse, but we can't read its DMs without the owner's
  consent. The operator policy is written down and shown to owners.

## Security

- TLS everywhere, and a pinned server public key saved on first join (trust on first use, then verified through the
  directory).
- Exports are encrypted with a passphrase by default (age or libsodium secretbox) and the download link expires.
- Rate limits on server creation per account. New hosted servers get quotas (storage, members, messages per
  minute), raised with a plan.
- The relay stores only what it needs: device tokens, server ids and account ids, never message bodies.

## Hosting and billing hooks

- **Free tier**: one small hosted server per account, with quotas (for example 50 members, 1 GB files).
- **Paid add-ons**, like OpenLink self-hosting: bigger quotas, a custom domain, longer history retention, and priority
  relay. Billing goes through the existing blind.software / WHMCS account, and the provisioning API checks the plan.
- **Self-hosted** is free, except for optional paid relay and push service for their iPhone users above a free
  allowance.

## Phases

1. **Multi-server clients**: server list and switcher, per-server keychain sign-in and unread counts on desktop, and
   the iPhone data layer keyed by server_id. There's no server creation yet.
2. **Relay and push for iPhone**: APNs relay, a Notification Service Extension, background reconnect, and tunnels
   for servers behind NAT.
3. **Create a hosted server** from the app: provisioning API, isolated instances, the directory, invites by link.
4. **Export and import** (format v1), plus the move notice to members.
5. **Self-hosted installer** and federated sign-in.
6. **Paid plans** and quotas through blind.software / WHMCS.

## Open questions for Dom

- Do hosted servers live on this server machine at first, or on a separate host? This server has had hardware resets
  under load.
- Is there a default free quota, and which plans cost extra?
- Should members be told when their server is exported?
