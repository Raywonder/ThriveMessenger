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
- **Chat Archive** (formerly "Saved Messages"): every day of this conversation, from the server's history plus anything saved on this device, grouped by year, month and day. Choose newest or oldest first. Press Enter on a day to read it in a read-only text box. Escape goes back to the list of days. Control+S on a message also saves it on this device.
- **File Transfers**: every file and voice message you sent to or received from this person, with name, size, date, direction and status.
  - **Open** or **Show in Folder** works when the file is still on this device.
  - If it isn't, **Get Again** asks the other person's app for it. If they still have it, it comes back to you automatically. If not, it is marked **No longer available**.
  - The Show list filters to Voice messages or Voicemail.

## Message History
- When you open a chat, on any device and even after restarting Thrive, the last 200 messages are already there, in order and without duplicates. That includes Clawdia's and other bots' replies.
- Messages you send from one device also show up on your other signed-in devices.
- To see older messages, press **Load earlier messages** above the message list, or press Up Arrow on the first message. For a whole day at a time, use the Chat Archive tab.
- Opening a chat puts you in the message box, with the newest message selected. The backlog isn't read out.
- If you'd rather start with an empty chat each time, turn on **Start chats fresh each time** in Settings, General tab, Chat Behavior. Nothing is deleted, and older messages stay in the Chat Archive.

## Read Receipts
- Your own messages end with their status: "sent", "delivered", or "read" with the time, for example "read 2:14 PM".
- When the person reads your newest message, you hear a short "Read by" announcement and a soft sound, once. Older messages don't announce.
- A message you receive counts as read when it stays selected for 2 seconds (you can set 1 to 10), or when it's the newest message in the chat you're looking at.
- Settings, General tab, Chat Behavior: **Send read receipts** (on by default) and **Mark a message as read after it's selected for this many seconds**. If you turn read receipts off, others don't see when you read their messages, and you don't see theirs.
- Clawdia and the other assistant bots mark your message as read when their agent picks it up.

## Links in Chats
- A message with links says how many at the end, for example "3 links".
- On a message, **Right Arrow** and **Left Arrow** move between its links and read "link 2 of 3" and the page title. Up and Down still move between messages.
- **Enter** or **Space** opens the link you moved to. With one link, Enter opens it. With several and none picked yet, Enter shows a list of them. A message with no links opens in a read-only text box instead; Escape closes it.
- **Full view:** links open inside Thrive by default, showing the whole page. Use Back, Forward, Reload, Open in default browser and Close. The screen reader reads the page as it would in a browser. **Escape** or **Control+W** (Command+W on a Mac) closes it and puts you back on the message the link came from. Alt+Left and Alt+Right go back and forward, and F5 reloads.
- **Mouse:** double-click a message to open its link. View Full Message shows each link as a real clickable link.
- **Links menu:** the message context menu (Applications key or Shift+F10) has a Links group below the usual options:
  - Open link, Open link in full view, Open link in default browser, Copy link and Copy link title. These act on the link you moved to or the only link; with several links you pick one from a submenu.
  - **Show list of links:** in this message, in this conversation (its whole history), in this chat window (all open tabs) or in all conversations. Each item reads "title, address, sender, time". Enter opens, Control+C copies the link, Control+Shift+C copies the title, Delete removes it, and the Applications key shows more actions. Escape closes the list.
  - **Remove links:** this link, all links in this message, a link in this conversation (you pick from a list), all links in this conversation, or all links in all conversations. Thrive asks first. Links in your own messages are removed for everyone, following the same rule as deleting: only the sender or an admin. Links other people sent are hidden on this device only, and Thrive tells you which.
- **Link titles:** the Thrive server looks up each page's title in the background, so links are read by name, and the site sees the server rather than you. It never visits private or local network addresses. When there's no title, the address is used.
- Settings, General tab, Chat Behavior: **Open links in** (Full view inside Thrive, Default browser, or Ask each time), **Fetch link titles** (on by default) and **Sort link lists** (Newest first or By sender).

## Getting Around Long Histories
- The message context menu (Applications key or Shift+F10) has, below the usual options:
  - **Links in this message**: one submenu per link, named by its title and address, to open it (in full view or your browser) or copy the link or title.
  - **Link lists and removal**: lists of links in this message, conversation, chat window or all conversations, and removing links.
  - **Go to** (also **Control+G** in a chat): Messages with links, Messages from a person, My messages, Unread messages, By date, and Search. Each opens a list where every item reads "sender, time, first words". Enter goes to that message. Thrive loads the rest of the history first when needed.
- **Alt+Left** goes back to where you were before a jump.
- **Alt+Down** and **Alt+Up** go to the next or previous message with a link.
- **Control+Home** and **Control+End** go to the first and last message.

## Reactions
- React to a message instead of replying: the message context menu has **React** (or press **Alt+R** on a message): thumbs up, thumbs down, heart, laugh, wow, sad, celebrate, check mark, seen, and **More...** for any emoji. Choosing one you already added takes it away.
- Reactions are read as part of the message, for example "thumbs up from Dom and you, heart from Clawdia". When someone reacts to your message you hear it once, briefly.
- Agents use reactions too: System Monitor adds "seen" when it starts on your request. A thumbs up from you tells an agent you've seen something, but it isn't approval of anything risky unless it answers a clear yes or no question.

## Staying Connected
- If the connection drops (the server restarts, the network changes, or your computer wakes from sleep), Thrive says "Reconnecting" once and keeps trying in the background, every 30 seconds at most, for as long as it takes, then says "Reconnected". Messages you type meanwhile are sent when it's back, and anything you missed is filled in.

## Start at Sign-in
- Settings, General tab: **Start Thrive automatically when I sign in** (on by default), **Start minimised to the tray** (the menu bar on a Mac), and **Say "Started" when Thrive starts at sign-in**. At sign-in Thrive never takes focus. If the network isn't ready yet, it waits quietly and connects when it can.
- On a Mac this uses Login Items; if you turn it off in System Settings, Thrive's setting shows that.

## Chat Rooms
- The **Groups** tab is the room directory: your rooms and public rooms, each read as "name, your role, members, unread, topic". Type in Search rooms and press Enter to filter. Enter on a room opens it; a public room you're not in is joined first.
- **Create room** asks for a name, topic, description, public or private, and when it expires (never by default). Rooms and their history are kept on the server, so they survive restarts.
- A room opens as a chat tab like a conversation, so links, Go to, voice messages (Control+R), files, edit and delete all work the same way.
- **Mentions:** type @ and a member's name (for example @Clawdia). Mentioned people hear "X mentioned you" even when the room isn't open. Settings has **Room messages when the room isn't open** (mentions only by default, every message, or nothing).
- **Read receipts in rooms:** your messages end with "sent", "read by 2 of 5" or "read by everyone". Thrive says "Read by everyone" once for your newest message.
- **Members tab** (Control+Page Down in a room): the topic, then each member with their role (owner, admin, moderator, member or guest), whether they're muted, and whether they've read the newest message. The Applications key on a member offers direct message, mention, change role, mute, remove from room and ban. There are also Invite, Change topic, Room settings, Banned people and Leave room buttons.
- **Roles:** the owner can do everything, including handing the room over. Admins manage members and roles. Moderators can mute, remove, ban, and edit or delete others' messages. Members can post, share files and voice, and invite. Guests can post text.
- **Agents in rooms:** Clawdia, Sapphire, Sophia, Elder, Adam and System Monitor can be in rooms. An agent answers in the same room when you @mention it (or in a room with just you and that agent). Agents don't answer each other, so they can't loop.

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
- Voice calling is still switched off on this server while live call audio is being built.

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


## On a Mac
Thrive for Mac has the same features. Where Windows uses Control, the Mac uses Command. A few keys differ so they don't clash with macOS or VoiceOver:
- Switch conversation tabs: `Control+Tab` / `Control+Shift+Tab`, or `Command+Shift+]` / `Command+Shift+[`.
- Go to a conversation: `Command+1` to `Command+9`. Close it: `Command+W`. Go to the contact list: `Command+0`.
- Switch the inner tabs (Messages, Chat Archive, File Transfers): `Control+Page Down` / `Control+Page Up`, or `Command+Option+Right` / `Command+Option+Left`.
- Insert emoji: `Command+E`. Record a voice message: `Command+R`. Leave a voicemail: `Command+Shift+R`.
- On a message: `Command+C` copies, `Command+S` saves to Chat Archive, and `Command+Delete` deletes.
- Announcements (typing, copied, voice messages) go to VoiceOver when it's on. If VoiceOver is off, the Mac speaks them with its built-in voice.
- The first time you record, macOS asks for permission to use the microphone.
- Saved passwords and passkeys are kept in the macOS Keychain. On Windows they're kept in Windows Credential Manager. Neither is ever stored in a settings file.

## Notes
- Server-side account permissions are enforced by each server.
- This build includes TappedIn server defaults and multi-server profile selection.
