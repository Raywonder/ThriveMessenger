# Sound wishlist: prompts to regenerate better versions

Each entry starts with the exact filename to save the result as. Generate with Suno (instrumental) or the ElevenLabs Sound Effects generator, export or convert to WAV (16-bit, 44.1 kHz), and drop the file into that theme folder with the same name, replacing the current one. Then run `python3 verify_sounds.py`.

Tips: ask for "no vocals, no speech" so it will not clash with a screen reader. Keep `typing` and `copied` under 0.3 s (trim if needed). Ringtones (loop: yes) should start and end on the beat so they repeat cleanly.

## default

### `sounds/default/call_busy.wav`

- Style: clean, neutral, modern UI sound
- Mood: calm, clear, unobtrusive
- Length: 1.2 s
- Loop: no
- Instruments: soft sine and marimba-like mallet tones, light room ambience

```
Clean, neutral, modern UI sound, call busy. Sound: a busy / call declined signal: exactly two identical short beeps. Mood: calm, clear, unobtrusive. Instruments: soft sine and marimba-like mallet tones, light room ambience. Length about 1.2 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/default/call_missed.wav`

- Style: clean, neutral, modern UI sound
- Mood: calm, clear, unobtrusive
- Length: 1.2 s
- Loop: no
- Instruments: soft sine and marimba-like mallet tones, light room ambience

```
Clean, neutral, modern UI sound, call missed. Sound: a missed-call notice: a high-low pair of notes played twice. Mood: calm, clear, unobtrusive. Instruments: soft sine and marimba-like mallet tones, light room ambience. Length about 1.2 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/default/connection_lost.wav`

- Style: clean, neutral, modern UI sound
- Mood: calm, clear, unobtrusive
- Length: 0.9 s
- Loop: no
- Instruments: soft sine and marimba-like mallet tones, light room ambience

```
Clean, neutral, modern UI sound, connection lost. Sound: "connection lost": two low falling notes, concerned but not alarming. Mood: calm, clear, unobtrusive. Instruments: soft sine and marimba-like mallet tones, light room ambience. Length about 0.9 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/default/copied.wav`

- Style: clean, neutral, modern UI sound
- Mood: calm, clear, unobtrusive
- Length: 0.1 s
- Loop: no
- Instruments: soft sine and marimba-like mallet tones, light room ambience

```
Clean, neutral, modern UI sound, copied. Sound: a single tiny, very quiet tick meaning copied to clipboard. Mood: calm, clear, unobtrusive. Instruments: soft sine and marimba-like mallet tones, light room ambience. Length about 0.1 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/default/message_deleted.wav`

- Style: clean, neutral, modern UI sound
- Mood: calm, clear, unobtrusive
- Length: 0.4 s
- Loop: no
- Instruments: soft sine and marimba-like mallet tones, light room ambience

```
Clean, neutral, modern UI sound, message deleted. Sound: "message deleted": a quick soft downward swish. Mood: calm, clear, unobtrusive. Instruments: soft sine and marimba-like mallet tones, light room ambience. Length about 0.4 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/default/message_edited.wav`

- Style: clean, neutral, modern UI sound
- Mood: calm, clear, unobtrusive
- Length: 0.4 s
- Loop: no
- Instruments: soft sine and marimba-like mallet tones, light room ambience

```
Clean, neutral, modern UI sound, message edited. Sound: "message edited": tap-tap and a small higher tink. Mood: calm, clear, unobtrusive. Instruments: soft sine and marimba-like mallet tones, light room ambience. Length about 0.4 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/default/reconnected.wav`

- Style: clean, neutral, modern UI sound
- Mood: calm, clear, unobtrusive
- Length: 0.7 s
- Loop: no
- Instruments: soft sine and marimba-like mallet tones, light room ambience

```
Clean, neutral, modern UI sound, reconnected. Sound: "reconnected": a fast bright four-note rising arpeggio. Mood: calm, clear, unobtrusive. Instruments: soft sine and marimba-like mallet tones, light room ambience. Length about 0.7 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/default/recording_start.wav`

- Style: clean, neutral, modern UI sound
- Mood: calm, clear, unobtrusive
- Length: 0.4 s
- Loop: no
- Instruments: soft sine and marimba-like mallet tones, light room ambience

```
Clean, neutral, modern UI sound, recording start. Sound: "recording started": two short beeps rising. Mood: calm, clear, unobtrusive. Instruments: soft sine and marimba-like mallet tones, light room ambience. Length about 0.4 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/default/recording_stop.wav`

- Style: clean, neutral, modern UI sound
- Mood: calm, clear, unobtrusive
- Length: 0.4 s
- Loop: no
- Instruments: soft sine and marimba-like mallet tones, light room ambience

```
Clean, neutral, modern UI sound, recording stop. Sound: "recording stopped": two short beeps falling. Mood: calm, clear, unobtrusive. Instruments: soft sine and marimba-like mallet tones, light room ambience. Length about 0.4 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/default/typing.wav`

- Style: clean, neutral, modern UI sound
- Mood: calm, clear, unobtrusive
- Length: 0.2 s
- Loop: no
- Instruments: soft sine and marimba-like mallet tones, light room ambience

```
Clean, neutral, modern UI sound, typing. Sound: a tiny, very quiet double tick meaning someone is typing; must not distract from a screen reader. Mood: calm, clear, unobtrusive. Instruments: soft sine and marimba-like mallet tones, light room ambience. Length about 0.2 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/default/voice_message_receive.wav`

- Style: clean, neutral, modern UI sound
- Mood: calm, clear, unobtrusive
- Length: 0.6 s
- Loop: no
- Instruments: soft sine and marimba-like mallet tones, light room ambience

```
Clean, neutral, modern UI sound, voice message receive. Sound: "voice message received": a small ping then a downward swoop. Mood: calm, clear, unobtrusive. Instruments: soft sine and marimba-like mallet tones, light room ambience. Length about 0.6 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/default/voice_message_send.wav`

- Style: clean, neutral, modern UI sound
- Mood: calm, clear, unobtrusive
- Length: 0.5 s
- Loop: no
- Instruments: soft sine and marimba-like mallet tones, light room ambience

```
Clean, neutral, modern UI sound, voice message send. Sound: "voice message sent": a quick upward swoop ending in a small ping. Mood: calm, clear, unobtrusive. Instruments: soft sine and marimba-like mallet tones, light room ambience. Length about 0.5 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/default/voicemail_left.wav`

- Style: clean, neutral, modern UI sound
- Mood: calm, clear, unobtrusive
- Length: 0.8 s
- Loop: no
- Instruments: soft sine and marimba-like mallet tones, light room ambience

```
Clean, neutral, modern UI sound, voicemail left. Sound: "voicemail sent": three notes falling, calm and final. Mood: calm, clear, unobtrusive. Instruments: soft sine and marimba-like mallet tones, light room ambience. Length about 0.8 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/default/voicemail_new.wav`

- Style: clean, neutral, modern UI sound
- Mood: calm, clear, unobtrusive
- Length: 0.8 s
- Loop: no
- Instruments: soft sine and marimba-like mallet tones, light room ambience

```
Clean, neutral, modern UI sound, voicemail new. Sound: "you have a new voicemail": three notes rising, inviting. Mood: calm, clear, unobtrusive. Instruments: soft sine and marimba-like mallet tones, light room ambience. Length about 0.8 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

## galaxia

### `sounds/galaxia/call_busy.wav`

- Style: spacey ambient synth UI sound
- Mood: dreamy, cosmic, airy
- Length: 2.2 s
- Loop: no
- Instruments: analog-style synth pad and pluck, gentle detune, shimmer, stereo delay and long reverb

```
Spacey ambient synth UI sound, call busy. Sound: a busy / call declined signal: exactly two identical short beeps. Mood: dreamy, cosmic, airy. Instruments: analog-style synth pad and pluck, gentle detune, shimmer, stereo delay and long reverb. Length about 2.2 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/galaxia/call_missed.wav`

- Style: spacey ambient synth UI sound
- Mood: dreamy, cosmic, airy
- Length: 2.2 s
- Loop: no
- Instruments: analog-style synth pad and pluck, gentle detune, shimmer, stereo delay and long reverb

```
Spacey ambient synth UI sound, call missed. Sound: a missed-call notice: a high-low pair of notes played twice. Mood: dreamy, cosmic, airy. Instruments: analog-style synth pad and pluck, gentle detune, shimmer, stereo delay and long reverb. Length about 2.2 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/galaxia/connection_lost.wav`

- Style: spacey ambient synth UI sound
- Mood: dreamy, cosmic, airy
- Length: 1.8 s
- Loop: no
- Instruments: analog-style synth pad and pluck, gentle detune, shimmer, stereo delay and long reverb

```
Spacey ambient synth UI sound, connection lost. Sound: "connection lost": two low falling notes, concerned but not alarming. Mood: dreamy, cosmic, airy. Instruments: analog-style synth pad and pluck, gentle detune, shimmer, stereo delay and long reverb. Length about 1.8 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/galaxia/copied.wav`

- Style: spacey ambient synth UI sound
- Mood: dreamy, cosmic, airy
- Length: 0.1 s
- Loop: no
- Instruments: analog-style synth pad and pluck, gentle detune, shimmer, stereo delay and long reverb

```
Spacey ambient synth UI sound, copied. Sound: a single tiny, very quiet tick meaning copied to clipboard. Mood: dreamy, cosmic, airy. Instruments: analog-style synth pad and pluck, gentle detune, shimmer, stereo delay and long reverb. Length about 0.1 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/galaxia/message_deleted.wav`

- Style: spacey ambient synth UI sound
- Mood: dreamy, cosmic, airy
- Length: 1.1 s
- Loop: no
- Instruments: analog-style synth pad and pluck, gentle detune, shimmer, stereo delay and long reverb

```
Spacey ambient synth UI sound, message deleted. Sound: "message deleted": a quick soft downward swish. Mood: dreamy, cosmic, airy. Instruments: analog-style synth pad and pluck, gentle detune, shimmer, stereo delay and long reverb. Length about 1.1 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/galaxia/message_edited.wav`

- Style: spacey ambient synth UI sound
- Mood: dreamy, cosmic, airy
- Length: 1.1 s
- Loop: no
- Instruments: analog-style synth pad and pluck, gentle detune, shimmer, stereo delay and long reverb

```
Spacey ambient synth UI sound, message edited. Sound: "message edited": tap-tap and a small higher tink. Mood: dreamy, cosmic, airy. Instruments: analog-style synth pad and pluck, gentle detune, shimmer, stereo delay and long reverb. Length about 1.1 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/galaxia/reconnected.wav`

- Style: spacey ambient synth UI sound
- Mood: dreamy, cosmic, airy
- Length: 1.5 s
- Loop: no
- Instruments: analog-style synth pad and pluck, gentle detune, shimmer, stereo delay and long reverb

```
Spacey ambient synth UI sound, reconnected. Sound: "reconnected": a fast bright four-note rising arpeggio. Mood: dreamy, cosmic, airy. Instruments: analog-style synth pad and pluck, gentle detune, shimmer, stereo delay and long reverb. Length about 1.5 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/galaxia/recording_start.wav`

- Style: spacey ambient synth UI sound
- Mood: dreamy, cosmic, airy
- Length: 1.1 s
- Loop: no
- Instruments: analog-style synth pad and pluck, gentle detune, shimmer, stereo delay and long reverb

```
Spacey ambient synth UI sound, recording start. Sound: "recording started": two short beeps rising. Mood: dreamy, cosmic, airy. Instruments: analog-style synth pad and pluck, gentle detune, shimmer, stereo delay and long reverb. Length about 1.1 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/galaxia/recording_stop.wav`

- Style: spacey ambient synth UI sound
- Mood: dreamy, cosmic, airy
- Length: 1.1 s
- Loop: no
- Instruments: analog-style synth pad and pluck, gentle detune, shimmer, stereo delay and long reverb

```
Spacey ambient synth UI sound, recording stop. Sound: "recording stopped": two short beeps falling. Mood: dreamy, cosmic, airy. Instruments: analog-style synth pad and pluck, gentle detune, shimmer, stereo delay and long reverb. Length about 1.1 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/galaxia/typing.wav`

- Style: spacey ambient synth UI sound
- Mood: dreamy, cosmic, airy
- Length: 0.2 s
- Loop: no
- Instruments: analog-style synth pad and pluck, gentle detune, shimmer, stereo delay and long reverb

```
Spacey ambient synth UI sound, typing. Sound: a tiny, very quiet double tick meaning someone is typing; must not distract from a screen reader. Mood: dreamy, cosmic, airy. Instruments: analog-style synth pad and pluck, gentle detune, shimmer, stereo delay and long reverb. Length about 0.2 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/galaxia/voice_message_receive.wav`

- Style: spacey ambient synth UI sound
- Mood: dreamy, cosmic, airy
- Length: 1.3 s
- Loop: no
- Instruments: analog-style synth pad and pluck, gentle detune, shimmer, stereo delay and long reverb

```
Spacey ambient synth UI sound, voice message receive. Sound: "voice message received": a small ping then a downward swoop. Mood: dreamy, cosmic, airy. Instruments: analog-style synth pad and pluck, gentle detune, shimmer, stereo delay and long reverb. Length about 1.3 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/galaxia/voice_message_send.wav`

- Style: spacey ambient synth UI sound
- Mood: dreamy, cosmic, airy
- Length: 1.2 s
- Loop: no
- Instruments: analog-style synth pad and pluck, gentle detune, shimmer, stereo delay and long reverb

```
Spacey ambient synth UI sound, voice message send. Sound: "voice message sent": a quick upward swoop ending in a small ping. Mood: dreamy, cosmic, airy. Instruments: analog-style synth pad and pluck, gentle detune, shimmer, stereo delay and long reverb. Length about 1.2 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/galaxia/voicemail_left.wav`

- Style: spacey ambient synth UI sound
- Mood: dreamy, cosmic, airy
- Length: 1.6 s
- Loop: no
- Instruments: analog-style synth pad and pluck, gentle detune, shimmer, stereo delay and long reverb

```
Spacey ambient synth UI sound, voicemail left. Sound: "voicemail sent": three notes falling, calm and final. Mood: dreamy, cosmic, airy. Instruments: analog-style synth pad and pluck, gentle detune, shimmer, stereo delay and long reverb. Length about 1.6 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/galaxia/voicemail_new.wav`

- Style: spacey ambient synth UI sound
- Mood: dreamy, cosmic, airy
- Length: 1.6 s
- Loop: no
- Instruments: analog-style synth pad and pluck, gentle detune, shimmer, stereo delay and long reverb

```
Spacey ambient synth UI sound, voicemail new. Sound: "you have a new voicemail": three notes rising, inviting. Mood: dreamy, cosmic, airy. Instruments: analog-style synth pad and pluck, gentle detune, shimmer, stereo delay and long reverb. Length about 1.6 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

## skype

### `sounds/skype/call_busy.wav`

- Style: soft, rounded, bubbly chat-app UI sound (original, not imitating any existing brand)
- Mood: friendly, playful, warm
- Length: 1.2 s
- Loop: no
- Instruments: round sine "bloop" and water-drop bubble tones, soft mallets, no harsh highs

```
Soft, rounded, bubbly chat-app UI sound (original, not imitating any existing brand), call busy. Sound: a busy / call declined signal: exactly two identical short beeps. Mood: friendly, playful, warm. Instruments: round sine "bloop" and water-drop bubble tones, soft mallets, no harsh highs. Length about 1.2 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/skype/call_missed.wav`

- Style: soft, rounded, bubbly chat-app UI sound (original, not imitating any existing brand)
- Mood: friendly, playful, warm
- Length: 1.2 s
- Loop: no
- Instruments: round sine "bloop" and water-drop bubble tones, soft mallets, no harsh highs

```
Soft, rounded, bubbly chat-app UI sound (original, not imitating any existing brand), call missed. Sound: a missed-call notice: a high-low pair of notes played twice. Mood: friendly, playful, warm. Instruments: round sine "bloop" and water-drop bubble tones, soft mallets, no harsh highs. Length about 1.2 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/skype/connection_lost.wav`

- Style: soft, rounded, bubbly chat-app UI sound (original, not imitating any existing brand)
- Mood: friendly, playful, warm
- Length: 0.9 s
- Loop: no
- Instruments: round sine "bloop" and water-drop bubble tones, soft mallets, no harsh highs

```
Soft, rounded, bubbly chat-app UI sound (original, not imitating any existing brand), connection lost. Sound: "connection lost": two low falling notes, concerned but not alarming. Mood: friendly, playful, warm. Instruments: round sine "bloop" and water-drop bubble tones, soft mallets, no harsh highs. Length about 0.9 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/skype/copied.wav`

- Style: soft, rounded, bubbly chat-app UI sound (original, not imitating any existing brand)
- Mood: friendly, playful, warm
- Length: 0.1 s
- Loop: no
- Instruments: round sine "bloop" and water-drop bubble tones, soft mallets, no harsh highs

```
Soft, rounded, bubbly chat-app UI sound (original, not imitating any existing brand), copied. Sound: a single tiny, very quiet tick meaning copied to clipboard. Mood: friendly, playful, warm. Instruments: round sine "bloop" and water-drop bubble tones, soft mallets, no harsh highs. Length about 0.1 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/skype/message_deleted.wav`

- Style: soft, rounded, bubbly chat-app UI sound (original, not imitating any existing brand)
- Mood: friendly, playful, warm
- Length: 0.4 s
- Loop: no
- Instruments: round sine "bloop" and water-drop bubble tones, soft mallets, no harsh highs

```
Soft, rounded, bubbly chat-app UI sound (original, not imitating any existing brand), message deleted. Sound: "message deleted": a quick soft downward swish. Mood: friendly, playful, warm. Instruments: round sine "bloop" and water-drop bubble tones, soft mallets, no harsh highs. Length about 0.4 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/skype/message_edited.wav`

- Style: soft, rounded, bubbly chat-app UI sound (original, not imitating any existing brand)
- Mood: friendly, playful, warm
- Length: 0.4 s
- Loop: no
- Instruments: round sine "bloop" and water-drop bubble tones, soft mallets, no harsh highs

```
Soft, rounded, bubbly chat-app UI sound (original, not imitating any existing brand), message edited. Sound: "message edited": tap-tap and a small higher tink. Mood: friendly, playful, warm. Instruments: round sine "bloop" and water-drop bubble tones, soft mallets, no harsh highs. Length about 0.4 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/skype/reconnected.wav`

- Style: soft, rounded, bubbly chat-app UI sound (original, not imitating any existing brand)
- Mood: friendly, playful, warm
- Length: 0.7 s
- Loop: no
- Instruments: round sine "bloop" and water-drop bubble tones, soft mallets, no harsh highs

```
Soft, rounded, bubbly chat-app UI sound (original, not imitating any existing brand), reconnected. Sound: "reconnected": a fast bright four-note rising arpeggio. Mood: friendly, playful, warm. Instruments: round sine "bloop" and water-drop bubble tones, soft mallets, no harsh highs. Length about 0.7 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/skype/recording_start.wav`

- Style: soft, rounded, bubbly chat-app UI sound (original, not imitating any existing brand)
- Mood: friendly, playful, warm
- Length: 0.4 s
- Loop: no
- Instruments: round sine "bloop" and water-drop bubble tones, soft mallets, no harsh highs

```
Soft, rounded, bubbly chat-app UI sound (original, not imitating any existing brand), recording start. Sound: "recording started": two short beeps rising. Mood: friendly, playful, warm. Instruments: round sine "bloop" and water-drop bubble tones, soft mallets, no harsh highs. Length about 0.4 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/skype/recording_stop.wav`

- Style: soft, rounded, bubbly chat-app UI sound (original, not imitating any existing brand)
- Mood: friendly, playful, warm
- Length: 0.4 s
- Loop: no
- Instruments: round sine "bloop" and water-drop bubble tones, soft mallets, no harsh highs

```
Soft, rounded, bubbly chat-app UI sound (original, not imitating any existing brand), recording stop. Sound: "recording stopped": two short beeps falling. Mood: friendly, playful, warm. Instruments: round sine "bloop" and water-drop bubble tones, soft mallets, no harsh highs. Length about 0.4 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/skype/typing.wav`

- Style: soft, rounded, bubbly chat-app UI sound (original, not imitating any existing brand)
- Mood: friendly, playful, warm
- Length: 0.2 s
- Loop: no
- Instruments: round sine "bloop" and water-drop bubble tones, soft mallets, no harsh highs

```
Soft, rounded, bubbly chat-app UI sound (original, not imitating any existing brand), typing. Sound: a tiny, very quiet double tick meaning someone is typing; must not distract from a screen reader. Mood: friendly, playful, warm. Instruments: round sine "bloop" and water-drop bubble tones, soft mallets, no harsh highs. Length about 0.2 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/skype/voice_message_receive.wav`

- Style: soft, rounded, bubbly chat-app UI sound (original, not imitating any existing brand)
- Mood: friendly, playful, warm
- Length: 0.6 s
- Loop: no
- Instruments: round sine "bloop" and water-drop bubble tones, soft mallets, no harsh highs

```
Soft, rounded, bubbly chat-app UI sound (original, not imitating any existing brand), voice message receive. Sound: "voice message received": a small ping then a downward swoop. Mood: friendly, playful, warm. Instruments: round sine "bloop" and water-drop bubble tones, soft mallets, no harsh highs. Length about 0.6 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/skype/voice_message_send.wav`

- Style: soft, rounded, bubbly chat-app UI sound (original, not imitating any existing brand)
- Mood: friendly, playful, warm
- Length: 0.5 s
- Loop: no
- Instruments: round sine "bloop" and water-drop bubble tones, soft mallets, no harsh highs

```
Soft, rounded, bubbly chat-app UI sound (original, not imitating any existing brand), voice message send. Sound: "voice message sent": a quick upward swoop ending in a small ping. Mood: friendly, playful, warm. Instruments: round sine "bloop" and water-drop bubble tones, soft mallets, no harsh highs. Length about 0.5 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/skype/voicemail_left.wav`

- Style: soft, rounded, bubbly chat-app UI sound (original, not imitating any existing brand)
- Mood: friendly, playful, warm
- Length: 0.8 s
- Loop: no
- Instruments: round sine "bloop" and water-drop bubble tones, soft mallets, no harsh highs

```
Soft, rounded, bubbly chat-app UI sound (original, not imitating any existing brand), voicemail left. Sound: "voicemail sent": three notes falling, calm and final. Mood: friendly, playful, warm. Instruments: round sine "bloop" and water-drop bubble tones, soft mallets, no harsh highs. Length about 0.8 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/skype/voicemail_new.wav`

- Style: soft, rounded, bubbly chat-app UI sound (original, not imitating any existing brand)
- Mood: friendly, playful, warm
- Length: 0.8 s
- Loop: no
- Instruments: round sine "bloop" and water-drop bubble tones, soft mallets, no harsh highs

```
Soft, rounded, bubbly chat-app UI sound (original, not imitating any existing brand), voicemail new. Sound: "you have a new voicemail": three notes rising, inviting. Mood: friendly, playful, warm. Instruments: round sine "bloop" and water-drop bubble tones, soft mallets, no harsh highs. Length about 0.8 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

## flexpbx

### `sounds/flexpbx/call_busy.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 1.2 s
- Loop: no
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, call busy. Sound: a busy / call declined signal: exactly two identical short beeps. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 1.2 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/call_connect_prompt.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 2 s
- Loop: no
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, call connect prompt. Sound: a short neutral cue that a call is being connected (sound only, no voice). Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 2 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/call_connected.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 1.5 s
- Loop: no
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, call connected. Sound: a short "call answered" confirmation, two or three rising tones. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 1.5 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/call_ended.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 2 s
- Loop: no
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, call ended. Sound: a short "call ended" cue, gently falling tones that settle. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 2 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/call_missed.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 1.2 s
- Loop: no
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, call missed. Sound: a missed-call notice: a high-low pair of notes played twice. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 1.2 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/connection_lost.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 0.9 s
- Loop: no
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, connection lost. Sound: "connection lost": two low falling notes, concerned but not alarming. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 0.9 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/contact_offline.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 0.5 s
- Loop: no
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, contact offline. Sound: a short two-note falling chime meaning a contact went offline. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 0.5 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/contact_online.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 0.5 s
- Loop: no
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, contact online. Sound: a short friendly two-note rising chime meaning a contact came online. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 0.5 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/copied.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 0.1 s
- Loop: no
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, copied. Sound: a single tiny, very quiet tick meaning copied to clipboard. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 0.1 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/file_error.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 1 s
- Loop: no
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, file error. Sound: a short, clear but not scary error cue, three stepped tones. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 1 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/file_receive.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 1.5 s
- Loop: no
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, file receive. Sound: a pleasant "delivery complete" chime meaning a file arrived. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 1.5 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/file_send.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 0.6 s
- Loop: no
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, file send. Sound: a quick upward whoosh-and-blip meaning a file was sent. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 0.6 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/group_call_join.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 0.5 s
- Loop: no
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, group call join. Sound: a two-note rising "someone joined" chime. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 0.5 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/group_call_leave.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 0.5 s
- Loop: no
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, group call leave. Sound: a two-note falling "someone left" chime. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 0.5 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/incoming_call.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 6 s
- Loop: yes
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, incoming call. Sound: an incoming-call ringtone phrase that loops seamlessly. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 6 seconds, seamless loop. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/incoming_call_alt.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 5 s
- Loop: yes
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, incoming call alt. Sound: an alternative incoming-call ringtone phrase that loops seamlessly. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 5 seconds, seamless loop. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/login.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 1 s
- Loop: no
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, login. Sound: a welcoming "signed in" jingle, rising. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 1 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/logout.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 0.7 s
- Loop: no
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, logout. Sound: a short "signed out" cue, falling. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 0.7 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/message_deleted.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 0.4 s
- Loop: no
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, message deleted. Sound: "message deleted": a quick soft downward swish. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 0.4 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/message_edited.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 0.4 s
- Loop: no
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, message edited. Sound: "message edited": tap-tap and a small higher tink. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 0.4 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/outgoing_call.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 4 s
- Loop: yes
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, outgoing call. Sound: a ringback tone heard while an outgoing call rings, repeating ring pattern that loops seamlessly. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 4 seconds, seamless loop. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/receive.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 1 s
- Loop: no
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, receive. Sound: a short "new message" notification chime. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 1 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/reconnected.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 0.7 s
- Loop: no
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, reconnected. Sound: "reconnected": a fast bright four-note rising arpeggio. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 0.7 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/recording_start.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 0.4 s
- Loop: no
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, recording start. Sound: "recording started": two short beeps rising. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 0.4 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/recording_stop.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 0.4 s
- Loop: no
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, recording stop. Sound: "recording stopped": two short beeps falling. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 0.4 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/ringtone_are_you_gonna_answer.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 6.5 s
- Loop: yes
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, ringtone are you gonna answer. Sound: a catchy, insistent ringtone with an "are you gonna answer?" feel, no lyrics needed, loops. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 6.5 seconds, seamless loop. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/ringtone_ring_ring.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 5 s
- Loop: yes
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, ringtone ring ring. Sound: a lively "ring ring" ringtone that loops. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 5 seconds, seamless loop. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/send.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 0.2 s
- Loop: no
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, send. Sound: a very short soft "message sent" blip. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 0.2 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/typing.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 0.2 s
- Loop: no
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, typing. Sound: a tiny, very quiet double tick meaning someone is typing; must not distract from a screen reader. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 0.2 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/voice_message_receive.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 0.6 s
- Loop: no
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, voice message receive. Sound: "voice message received": a small ping then a downward swoop. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 0.6 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/voice_message_send.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 0.5 s
- Loop: no
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, voice message send. Sound: "voice message sent": a quick upward swoop ending in a small ping. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 0.5 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/voicemail_left.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 0.8 s
- Loop: no
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, voicemail left. Sound: "voicemail sent": three notes falling, calm and final. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 0.8 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```

### `sounds/flexpbx/voicemail_new.wav`

- Style: telephone-system / PBX style sound
- Mood: professional, functional, clearly "phone"
- Length: 0.8 s
- Loop: no
- Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line

```
Telephone-system / PBX style sound, voicemail new. Sound: "you have a new voicemail": three notes rising, inviting. Mood: professional, functional, clearly "phone". Instruments: telephone keypad DTMF tones, call-progress beeps, classic phone ringer, slightly band-limited like a phone line. Length about 0.8 seconds, one-shot, not looping, short natural tail. No vocals, no speech, clean start, no background noise.
```


## message_read.wav (all themes)
Prompt: "A very soft, short UI confirmation chime, under half a second, gentle and unobtrusive, signalling a message was read; no loop; matches the theme (neutral / spacey synth / soft bubbly / telephone-style tick)."
