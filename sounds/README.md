# Thrive Messenger sound themes

Each folder here is a sound theme (sound pack). A theme plays `<event>.wav` for each event below. **If a theme is missing a file, the app falls back to the `default` theme's file** for that event.

All files added in this round are PCM 16-bit WAV, 44100 Hz; mono unless the source had real stereo (FlexPBX system sounds and ringtones, and the galaxia originals, which use stereo reverb). Peaks were normalised per theme to sit with the existing files: default about -6 dBFS, galaxia -3 dBFS, skype -9 dBFS, flexpbx -3 dBFS. The `typing` and `copied` blips are under 0.3 s and much quieter (about -17 to -22 dBFS). Ringtones loop cleanly and are at most 6.63 s long.

Pattern used across themes so events are easy to tell apart by ear: rising = start/connected/new, falling = stop/ended/lost, double beep = busy, hi-lo twice = missed call, three notes = voicemail (falling = you left one, rising = you got one), a swoop = voice message (up = sent, down = received).

Regenerate prompts for better versions are in `WISHLIST.md`. Check everything with `python3 verify_sounds.py`.

## Events

| Event | Meaning |
|---|---|
| `call_connected` | a call was answered |
| `call_ended` | a call ended |
| `contact_offline` | a contact went offline |
| `contact_online` | a contact came online |
| `file_error` | a file transfer failed |
| `file_receive` | a file arrived |
| `file_send` | a file was sent |
| `group_call_join` | someone joined a group call |
| `group_call_leave` | someone left a group call |
| `incoming_call` | ringing, someone is calling you (loops) |
| `login` | you signed in |
| `logout` | you signed out |
| `outgoing_call` | ringback while your call rings out (loops) |
| `receive` | message received |
| `send` | message sent |
| `call_busy` | call busy or declined |
| `call_missed` | you missed a call |
| `voicemail_left` | you finished leaving a voicemail |
| `voicemail_new` | you received a voicemail |
| `voice_message_send` | voice message sent |
| `voice_message_receive` | voice message received |
| `recording_start` | recording started |
| `recording_stop` | recording stopped |
| `typing` | contact is typing (very short, subtle) |
| `copied` | copied to clipboard (tiny tick) |
| `message_deleted` | a message was deleted |
| `message_edited` | a message was edited |
| `connection_lost` | connection to the server lost |
| `reconnected` | connection restored |

## Coverage

T = came with the theme, F = copied from FlexPBX, O = original made for Thrive, - = missing (falls back to default).

| Event | default | galaxia | skype | flexpbx |
|---|---|---|---|---|
| `call_connected` | T | T | T | F |
| `call_ended` | T | T | T | F |
| `contact_offline` | T | T | T | O |
| `contact_online` | T | T | T | O |
| `file_error` | T | T | T | O |
| `file_receive` | T | T | T | F |
| `file_send` | T | T | T | O |
| `group_call_join` | T | T | T | O |
| `group_call_leave` | T | T | T | O |
| `incoming_call` | T | T | T | F |
| `login` | T | T | T | O |
| `logout` | T | T | T | O |
| `outgoing_call` | T | T | T | F |
| `receive` | T | T | T | F |
| `send` | T | T | T | O |
| `call_busy` | O | O | O | O |
| `call_missed` | O | O | O | O |
| `voicemail_left` | O | O | O | O |
| `voicemail_new` | O | O | O | O |
| `voice_message_send` | O | O | O | O |
| `voice_message_receive` | O | O | O | O |
| `recording_start` | O | O | O | O |
| `recording_stop` | O | O | O | O |
| `typing` | O | O | O | O |
| `copied` | O | O | O | O |
| `message_deleted` | O | O | O | O |
| `message_edited` | O | O | O | O |
| `connection_lost` | O | O | O | F |
| `reconnected` | O | O | O | F |
| `incoming_call_alt` | - | - | - | F |
| `ringtone_are_you_gonna_answer` | - | - | - | F |
| `ringtone_ring_ring` | - | - | - | F |
| `call_connect_prompt` | - | - | - | F |

The last four rows are extra FlexPBX files (not events the app plays by name yet), kept so they can be swapped in as `incoming_call.wav` or `call_connected.wav` if preferred. `call_connect_prompt` sounds like a spoken voice prompt.

## Theme: default

Neutral. Originals use clean sine plus triangle tones with a small room reverb, base note C5.

| File | Length | Source |
|---|---|---|
| `call_connected.wav` | 1.50 s | came with theme |
| `call_ended.wav` | 1.50 s | came with theme |
| `contact_offline.wav` | 1.40 s | came with theme |
| `contact_online.wav` | 1.14 s | came with theme |
| `file_error.wav` | 1.00 s | came with theme |
| `file_receive.wav` | 0.96 s | came with theme |
| `file_send.wav` | 0.96 s | came with theme |
| `group_call_join.wav` | 1.50 s | came with theme |
| `group_call_leave.wav` | 1.00 s | came with theme |
| `incoming_call.wav` | 6.00 s | came with theme |
| `login.wav` | 2.00 s | came with theme |
| `logout.wav` | 1.50 s | came with theme |
| `outgoing_call.wav` | 4.00 s | came with theme |
| `receive.wav` | 1.01 s | came with theme |
| `send.wav` | 0.34 s | came with theme |
| `call_busy.wav` | 0.59 s | original made for Thrive (sox/ffmpeg): low double beep; neutral sine/triangle tones, light room |
| `call_missed.wav` | 1.18 s | original made for Thrive (sox/ffmpeg): falling minor-third pair played twice (hi-lo, hi-lo); neutral sine/triangle tones, light room |
| `voicemail_left.wav` | 0.76 s | original made for Thrive (sox/ffmpeg): three-note falling major arpeggio; neutral sine/triangle tones, light room |
| `voicemail_new.wav` | 0.79 s | original made for Thrive (sox/ffmpeg): three-note rising major arpeggio; neutral sine/triangle tones, light room |
| `voice_message_send.wav` | 0.46 s | original made for Thrive (sox/ffmpeg): upward octave swoop ending on a ping; neutral sine/triangle tones, light room |
| `voice_message_receive.wav` | 0.58 s | original made for Thrive (sox/ffmpeg): ping then downward octave swoop; neutral sine/triangle tones, light room |
| `recording_start.wav` | 0.47 s | original made for Thrive (sox/ffmpeg): two beeps rising an octave; neutral sine/triangle tones, light room |
| `recording_stop.wav` | 0.46 s | original made for Thrive (sox/ffmpeg): two beeps falling an octave; neutral sine/triangle tones, light room |
| `typing.wav` | 0.24 s | original made for Thrive (sox/ffmpeg): two tiny quiet high ticks (<0.3 s); neutral sine/triangle tones, light room |
| `copied.wav` | 0.24 s | original made for Thrive (sox/ffmpeg): single tiny quiet tick (<0.3 s); neutral sine/triangle tones, light room |
| `message_deleted.wav` | 0.39 s | original made for Thrive (sox/ffmpeg): quick downward pitch sweep; neutral sine/triangle tones, light room |
| `message_edited.wav` | 0.46 s | original made for Thrive (sox/ffmpeg): tap-tap-tink (two taps, then a step up); neutral sine/triangle tones, light room |
| `connection_lost.wav` | 0.88 s | original made for Thrive (sox/ffmpeg): low falling tritone, two notes; neutral sine/triangle tones, light room |
| `reconnected.wav` | 0.65 s | original made for Thrive (sox/ffmpeg): fast four-note rising arpeggio; neutral sine/triangle tones, light room |

## Theme: galaxia

Spacey synth. Originals use detuned triangle synth notes with chorus, echo and wide stereo reverb, base note G4, slower.

| File | Length | Source |
|---|---|---|
| `call_connected.wav` | 1.50 s | came with theme |
| `call_ended.wav` | 1.50 s | came with theme |
| `contact_offline.wav` | 2.08 s | came with theme |
| `contact_online.wav` | 2.08 s | came with theme |
| `file_error.wav` | 0.53 s | came with theme |
| `file_receive.wav` | 2.08 s | came with theme |
| `file_send.wav` | 2.08 s | came with theme |
| `group_call_join.wav` | 1.50 s | came with theme |
| `group_call_leave.wav` | 1.00 s | came with theme |
| `incoming_call.wav` | 6.00 s | came with theme |
| `login.wav` | 4.06 s | came with theme |
| `logout.wav` | 1.11 s | came with theme |
| `outgoing_call.wav` | 4.00 s | came with theme |
| `receive.wav` | 2.08 s | came with theme |
| `send.wav` | 0.87 s | came with theme |
| `call_busy.wav` | 1.79 s | original made for Thrive (sox/ffmpeg): low double beep; detuned triangle synth, chorus, echo and wide stereo reverb |
| `call_missed.wav` | 2.59 s | original made for Thrive (sox/ffmpeg): falling minor-third pair played twice (hi-lo, hi-lo); detuned triangle synth, chorus, echo and wide stereo reverb |
| `voicemail_left.wav` | 2.05 s | original made for Thrive (sox/ffmpeg): three-note falling major arpeggio; detuned triangle synth, chorus, echo and wide stereo reverb |
| `voicemail_new.wav` | 2.06 s | original made for Thrive (sox/ffmpeg): three-note rising major arpeggio; detuned triangle synth, chorus, echo and wide stereo reverb |
| `voice_message_send.wav` | 1.63 s | original made for Thrive (sox/ffmpeg): upward octave swoop ending on a ping; detuned triangle synth, chorus, echo and wide stereo reverb |
| `voice_message_receive.wav` | 1.78 s | original made for Thrive (sox/ffmpeg): ping then downward octave swoop; detuned triangle synth, chorus, echo and wide stereo reverb |
| `recording_start.wav` | 1.61 s | original made for Thrive (sox/ffmpeg): two beeps rising an octave; detuned triangle synth, chorus, echo and wide stereo reverb |
| `recording_stop.wav` | 1.61 s | original made for Thrive (sox/ffmpeg): two beeps falling an octave; detuned triangle synth, chorus, echo and wide stereo reverb |
| `typing.wav` | 0.24 s | original made for Thrive (sox/ffmpeg): two tiny quiet high ticks (<0.3 s); detuned triangle synth, chorus, echo and wide stereo reverb |
| `copied.wav` | 0.24 s | original made for Thrive (sox/ffmpeg): single tiny quiet tick (<0.3 s); detuned triangle synth, chorus, echo and wide stereo reverb |
| `message_deleted.wav` | 1.54 s | original made for Thrive (sox/ffmpeg): quick downward pitch sweep; detuned triangle synth, chorus, echo and wide stereo reverb |
| `message_edited.wav` | 1.58 s | original made for Thrive (sox/ffmpeg): tap-tap-tink (two taps, then a step up); detuned triangle synth, chorus, echo and wide stereo reverb |
| `connection_lost.wav` | 2.23 s | original made for Thrive (sox/ffmpeg): low falling tritone, two notes; detuned triangle synth, chorus, echo and wide stereo reverb |
| `reconnected.wav` | 1.88 s | original made for Thrive (sox/ffmpeg): fast four-note rising arpeggio; detuned triangle synth, chorus, echo and wide stereo reverb |

## Theme: skype

Soft, rounded and bubbly. Originals use pure sine "bloops" that bend up into each note, low-passed, base note E5, quicker and quieter. They are original sounds in that spirit, not copies of Microsoft/Skype audio.

| File | Length | Source |
|---|---|---|
| `call_connected.wav` | 1.50 s | came with theme |
| `call_ended.wav` | 1.50 s | came with theme |
| `contact_offline.wav` | 1.00 s | came with theme |
| `contact_online.wav` | 2.20 s | came with theme |
| `file_error.wav` | 2.70 s | came with theme |
| `file_receive.wav` | 2.01 s | came with theme |
| `file_send.wav` | 2.06 s | came with theme |
| `group_call_join.wav` | 1.50 s | came with theme |
| `group_call_leave.wav` | 1.00 s | came with theme |
| `incoming_call.wav` | 6.00 s | came with theme |
| `login.wav` | 2.26 s | came with theme |
| `logout.wav` | 3.00 s | came with theme |
| `outgoing_call.wav` | 4.00 s | came with theme |
| `receive.wav` | 0.84 s | came with theme |
| `send.wav` | 0.74 s | came with theme |
| `call_busy.wav` | 0.60 s | original made for Thrive (sox/ffmpeg): low double beep; soft rounded sine "bloops" with upward pitch bends, low-passed |
| `call_missed.wav` | 1.07 s | original made for Thrive (sox/ffmpeg): falling minor-third pair played twice (hi-lo, hi-lo); soft rounded sine "bloops" with upward pitch bends, low-passed |
| `voicemail_left.wav` | 0.74 s | original made for Thrive (sox/ffmpeg): three-note falling major arpeggio; soft rounded sine "bloops" with upward pitch bends, low-passed |
| `voicemail_new.wav` | 0.74 s | original made for Thrive (sox/ffmpeg): three-note rising major arpeggio; soft rounded sine "bloops" with upward pitch bends, low-passed |
| `voice_message_send.wav` | 0.46 s | original made for Thrive (sox/ffmpeg): upward octave swoop ending on a ping; soft rounded sine "bloops" with upward pitch bends, low-passed |
| `voice_message_receive.wav` | 0.56 s | original made for Thrive (sox/ffmpeg): ping then downward octave swoop; soft rounded sine "bloops" with upward pitch bends, low-passed |
| `recording_start.wav` | 0.46 s | original made for Thrive (sox/ffmpeg): two beeps rising an octave; soft rounded sine "bloops" with upward pitch bends, low-passed |
| `recording_stop.wav` | 0.44 s | original made for Thrive (sox/ffmpeg): two beeps falling an octave; soft rounded sine "bloops" with upward pitch bends, low-passed |
| `typing.wav` | 0.24 s | original made for Thrive (sox/ffmpeg): two tiny quiet high ticks (<0.3 s); soft rounded sine "bloops" with upward pitch bends, low-passed |
| `copied.wav` | 0.24 s | original made for Thrive (sox/ffmpeg): single tiny quiet tick (<0.3 s); soft rounded sine "bloops" with upward pitch bends, low-passed |
| `message_deleted.wav` | 0.38 s | original made for Thrive (sox/ffmpeg): quick downward pitch sweep; soft rounded sine "bloops" with upward pitch bends, low-passed |
| `message_edited.wav` | 0.44 s | original made for Thrive (sox/ffmpeg): tap-tap-tink (two taps, then a step up); soft rounded sine "bloops" with upward pitch bends, low-passed |
| `connection_lost.wav` | 0.83 s | original made for Thrive (sox/ffmpeg): low falling tritone, two notes; soft rounded sine "bloops" with upward pitch bends, low-passed |
| `reconnected.wav` | 0.61 s | original made for Thrive (sox/ffmpeg): fast four-note rising arpeggio; soft rounded sine "bloops" with upward pitch bends, low-passed |

## Theme: flexpbx

Telephony. Real FlexPBX system sounds and ringtones where they fit, and telephone-style originals (DTMF keypad pairs, call-progress tones, band-limited to 300-3400 Hz like a phone line) for the rest.

| File | Length | Source |
|---|---|---|
| `call_connected.wav` | 1.80 s | copied from FlexPBX: `/home/flexpbxuser/apps/flexpbx/media/sounds/system/connected.wav` (first 1.8 s, faded) |
| `call_ended.wav` | 2.50 s | copied from FlexPBX: `/home/flexpbxuser/apps/flexpbx/media/sounds/system/disconnect.wav` (first 2.5 s (rest was silence), faded) |
| `contact_offline.wav` | 0.26 s | original made for Thrive (sox/ffmpeg): two DTMF digits falling (3 then 1); telephony band-limited 300-3400 Hz |
| `contact_online.wav` | 0.26 s | original made for Thrive (sox/ffmpeg): two DTMF digits rising (1 then 3); telephony band-limited 300-3400 Hz |
| `file_error.wav` | 0.93 s | original made for Thrive (sox/ffmpeg): standard telephone special-information tone triad (913.8/1370.6/1776.7 Hz); telephony band-limited 300-3400 Hz |
| `file_receive.wav` | 2.60 s | copied from FlexPBX: `/home/flexpbxuser/apps/flexpbx/media/sounds/system/file transfer complete.wav` (first 2.6 s (rest was silence), faded) |
| `file_send.wav` | 0.46 s | original made for Thrive (sox/ffmpeg): quick DTMF dialling run 1-2-3-6-9; telephony band-limited 300-3400 Hz |
| `group_call_join.wav` | 0.34 s | original made for Thrive (sox/ffmpeg): conference-bridge style two-tone rising beep; telephony band-limited 300-3400 Hz |
| `group_call_leave.wav` | 0.34 s | original made for Thrive (sox/ffmpeg): conference-bridge style two-tone falling beep; telephony band-limited 300-3400 Hz |
| `incoming_call.wav` | 6.00 s | copied from FlexPBX: `/home/flexpbxuser/public_html/uploads/media/sounds/ringtones/ringtone-incoming-call.wav` (full 6 s = 3 ring cycles, loops cleanly) |
| `login.wav` | 0.77 s | original made for Thrive (sox/ffmpeg): short dial tone (350+440 Hz) then two rising DTMF digits; telephony band-limited 300-3400 Hz |
| `logout.wav` | 0.48 s | original made for Thrive (sox/ffmpeg): two falling DTMF digits then a short busy-tone blip (hang-up); telephony band-limited 300-3400 Hz |
| `outgoing_call.wav` | 3.40 s | copied from FlexPBX: `/home/flexpbxuser/public_html/uploads/media/sounds/ringtones/ringtone-ring-ring-flitch.wav` (2 bars from 2.70 s (3.4 s), loops cleanly) |
| `receive.wav` | 1.20 s | copied from FlexPBX: `/home/flexpbxuser/apps/flexpbx/media/sounds/system/message.wav` (first 1.2 s, faded) |
| `send.wav` | 0.08 s | original made for Thrive (sox/ffmpeg): single DTMF "#" blip; telephony band-limited 300-3400 Hz |
| `call_busy.wav` | 1.35 s | original made for Thrive (sox/ffmpeg): busy tone (480+620 Hz), double beep; telephony band-limited 300-3400 Hz |
| `call_missed.wav` | 1.18 s | original made for Thrive (sox/ffmpeg): call-waiting style 440 Hz beeps, hi-lo twice; telephony band-limited 300-3400 Hz |
| `voicemail_left.wav` | 0.64 s | original made for Thrive (sox/ffmpeg): three voicemail-style beeps falling (1400/1050/700 Hz); telephony band-limited 300-3400 Hz |
| `voicemail_new.wav` | 0.79 s | original made for Thrive (sox/ffmpeg): stutter dial tone (message-waiting indicator), three bursts; telephony band-limited 300-3400 Hz |
| `voice_message_send.wav` | 0.27 s | original made for Thrive (sox/ffmpeg): chirp up 600->1400 Hz then beep; telephony band-limited 300-3400 Hz |
| `voice_message_receive.wav` | 0.40 s | original made for Thrive (sox/ffmpeg): beep then chirp down 1400->600 Hz; telephony band-limited 300-3400 Hz |
| `recording_start.wav` | 0.39 s | original made for Thrive (sox/ffmpeg): record beep rising 700 -> 1000 Hz; telephony band-limited 300-3400 Hz |
| `recording_stop.wav` | 0.39 s | original made for Thrive (sox/ffmpeg): record beep falling 1000 -> 700 Hz; telephony band-limited 300-3400 Hz |
| `typing.wav` | 0.24 s | original made for Thrive (sox/ffmpeg): two tiny quiet keypad clicks (<0.3 s); telephony band-limited 300-3400 Hz |
| `copied.wav` | 0.24 s | original made for Thrive (sox/ffmpeg): single tiny quiet keypad tick (<0.3 s); telephony band-limited 300-3400 Hz |
| `message_deleted.wav` | 0.30 s | original made for Thrive (sox/ffmpeg): downward sweep 1200 -> 250 Hz; telephony band-limited 300-3400 Hz |
| `message_edited.wav` | 0.28 s | original made for Thrive (sox/ffmpeg): DTMF 5-5-6 tap-tap-tink; telephony band-limited 300-3400 Hz |
| `connection_lost.wav` | 1.00 s | copied from FlexPBX: `/home/flexpbxuser/apps/flexpbx/media/sounds/system/connection lost.wav` (first 1.0 s (rest was silence), mono) |
| `reconnected.wav` | 1.69 s | copied from FlexPBX: `/home/flexpbxuser/apps/flexpbx/media/sounds/system/reconnected.wav` (full) |
| `incoming_call_alt.wav` | 5.38 s | copied from FlexPBX: `/home/flexpbxuser/public_html/uploads/media/sounds/ringtones/ringtone-incoming-call-alt.wav` (trimmed to 3 ring cycles (5.38 s), loops cleanly) |
| `ringtone_are_you_gonna_answer.wav` | 6.63 s | copied from FlexPBX: `/home/flexpbxuser/public_html/uploads/media/sounds/ringtones/ringtone-are-you-gonna-answer.wav` (2 phrases from 0.40 s (6.63 s), faded) |
| `ringtone_ring_ring.wav` | 5.10 s | copied from FlexPBX: `/home/flexpbxuser/public_html/uploads/media/sounds/ringtones/ringtone-ring-ring-flitch.wav` (3 bars from 2.70 s (5.1 s), faded) |
| `call_connect_prompt.wav` | 3.68 s | copied from FlexPBX: `/home/flexpbxuser/apps/flexpbx/media/sounds/queue/call-connect.wav` (extra, not mapped to an event: sounds like a spoken prompt (8 kHz voice), kept so Dom can decide; resampled to 44.1 kHz mono) |


## message_read (added 2026-09-28)
Original for Thrive in every theme (sox): a soft, short cue when someone reads your newest message. default: two soft sine notes rising (0.2 s); galaxia: detuned synth ping with reverb (0.35 s); skype: rounded upward glide (0.16 s); flexpbx: two soft ticks (0.2 s).
