from __future__ import annotations
import pytest
from agent_call_bridge.config import BridgeConfig
from agent_call_bridge.thrive_agent_call_bridge import Bridge
def test_only_dom_is_allowed_by_default() -> None:
    bridge = Bridge(BridgeConfig(password="test")); assert bridge.allowed("tappedinfm"); assert bridge.allowed("TAPPEDINFM"); assert not bridge.allowed("adonis1111")
@pytest.mark.asyncio
async def test_disabled_bridge_never_connects() -> None:
    bridge = Bridge(BridgeConfig(password="test", enabled=False)); await bridge.run(); assert bridge.connection.writer is None
