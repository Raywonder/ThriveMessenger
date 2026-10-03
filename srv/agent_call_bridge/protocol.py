from __future__ import annotations

import asyncio
import json
import ssl
from typing import Any

Json = dict[str, Any]


class ThriveConnection:
    """Authenticated JSON-lines connection and normal bot-session lease."""
    def __init__(self, host: str, port: int, username: str, password: str, *, tls: bool, insecure: bool) -> None:
        self.host, self.port, self.username, self.password, self.tls, self.insecure = host, port, username, password, tls, insecure
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        context: ssl.SSLContext | bool | None = None
        if self.tls:
            context = ssl._create_unverified_context() if self.insecure else ssl.create_default_context()
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port, ssl=context, server_hostname=self.host if context else None)
        await self.send({"action": "login", "user": self.username, "pass": self.password})
        if (await self.receive()).get("status") != "ok":
            raise ConnectionError("Thrive login refused")

    async def register(self, session_id: str) -> None:
        await self.send({"action": "register_bot_session", "session_id": session_id, "auth_type": "claude", "runtime": "thrive-agent-call-bridge", "host_label": "server.devine-creations.com", "platform": "linux", "capabilities": ["chat", "voice-call", "webrtc", "opus"], "transports": ["thrive", "webrtc"], "accepts_files": False, "supports_delegation": False, "background": True})

    async def send(self, payload: Json) -> None:
        if not self.writer: raise ConnectionError("not connected")
        async with self._lock:
            self.writer.write((json.dumps(payload, separators=(",", ":")) + "\n").encode())
            await self.writer.drain()

    async def receive(self) -> Json:
        if not self.reader: raise ConnectionError("not connected")
        line = await self.reader.readline()
        if not line: raise ConnectionError("Thrive connection closed")
        event = json.loads(line)
        if not isinstance(event, dict): raise ValueError("invalid Thrive event")
        return event

    async def close(self) -> None:
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        self.reader = self.writer = None
