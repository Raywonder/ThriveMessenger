# Thrive server directory

`https://im.tappedin.fm/thrive/directory.json` is a signed, public discovery list. It is not an authority over a server: the client still makes a normal protocol connection, detects live capabilities, and warns before any unencrypted connection.

## Envelope

The response is UTF-8 JSON:

```json
{
  "format": 1,
  "generated_at": "2026-10-01T00:00:00Z",
  "key_id": "2026-10-primary",
  "payload": "{...canonical JSON string...}",
  "signature": "base64 Ed25519 signature of the exact UTF-8 payload"
}
```

The payload contains `servers`, whose entries have `id`, `name`, `description`, `host`, `port`, `allows_sign_up`, and `compatibility`. `compatibility` is advisory; the live capability request wins.

## Listing policy

- A server owner can opt in or out by submitting a signed server identity request to the directory operator.
- List only public servers that state that they accept users. Keep the verification URL/date and operator confirmation in the private directory-operating record; do not publish private contact details.
- The initial classic entry is `msg.thecubed.cc:2005`, found in the upstream G4p-Studios/ThriveMessenger README as its default client server. It is marked `classic`; no extension support is assumed.
- Do not add a third-party server merely because it answers a port scan, and do not contact or post to an upstream service without the owner's approval.

## Publishing

The signing key is an off-line deployment secret, never committed to this repository. Generate the envelope during the release deployment, publish it atomically, and retain the last valid envelope for rollback. Rotate by shipping the next public key in clients before using it as the only signing key.
