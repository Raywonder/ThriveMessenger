# Thrive voice calling: current state and plan (2026-09-27)

## What ships now (Alpha 15.11)
- **Voice messages**: record with Ctrl+R, play inline (Enter, Space, Left/Right). The server transcodes to MP3, stores the audio for history, delivers to every device, and delete-for-everyone removes the file.
- **Voicemail**: Ctrl+Shift+R. Kept on the server for offline users (`pending_voicemail`) and delivered when they sign in. File > Voicemail lists voicemail you've received, and the File Transfers tab can filter to it.
- **Clawdia**:
  - Her voice replies arrive as voice messages, transcoded from Opus/OGG to MP3. Delivered agent audio is still deleted afterwards.
  - Voice messages and voicemail sent to her are transcribed locally with faster-whisper, then passed to her real agent.
  - Her call auto-decline now offers voicemail.
- **Sounds**: all call and voicemail events have sounds in every theme. The FlexPBX theme is the default for call sounds.

## Why live calls stay off
The `voice_call` and `group_call` feature policies have been disabled since 2026-07-04. The audit found:
- **Server**:
  - Signaling only: `voice_call_request`/`accept`/`decline`/`end`, plus an opaque `voice_call_signal` relay.
  - No audio relay; `group_call_audio` is silently dropped.
  - No ring timeout and no call log.
- **Release client**:
  - Listens for `voice_call_incoming` and `voice_call_event ringing`, but the server sends `voice_call_request`/`voice_call_result`, so incoming calls never appear.
  - `GroupCallDialog` streams raw 16 kHz PCM as base64 `group_call_audio`, which the server drops. There's no jitter buffer, codec or echo cancellation.
- **Clawdia's listener**: auto-declines. There is no streaming speech-to-text or text-to-speech bridge.

Rule: don't enable either policy until live microphone audio is proven end to end.

## Plan and estimates
1. **Protocol alignment and missed calls** (1–2 days). Build this with step 2, not before it.
   - Fix the client handler names.
   - Add a 30 s ring timeout and a `call_log` table: missed, declined, offline and busy calls.
   - Deliver missed calls at login, show a "Missed call from X" row, and send an optional notification.
   - After a decline or timeout, offer "Leave voicemail" (reuse Ctrl+Shift+R).
2. **1:1 live audio over WebRTC** (about 3 weeks, including Windows and NVDA testing).
   - `aiortc` + Opus in the desktop client, using the existing `voice_call_signal` relay for SDP/ICE.
   - TURN/STUN through the coturn already on the host.
   - Accessible call window: Answer (Enter), Decline (Escape), Mute (Ctrl+M), Hang up (Ctrl+W), speak the call timer on demand (Ctrl+T), and announce every state change.
   - Ringtones from the FlexPBX theme. Output and input device choice. Speaker/Bluetooth routing where Windows allows it.
   - Proof gate: a real microphone-to-speaker call between two machines, verified by ear, before `voice_call` is re-enabled.
3. **Group calls** (2–3 weeks after step 2): an SFU (for example LiveKit or mediasoup) behind the Thrive auth token; join/leave sounds; a participant list with speaking indicators.
4. **Calls to Clawdia** (1–2 weeks after step 2): a bot media endpoint (aiortc) that
   - receives caller audio;
   - runs streaming faster-whisper;
   - sends the turn to her real OpenClaw agent;
   - speaks the reply with **Voice D only** (local Qwen3 TTS, clawdia-archive reference, 0.75–1 s lead-in, at least 1.5 s tail);
   - keeps no audio after the call beyond the transcript.
   Until then she declines and offers voicemail.
5. **iOS** (plan only, branch `codex/thrive-ios-foundation`): CallKit incoming/outgoing UI, the microphone permission prompt, `AVAudioSession` (voiceChat mode, Bluetooth routes), VoiceOver announcements for call state, and push (VoIP PushKit) for incoming calls. This follows steps 2–3 on the same WebRTC signaling.

Rough total for live 1:1 calls you can rely on: about 3–4 weeks. Group calls and Clawdia calls add another 3–5 weeks.
