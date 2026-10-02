# TestFlight "What to Test" notes

Keep the newest batch at the top. Paste the matching section into App Store Connect when
`asc_beta.py submit` uploads that build.

## Batch 20260930 (VoiceOver actions)

Voice messages now pause and carry on:

- Activate a voice message to play it, activate it again to pause, again to resume. It no longer
  jumps back to 0:00 on the second activation.
- The separate "Play voice message" action is gone from the Actions rotor and the context menu,
  because activating the message itself plays it.
- With VoiceOver on, a double-tap on a message now reaches the app at all. It used to be dropped,
  which is why the rotor action was the only way to play anything.

With a hardware keyboard, **Enter on a voice message plays, pauses and resumes it** -- no
double-tap needed. It runs through the same play/pause as double-tapping does, so the key and the
double-tap always agree about what is paused. Enter still sends your message while you are in the
typing box, and Enter on a text message does nothing.

The "Seen" reaction is gone. Thrive already tells the sender you have read a message a few
seconds after you reach it, so the manual eyes reaction was duplicate work.

Contacts in the Chats list now have actions. Swipe up or down on a contact for: Message, Voice
message, Call (only when the server offers calling), Add to group, Block or Unblock, Remove
contact, Copy username. Touch and hold gives the same list without VoiceOver.

New in the app: **Settings > Help and What's New**, with every chat, message and contact action
written out, the hardware-keyboard keys, and what changed in this version.

What to check:

1. A voice message plays on the first double-tap, pauses on the second, resumes on the third.
2. Playing a different voice message starts it from the beginning.
3. No "Play voice message" and no "Seen" anywhere in the Actions rotor or the context menu.
4. A 👀 reaction sent from Windows or Mac still reads as "eyes".
5. Each contact action speaks its result, and Remove contact asks first.
6. Message rows still read "sender, time, text, links, reactions, status"; contacts still read
   "name, online or offline, status, unread count".
7. With a hardware keyboard: Enter on a voice message plays it, Enter again pauses, Enter again
   resumes -- and it never plays and pauses on one press.
8. Enter in the typing box still sends the message, and Enter on a text message does nothing.
# Next TestFlight batch

- Choose a Thrive server from the in-app directory, or add a server manually when it is private or not listed.
- The directory refreshes quietly and keeps the last safe list when you are offline.
- Classic Thrive servers now have a clear compatibility note. Chats and contacts remain available while newer server-only features stay out of the way.
- Thrive warns plainly before signing in to a server that does not offer encryption.
