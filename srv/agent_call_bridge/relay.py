from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path


class RelayUnavailable(RuntimeError): pass


class SystemMonitorRelay:
    """UDS contract: the existing relay retains chat history and trust policy."""
    def __init__(self, socket_path: Path) -> None: self.socket_path = socket_path
    async def reply(self, caller: str, transcript: str) -> AsyncIterator[str]:
        if not self.socket_path.exists(): raise RelayUnavailable("System Monitor voice relay socket unavailable")
        reader, writer = await asyncio.open_unix_connection(str(self.socket_path))
        try:
            writer.write((json.dumps({"channel": "thrive_voice_call", "speaker": caller, "trust": "owner" if caller.lower() == "tappedinfm" else "unknown", "text": transcript, "stream": True, "voice_reply": True}) + "\n").encode())
            await writer.drain()
            while line := await reader.readline():
                event = json.loads(line)
                if event.get("type") == "text" and event.get("text"): yield str(event["text"])
                if event.get("type") == "done": return
                if event.get("type") == "error": raise RelayUnavailable(str(event.get("reason", "relay error")))
        finally:
            writer.close(); await writer.wait_closed()
