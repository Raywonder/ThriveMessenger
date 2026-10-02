#!/usr/bin/env python3
"""Sign a canonical Thrive directory payload with the offline Ed25519 deployment key."""
import argparse
import base64
import json
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("payload", type=Path, help="JSON object containing a servers array")
    parser.add_argument("output", type=Path, help="signed directory.json output")
    parser.add_argument("--key", type=Path, required=True, help="offline Ed25519 private PEM")
    parser.add_argument("--key-id", required=True)
    args = parser.parse_args()
    # Canonicalize once here; do not parse/re-serialize this string in a client before verification.
    body = json.dumps(json.loads(args.payload.read_text(encoding="utf-8")), separators=(",", ":"), sort_keys=True)
    private = serialization.load_pem_private_key(args.key.read_bytes(), password=None)
    signature = private.sign(body.encode("utf-8"))
    envelope = {"format": 1, "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                "key_id": args.key_id, "payload": body, "signature": base64.b64encode(signature).decode("ascii")}
    args.output.write_text(json.dumps(envelope, separators=(",", ":"), sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
