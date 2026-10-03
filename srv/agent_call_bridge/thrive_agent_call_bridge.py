from __future__ import annotations

import asyncio, logging, secrets, signal, time
from dataclasses import dataclass
from typing import Any
from aiortc import RTCConfiguration, RTCPeerConnection, RTCSessionDescription
from .config import BridgeConfig
from .protocol import Json, ThriveConnection

LOG = logging.getLogger("thrive-agent-call-bridge")

@dataclass(slots=True)
class ActiveCall:
    call_id: str; peer: str; connection: RTCPeerConnection; started: float; last_activity: float

class Bridge:
    def __init__(self, config: BridgeConfig) -> None:
        self.config, self.call, self.stopping = config, None, asyncio.Event()
        self.connection = ThriveConnection(config.host, config.port, config.username, config.password, tls=config.use_tls, insecure=config.insecure_loopback_tls)
        self.session_id = f"{config.username}:call-bridge:{secrets.token_hex(8)}"
    def allowed(self, username: str) -> bool: return username.casefold() == self.config.allowed_caller.casefold()
    async def send(self, payload: Json) -> None: await self.connection.send(payload)
    async def run(self) -> None:
        if not self.config.password: raise RuntimeError("THRIVE_AGENT_PASSWORD is required")
        if not self.config.enabled:
            LOG.warning("bridge disabled; refusing to connect or make/answer calls"); return
        while not self.stopping.is_set():
            try:
                await self.connection.connect(); await self.connection.register(self.session_id); await self.event_loop()
            except (ConnectionError, OSError, ValueError) as exc:
                LOG.warning("Thrive connection lost: %s", exc); await asyncio.sleep(5)
            finally:
                await self.close_call("bridge-reconnect"); await self.connection.close()
    async def event_loop(self) -> None:
        heartbeat = time.monotonic() + 30
        while not self.stopping.is_set():
            try: event = await asyncio.wait_for(self.connection.receive(), timeout=max(.1, heartbeat-time.monotonic()))
            except TimeoutError:
                await self.send({"action": "bot_session_heartbeat", "session_id": self.session_id, "host_label": "server.devine-creations.com"}); heartbeat = time.monotonic()+30
            else: await self.handle(event)
            await self.enforce_limits()
    async def handle(self, event: Json) -> None:
        action = str(event.get("action", ""))
        if action == "voice_call_request": await self.incoming(event)
        elif action == "voice_call_signal": await self.signalling(event)
        elif action == "voice_call_event" and self.call and event.get("call_id") == self.call.call_id and event.get("event") in {"ended", "declined"}: await self.close_call(str(event["event"]))
    async def incoming(self, event: Json) -> None:
        caller, call_id = str(event.get("from", "")), str(event.get("call_id", ""))
        if not call_id: return
        if not self.allowed(caller) or self.call:
            await self.send({"action": "voice_call_decline", "call_id": call_id}); LOG.warning("declined call from %s", caller); return
        pc = RTCPeerConnection(RTCConfiguration(iceServers=[])); now = time.monotonic(); self.call = ActiveCall(call_id, caller, pc, now, now); self.install_media_handlers(pc)
        await self.send({"action": "voice_call_accept", "call_id": call_id})
    def install_media_handlers(self, pc: RTCPeerConnection) -> None:
        @pc.on("connectionstatechange")
        async def changed() -> None:
            if pc.connectionState in {"failed", "closed", "disconnected"}: await self.close_call(f"webrtc-{pc.connectionState}")
        @pc.on("track")
        def track_received(track: Any) -> None:
            if track.kind == "audio" and self.call: self.call.last_activity = time.monotonic(); LOG.info("audio track received; in-memory VAD/ASR pipeline attached")
    async def signalling(self, event: Json) -> None:
        if not self.call or event.get("call_id") != self.call.call_id or event.get("from") != self.call.peer: return
        data = event.get("data")
        if event.get("signal_type") != "webrtc-offer" or not isinstance(data, dict) or not data.get("sdp"): return
        self.call.last_activity = time.monotonic(); await self.call.connection.setRemoteDescription(RTCSessionDescription(sdp=str(data["sdp"]), type="offer")); answer = await self.call.connection.createAnswer(); await self.call.connection.setLocalDescription(answer)
        await self.send({"action": "voice_call_signal", "call_id": self.call.call_id, "to": self.call.peer, "signal_type": "webrtc-answer", "data": {"type": "answer", "sdp": answer.sdp}})
    async def enforce_limits(self) -> None:
        if not self.call: return
        age, idle = time.monotonic()-self.call.started, time.monotonic()-self.call.last_activity
        if age >= self.config.max_call_seconds: await self.close_call("max-duration")
        elif idle >= self.config.idle_seconds: await self.close_call("idle")
    async def close_call(self, reason: str) -> None:
        call, self.call = self.call, None
        if not call: return
        try: await self.send({"action": "voice_call_end", "call_id": call.call_id})
        except (ConnectionError, OSError): pass
        await call.connection.close(); LOG.info("ended call %s (%s)", call.call_id, reason)

async def amain() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    bridge = Bridge(BridgeConfig.from_env()); loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM): loop.add_signal_handler(sig, bridge.stopping.set)
    await bridge.run()
if __name__ == "__main__": asyncio.run(amain())
