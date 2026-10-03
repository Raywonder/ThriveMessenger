from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True, slots=True)
class BridgeConfig:
    """Runtime configuration. Secrets come only from EnvironmentFile."""
    host: str = "127.0.0.1"
    port: int = 2005
    use_tls: bool = True
    insecure_loopback_tls: bool = True
    username: str = "SystemMonitor"
    password: str = ""
    allowed_caller: str = "tappedinfm"
    enabled: bool = False
    max_call_seconds: int = 600
    idle_seconds: int = 90
    ring_seconds: int = 30
    audio_url: str = "http://127.0.0.1:18081"
    voice: str = "M3"
    state_dir: Path = Path("/var/lib/thrive-agent-call-bridge")
    relay_socket: Path = Path("/run/sysmon-thrive/voice-call.sock")

    @classmethod
    def from_env(cls) -> "BridgeConfig":
        def truth(name: str, default: bool) -> bool:
            return os.getenv(name, str(default)).lower() in {"1", "true", "yes"}
        return cls(host=os.getenv("THRIVE_HOST", "127.0.0.1"), port=int(os.getenv("THRIVE_PORT", "2005")),
                   use_tls=truth("THRIVE_TLS", True), insecure_loopback_tls=truth("THRIVE_INSECURE_LOOPBACK_TLS", True),
                   username=os.getenv("THRIVE_AGENT_USERNAME", "SystemMonitor"), password=os.getenv("THRIVE_AGENT_PASSWORD", ""),
                   allowed_caller=os.getenv("THRIVE_ALLOWED_CALLER", "tappedinfm").lower(),
                   enabled=truth("THRIVE_AGENT_CALLS_ENABLED", False), max_call_seconds=int(os.getenv("THRIVE_CALL_MAX_SECONDS", "600")),
                   idle_seconds=int(os.getenv("THRIVE_CALL_IDLE_SECONDS", "90")), audio_url=os.getenv("AGENT_AUDIO_URL", "http://127.0.0.1:18081").rstrip("/"),
                   voice=os.getenv("THRIVE_AGENT_VOICE", "M3"), state_dir=Path(os.getenv("THRIVE_AGENT_CALL_STATE", "/var/lib/thrive-agent-call-bridge")),
                   relay_socket=Path(os.getenv("SYSMON_VOICE_RELAY_SOCKET", "/run/sysmon-thrive/voice-call.sock")))
