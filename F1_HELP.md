# Thrive Messenger Help (TappedIn Build)

## Quick Start
1. Open Thrive Messenger.
2. Press `F1` any time to open this help file.
3. In Login, pick a server from the **Server** dropdown.
4. Sign in with your username/password.

## Server Manager (No manual .conf edits required)
- In the Login window, use **Manage Servers...**
- Add/update/remove server entries.
- Pick any saved server before login.
- Last selected server is remembered for next launch.

## TappedIn Default Server
- Host: `im.tappedin.fm`
- Port: `2005`
- TLS: enabled

## Welcome Messages
- Pre-login welcome can be shown in Login.
- Click **View Full Welcome** in Login.
- Optional post-login message can appear after successful sign-in.
- Admin config location: `srv/srv.conf` under `[welcome]`.

## Chat Windows and Tabs
- Opening a chat never hides the contact list. Chats open in their own window with its own taskbar and Alt+Tab entry.
- By default every conversation is a tab in one **Chats** window. Settings, General tab, Chat Behavior group:
  - **Open chats in tabs in one chat window** (on by default). Turn it off for one window per chat.
  - **Keep the contact list open when a chat opens** (on by default). Turn it off for the older behaviour, where chat windows belong to the contact list window.
- A new message never moves your focus or switches tabs. Its tab shows the unread count, for example "Clawdia (2 unread)", and you hear the usual sound or announcement.

## Inside a Conversation
Each conversation has three tabs:
- **Messages**: the live chat.
- **Chat Archive** (formerly "Saved Messages"): the messages you chose to save, grouped by year, month and day. Choose newest or oldest first. Press Enter on a day to read it in a read-only text box. Escape goes back to the list of days.
  - To save a message, press Control+S on it, or use **Save to Chat Archive** in its context menu. If chat history saving is on for a contact, whole days are saved automatically.
- **File Transfers**: every file and voice message you sent to or received from this person, with name, size, date, direction and status.
  - **Open** or **Show in Folder** works when the file is still on this device.
  - If it isn't, **Get Again** asks the other person's app for it. If they still have it, it comes back to you automatically. If not, it is marked **No longer available**.
  - The Show list filters to Voice messages or Voicemail.

## Chat Links
- Links in chat messages are clickable.
- Activate a message row (Enter or double-click) to open its link. If the message has no link, Enter opens the full message in a read-only text box you can read line by line; Escape closes it.
- The context menu (Applications key or Shift+F10) on a message row also has "View Full Message".
- If multiple links are present, the first one opens.

## Messages: Copy, Edit and Delete
- **Copy Message** (Control+C on a message) copies it to the clipboard and says "Copied".
- **Edit Message** appears only on your own recent messages. Admins can edit any message. Enter saves the edit and Escape cancels. Both people see it marked "(edited)".
- **Delete Message** (the Delete key) asks you to confirm, then deletes the message for both people if you sent it or you are an admin. Otherwise it only removes it from your screen, and the app tells you so.
- Settings has **Delete messages for everyone** (on by default) and **Also delete attached files when deleting a message**. The second moves the files you received with that message, and cached voice messages, to the Recycle Bin.

## Emoji
- Emoji display in messages, and screen readers read them by name.
- **Insert Emoji** (Control+E in a chat, or the Chat menu) opens a searchable list. Type part of a name, such as "heart" or "thumbs", arrow to the one you want, and press Enter. It goes in at the cursor.

## Voice Messages and Voicemail
- A voice message appears in the chat as "Voice message (0:12)". Voicemail appears as "Voicemail (0:12)".
- On a voice message:
  - **Enter** plays it, and Enter again stops it.
  - **Space** pauses and resumes.
  - **Left Arrow** and **Right Arrow** go back or forward 5 seconds.
  - Nothing opens and your focus doesn't move.
- **Record a voice message**: press Control+R, speak, then press Control+R again. Then choose **Send**, **Play Back** or **Discard**. Recordings can be up to 3 minutes.
- **Leave a voicemail**: press Control+Shift+R. Voicemail is kept on the server for people who are offline and delivered when they sign in.
- **File, Voicemail...** in the contact list window lists all voicemail you've received.
- Voice replies from Clawdia arrive as voice messages. Voice messages and voicemail you send her are transcribed so she can answer.
- Agents that sign in on their own, like Adam, aren't in the chat window live the way Clawdia is, but voice messages and room voice messages you send them are transcribed for them the same way, so they can read and reply even though they can't play audio themselves.
- Voice calling is still switched off on this server while live call audio is being built.

## The VoiceLink Contact (VoiceLink server chat)
- **VoiceLink** in your contacts answers short commands about our VoiceLink servers. Message it **help** to start.
- Everyone can ask for **status**, **servers**, **rooms**, **who** (or **who** and a room) and **room** and a name.
- Servers are known by name: Main, Community, Dev and Devine Creations. Send **use community** to switch, or put the name first to ask once, for example **community rooms** or **dev status**.
- Staff of a VoiceLink server can manage it from here after linking once: sign in to VoiceLink on that server, message Admin chat there with **link code**, then send the VoiceLink contact **link** with the server name and the code, for example **link Community ABCD-1234**. You then get exactly your role on that server.
- Staff commands include **invite** a room (optionally **to** a person), **announce**, **agents**, **modules**, **users** (find, kick, ban, unban, role), **logs**, **deploy status**, **restart** and **broadcast**. Changes ask you to reply **confirm** within 2 minutes; anything else cancels.
- Staff can also ask in their own words, such as "is anyone in the music rooms on community?". The answer only uses these same commands and your permissions.
- **updates** (our server admins) lists the published VoiceLink app versions and any update problems. **unlink** removes your link.

## Keyboard Shortcuts
- `F1`: Open Help
- `Escape`: Close dialogs/chat
- `Enter`: Open selected contact chat / send in focused context
- `Shift+Enter`: New line in chat message box
- `Alt` shortcuts in Contacts screen:
  - `Alt+B` Block/Unblock
  - `Alt+A` Add Contact
  - `Alt+S` Start Chat
  - `Alt+F` Send File
  - `Alt+I` Server Info
  - `Alt+U` Set Status
  - `Alt+Y` User Directory
  - `Alt+V` Server Commands (admin)
  - `Alt+T` Settings
  - `Alt+P` Check Updates
  - `Alt+O` Logout
  - `Alt+X` Exit
- In a chat window:
  - `Ctrl+Tab` / `Ctrl+Shift+Tab`: next or previous conversation tab
  - `Ctrl+1` to `Ctrl+8`: go to that conversation; `Ctrl+9`: the last one
  - `Ctrl+W` or `Ctrl+F4`: close the current conversation
  - `Ctrl+0`: go to the contact list
  - `Ctrl+Page Down` / `Ctrl+Page Up`: next or previous inner tab (Messages, Chat Archive, File Transfers)
  - `Ctrl+E`: insert emoji
  - `Ctrl+R`: record a voice message (press again to stop)
  - `Ctrl+Shift+R`: leave a voicemail
  - On a message: `Ctrl+C` copy, `Ctrl+S` save to Chat Archive, `Delete` delete, `Applications` or `Shift+F10` for all actions
  - On a voice message: `Enter` play or stop, `Space` pause or resume, `Left`/`Right` skip 5 seconds

## Notes
- You can sign in to the same Thrive account on more than one device or approved agent session at once. New direct messages sync to every live session. For agent accounts, the worker that will handle a message claims it first; the other sessions see that claim and do not send a duplicate reply. Read receipts stay shared across your devices.
- Server-side account permissions are enforced by each server.
- This build includes TappedIn server defaults and multi-server profile selection.
