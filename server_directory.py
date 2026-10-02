"""Signed Thrive server-directory reader shared by the desktop client and release checks.

The server returns an envelope whose payload is a JSON *string*.  The exact UTF-8
payload bytes are signed with Ed25519, avoiding cross-language JSON canonicalisation
problems.  Treat a bad or unavailable response as a quiet refresh failure and retain
the cached, previously verified list.
"""

import base64
import json
from typing import Any, Dict, List, Set, Tuple
from urllib.request import Request, urlopen

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


DIRECTORY_URL = "https://im.tappedin.fm/thrive/directory.json"
# Raw Ed25519 public key for the 2026-10 primary directory signing key.  The
# corresponding private key is an offline deployment secret, never source code.
DIRECTORY_PUBLIC_KEYS = {
    "2026-10-primary": "QxOY9Q3BbqJ79uYPPuZvdzHmM38wWIv+r3BLoV5ttyQ=",
}


class DirectoryServer:
    def __init__(self, id, name, description, host, port, allows_sign_up, compatibility):
        self.id = id
        self.name = name
        self.description = description
        self.host = host
        self.port = port
        self.allows_sign_up = allows_sign_up
        self.compatibility = compatibility

    def as_client_entry(self) -> Dict[str, Any]:
        return {"name": self.name, "host": self.host, "port": self.port, "cafile": "", "primary": False,
                "description": self.description, "allows_sign_up": self.allows_sign_up,
                "compatibility": self.compatibility, "listed": True}


def parse_signed_directory(raw: bytes) -> List[DirectoryServer]:
    envelope = json.loads(raw.decode("utf-8"))
    if not isinstance(envelope, dict) or envelope.get("format") != 1:
        raise ValueError("Unsupported server-directory format.")
    payload = envelope.get("payload")
    key_id = envelope.get("key_id")
    signature = envelope.get("signature")
    if not isinstance(payload, str) or not isinstance(key_id, str) or not isinstance(signature, str):
        raise ValueError("Directory signature is missing.")
    encoded_key = DIRECTORY_PUBLIC_KEYS.get(key_id)
    if not encoded_key:
        raise ValueError("Directory signing key is not trusted by this Thrive version.")
    try:
        Ed25519PublicKey.from_public_bytes(base64.b64decode(encoded_key)).verify(
            base64.b64decode(signature, validate=True), payload.encode("utf-8")
        )
    except (InvalidSignature, ValueError, TypeError) as exc:
        raise ValueError("Directory signature did not verify.") from exc
    decoded = json.loads(payload)
    records = decoded.get("servers") if isinstance(decoded, dict) else None
    if not isinstance(records, list):
        raise ValueError("Directory has no server list.")
    servers = []  # type: List[DirectoryServer]
    seen = set()  # type: Set[Tuple[str, int]]
    for item in records:
        if not isinstance(item, dict):
            continue
        host = str(item.get("host", "")).strip().lower()
        name = str(item.get("name", "")).strip()
        try:
            port = int(item.get("port", 0))
        except (TypeError, ValueError):
            continue
        if not host or not name or not (1 <= port <= 65535) or (host, port) in seen:
            continue
        seen.add((host, port))
        servers.append(DirectoryServer(
            id=str(item.get("id") or f"{host}:{port}"), name=name,
            description=str(item.get("description", "")).strip(), host=host, port=port,
            allows_sign_up=bool(item.get("allows_sign_up", False)),
            compatibility=item.get("compatibility") if isinstance(item.get("compatibility"), dict) else {},
        ))
    if not servers:
        raise ValueError("Directory has no usable servers.")
    return servers


def fetch_signed_directory(url: str = DIRECTORY_URL, timeout: float = 8.0) -> List[DirectoryServer]:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "ThriveMessenger-directory/1"})
    with urlopen(request, timeout=timeout) as response:
        return parse_signed_directory(response.read())
