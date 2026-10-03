# Thrive agent call bridge

Disabled-by-default WebRTC endpoint for Thrive bot accounts. It uses existing `voice_call_*` signalling and accepts only `tappedinfm` until configured otherwise. Media is WebRTC audio/Opus. No audio is recorded: frames must remain transient for VAD and streaming ASR. The hard limit is ten minutes and idle calls end after 90 seconds.

`supertonic-3-stream` advertises streaming support on audio.cpp; System Monitor uses M3. If the TTS endpoint cannot provide playable chunks, synthesize one sentence at a time and pipeline them. The `SystemMonitorRelay` UDS contract is the integration point so the existing relay keeps the real chat history and trust policy.

Do not enable this service or Thrive's voice-call feature until a client produces matching WebRTC offer/answer/ICE messages and the full test matrix has passed.
