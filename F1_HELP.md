# Thrive Messenger Help (TappedIn Build)

## Quick Start
1. Open Thrive Messenger.
2. Press `F1` any time to open this help file.
3. In Login, pick a server from the **Server** dropdown.
4. Sign in with your username/password.

## What's New in Alpha 15.24
- **Fixed a crash after updating:** Thrive sometimes failed to reopen itself right after installing an update (a DLL file conflict between the old and new copy). The updater now waits for the old copy to fully close before installing, and checks that Thrive actually reopened.
- **Fixed a crash using Escape to minimise** to the tray/menu bar.
- **Manage Signed-In Devices** (User menu) now shows your real signed-in devices and locations -- device name, platform, app version, when it was last seen, and expiry -- instead of an empty or broken list. A new **Sign Out All Other Devices** button signs out everywhere except the device you're on.
- **Password reset codes now expire** (15 minutes) and you'll get an email whenever your password changes, whether through a reset or Change Password in Settings, so you'll know if it wasn't you.
- **Quieter multi-device notifications:** only the device you're actively using plays a sound or shows a notification for a new message; your other signed-in devices stay quiet and just sync, instead of all sounding off at once.

## What's New in Alpha 15.23
- **Drafts:** whatever you're typing but haven't sent is saved automatically about a second after you stop typing, and restored the next time you open that chat -- even after Thrive updates and restarts. The contact list and room list show "Draft: ..." with the first few words, so you can tell at a glance. Turn this off in Settings, General tab, Chat Behavior: **Remember unsent messages as drafts** (on by default); turning it off also forgets any drafts already saved.
- **Updates never interrupt you mid-typing.** If you're actively typing, or have any unsent text anywhere, Thrive no longer pops the "Update Available" dialog or an app-modal progress bar over your message box; it waits quietly until you're idle, or downloads in the background without showing anything. Right before installing and restarting, every open draft is saved to disk first, no matter what. If you still have an unsent draft at that point, Thrive asks "Install now or later?" instead of restarting on you -- choosing Later keeps the download so it won't happen twice, and Thrive reopens the chat you were in once it restarts.
- **What's New:** after an update installs, Thrive shows a short summary of what changed since you last saw it. Escape or the Close button dismisses it, and focus returns to your chat and message box. See it again any time from **Help, What's New**. Turn it off in Settings, General tab, Chat Behavior: **Show What's New after an update**.

## What's New in Alpha 15.22
- **Links list fix:** opening a link, opening it in your browser, copying the link, copying its title or removing it from the list of links now closes the list and puts you back on the message it came from, the same as Escape or Ctrl+W already did. Before, the list stayed open after any of those actions.

## What's New in Alpha 15.21
- **A folder for each person:** received files now go into a folder named after the person who sent them, under Documents, ThriveMessenger, files. Room files go into files, Rooms, and the room's name. Files already in the files folder are moved into the right folder the first time 15.21 starts; any whose sender Thrive can't tell go into "Earlier files (sender unknown)". Open and Show in Folder keep working.
- **Open Their Files Folder:** a new button in each conversation's File Transfers tab.

## What's New in Alpha 15.20
- **iPhone Settings** are now a list of categories (General, Notifications, Privacy, Profile and Authentication), each with a short description. Each category opens its own screen with tabs. See "iPhone settings" below.
- **iPhone:** a new message in the chat you have open is now read out by VoiceOver (it used to arrive silently). You can change that, and what you hear for other chats, under Settings, Notifications.
- **Listening without typing:** if the chat is in front but you haven't touched the keyboard for a minute, Thrive now reads new messages in full instead of only saying "New message from …". They stay unread until you press a key in that chat.
- **Calmer updates:** if Thrive can't reach the update server (you're offline, or the network is slow), it no longer shows an error or wrongly says you're up to date. It tries again by itself after about 5 minutes, 30 minutes and 2 hours. An interrupted update download continues where it stopped.
- **Update and error reports:** Thrive now tells our server whether updates install and reopen, and about errors, so we can fix problems before you notice them. No personal content is sent, and you can turn it off. See "Update and error reports" below.
- **Diagnostic logs** now go to our new reports server, without your user name, and Thrive tells you a reference number.

## What's New in Alpha 15.19
- **You hear every new message.** In the chat you're in, a new message now plays a sound and is read aloud. Before, it was added silently and marked read, so messages that arrived while you were typing, or while you were away, were easy to miss.
- **Away from the computer:** if nobody has touched the keyboard or mouse for a minute, new messages stay unread and you get the normal alert, even with the chat in front.
- **Alerts that always get through:** with "Show notification with username", Thrive now also plays a sound and has your screen reader say "New message from …", in case Windows hides the notification. Notifications themselves are fixed too: Windows was dropping them.
- **Reading older messages:** a new message no longer pulls you off the message you're reading. Thrive reads it out instead.
- **Updates:** Thrive also checks for updates every six hours while it's open, not only when you sign in.
- **New setting:** Settings, General, "New message in the chat I'm in": play a sound and read it aloud (the default), play a sound only, or nothing.

## Hearing New Messages
- **In the chat you're in:** you hear the receive sound, and Thrive reads the message ("Name: message"). If you're on the newest message in the history, your screen reader reads it as the list moves to it. Change this in Settings, General, **New message in the chat I'm in**.
- **Chat in front but you haven't touched the keyboard for a minute** (for example, you're listening): Thrive reads the message in full, and it stays unread until you press a key in that chat.
- **Anywhere else** (another chat, another app, minimised, or closed): what happens is set by **Incoming message behavior**. With **Show notification with username** you get a notification, the receive sound and "New message from …". The chat's tab and the contact show it as unread until you open it.
- A message counts as read only once you've seen it in the chat in front, so the sender's "read" is accurate.

## What's New in Alpha 15.18
- **Check for Updates is back** in the Help menu, with **Alt+P** from anywhere in the main window. On a Mac it's also in the Thrive Messenger menu. Thrive says "Checking for updates", then tells you either that you're up to date or that a new version is ready to install.
- The message box hint now says what Enter really does: nothing by default, unless you set Enter to send in Settings.

## Updates
- Thrive checks for updates by itself when it starts, and every six hours while it's open.
- To check now, choose **Help, Check for Updates…** or press **Alt+P**. On a Mac it's also in the **Thrive Messenger** menu.
- If a new version is available, Thrive asks whether to download and install it, then restarts on the new version. If you're up to date, it says so.
- If the update server can't be reached, Thrive says so calmly (only when you asked) and tries again by itself later. An interrupted download continues where it stopped.
- **Updates never interrupt your typing.** If you're actively typing, or have unsent text anywhere, Thrive won't show the "Update Available" dialog or any progress bar over your message box -- it waits until you're idle, or downloads silently in the background. Every open draft is saved to disk before Thrive ever installs and restarts, no matter what. If you still have an unsent draft at that moment, Thrive asks **Install now or later?** instead of restarting on you; choosing **Later** keeps the download so it won't happen twice. After the restart, Thrive reopens the chat you were in and restores your drafts.
- **What's New** after an update: see "What's New in Alpha 15.24" above, and **Help, What's New** any time.

## Update and error reports
To help us fix problems quickly, Thrive tells our server when an update installs, fails or doesn't reopen, and when the app hits an error. A report contains a random install number (not linked to your account), the Thrive version, your operating system version and a short error description. It never includes your messages, contacts, files, passwords, keys or user name. You can turn this off in Settings, General, "Send update results and error reports". Diagnostic logs are only sent when you choose Help, Submit Diagnostic Logs, and Thrive then gives you a reference to quote.

## What's New in Alpha 15.17
- **Links in chats:** a message says how many links it has. Left Arrow and Right Arrow move between them, and Enter opens one in a full view inside Thrive. Escape comes back. Link lists and link removal are in the message menu.
- **Go to** (Control+G): jump to messages with links, from a person, your own, unread, by date, or by search. Alt+Left goes back.
- **Chat rooms:** open rooms from the Groups tab as chat tabs, with members, roles, topics, @mentions, "read by 2 of 5", voice messages and moderation.
- **Reactions** (Alt+R on a message): thumbs up, heart, seen and more.
- **Reconnect:** Thrive reconnects by itself after any outage and fills in what you missed.
- **Start at sign-in:** on by default, and Thrive doesn't take focus.
- **Chat tabs:** arrowing along a tab strip stays on the tabs. Enter, Space or Tab moves into the page.
- **Mac:** the Mac app now runs natively on Apple silicon and on Intel Macs.
- **iPhone:** a native iPhone app is in testing through TestFlight. See "On iPhone" below.

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

### Moving along the tabs
There are two tab strips: the conversation tabs at the top of the Chats window, and the inner tabs inside each conversation (Messages, Chat Archive, File Transfers, and Members in a room).
1. Press Tab or Shift+Tab until you reach a tab strip. The screen reader reads the tab.
2. Press Left Arrow or Right Arrow to move between tabs. Focus stays on the tabs, so you can keep arrowing. The page behind the tab is updated, but nothing extra is announced.
3. Press Enter or Space to move into that page. On the Messages tab this puts you in the message box. Tab also moves into the page.
- Control+Page Down and Control+Page Up (inner tabs) and Control+Tab (conversations) still switch tabs from anywhere in the chat.

## Sending Messages
- Type in the message box, then press **Alt+S** (the Send button) to send. On a Mac, use the Send button, or set Enter to Send message.
- What **Enter** does in the message box is set in Settings, General tab, Chat Behavior: **Enter key action**. The choices are **Do nothing** (the default), **Send message** and **Place call**. Choose Send message if you want Enter to send.
- **Shift+Enter** (or Alt+Enter) always puts a new line in the message box.
- **Control+Enter** sends a file to this person.
- **Escape** closes the chat. With **Require double Escape to dismiss chat windows** on (the default), the first Escape shows "Press Escape again to close this chat", and a second Escape within about a second closes it. While you are editing a message, Escape cancels the edit instead.

## Drafts
- Whatever you type but don't send is saved as a draft automatically, about a second after you stop typing, and restored the next time you open that chat -- including after Thrive updates and restarts, or if you quit and relaunch it yourself.
- The contact list and room list show it: `Name  |  status  |  Draft: first few words`, so NVDA/VoiceOver reads it as part of the normal row.
- Sending the message, or clearing the message box, clears its draft.
- Turn this off in Settings, General tab, Chat Behavior: **Remember unsent messages as drafts** (on by default). Turning it off also forgets any drafts already saved, matching "remember."
- Updates respect this too: see **Updates** below for how Thrive protects an unsent draft during an update.

## Inside a Conversation
Each conversation has three tabs:
- **Messages**: the live chat.
- **Chat Archive** (formerly "Saved Messages"): every day of this conversation, from the server's history plus anything saved on this device, grouped by year, month and day. Choose newest or oldest first. Press Enter on a day to read it in a read-only text box. Escape goes back to the list of days. Control+S on a message also saves it on this device.
- **File Transfers**: every file and voice message you sent to or received from this person, with name, size, date, direction and status. Received files are kept in a folder for each person under Documents, ThriveMessenger, files, named with their user name (for example files\SystemMonitor). Files shared in a room go in files\Rooms\<room name>. In a conversation's File Transfers tab, Open Their Files Folder opens that person's folder, and Show in Folder shows the selected file.
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
  - **Show list of links:** in this message, in this conversation (its whole history), in this chat window (all open tabs) or in all conversations. Each item reads "title, address, sender, time". Enter opens, Control+C copies the link, Control+Shift+C copies the title, Delete removes it, and the Applications key shows more actions. Every one of those closes the list and puts you back on the message it came from, the same as Escape or Control+W.
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
- `Enter`: in the contact list, open a chat with the selected contact. In the message box, it does what Settings, **Enter key action** says (Do nothing by default, or Send message).
- `Alt+S`: send the message
- `Alt+P`: Check for Updates (also in the Help menu)
- `Shift+Enter`: New line in chat message box
- `Ctrl+Enter`: send a file in a chat
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
  - `Alt+P` Check for Updates
  - `Alt+O` Logout
  - `Alt+X` Exit
- In a chat window:
  - `Ctrl+Tab` / `Ctrl+Shift+Tab`: next or previous conversation tab
  - `Ctrl+1` to `Ctrl+8`: go to that conversation; `Ctrl+9`: the last one
  - `Ctrl+W` or `Ctrl+F4`: close the current conversation
  - `Ctrl+0`: go to the contact list
  - `Ctrl+Page Down` / `Ctrl+Page Up`: next or previous inner tab (Messages, Chat Archive, File Transfers, and Members in a room)
  - On a tab strip: `Left`/`Right` move between tabs and keep focus on the tabs; `Enter`, `Space` or `Tab` move into the page
  - `Ctrl+G`: Go to (messages with links, from a person, mine, unread, by date, search)
  - `Ctrl+E`: insert emoji
  - `Ctrl+R`: record a voice message (press again to stop)
  - `Ctrl+Shift+R`: leave a voicemail
  - `Escape`: close the chat (press it twice when Require double Escape is on); while editing, cancel the edit
  - On a message: `Ctrl+C` copy, `Ctrl+S` save to Chat Archive, `Delete` delete, `Alt+R` react, `Applications` or `Shift+F10` for all actions
  - On a message with links: `Left`/`Right` move between its links, `Enter` or `Space` open the link
  - In the message list: `Alt+Down` / `Alt+Up` next or previous message with a link, `Alt+Left` back to where you were before a jump, `Ctrl+Home` / `Ctrl+End` first or last message
  - In full view of a link: `Escape` or `Ctrl+W` close, `Alt+Left` / `Alt+Right` back and forward, `F5` reload
  - In a list of links: `Enter` open, `Ctrl+C` copy the link, `Ctrl+Shift+C` copy the title, `Delete` remove, `Escape`/`Ctrl+W` close - each one closes the list and returns to the message it came from
  - On a voice message: `Enter` play or stop, `Space` pause or resume, `Left`/`Right` skip 5 seconds


## On a Mac
Thrive for Mac has the same features. Where Windows uses Control, the Mac uses Command. A few keys differ so they don't clash with macOS or VoiceOver:
- Switch conversation tabs: `Control+Tab` / `Control+Shift+Tab`, or `Command+Shift+]` / `Command+Shift+[`.
- Go to a conversation: `Command+1` to `Command+9`. Close it: `Command+W`. Go to the contact list: `Command+0`.
- Switch the inner tabs (Messages, Chat Archive, File Transfers): `Control+Page Down` / `Control+Page Up`, or `Command+Option+Right` / `Command+Option+Left`.
- Insert emoji: `Command+E`. Record a voice message: `Command+R`. Leave a voicemail: `Command+Shift+R`.
- Check for Updates: in the **Thrive Messenger** menu and the **Help** menu, or `Option+P`.
- Go to: `Command+G`. First and last message: `Command+Home` and `Command+End`.
- Shortcuts that use Alt on Windows use Option on a Mac, for example `Option+R` to react and `Option+Down` for the next message with a link.
- On a message: `Command+C` copies, `Command+S` saves to Chat Archive, and `Command+Delete` deletes.
- Announcements (typing, copied, voice messages) go to VoiceOver when it's on. If VoiceOver is off, the Mac speaks them with its built-in voice.
- The first time you record, macOS asks for permission to use the microphone.
- Saved passwords and passkeys are kept in the macOS Keychain. On Windows they're kept in Windows Credential Manager. Neither is ever stored in a settings file.

## On iPhone (TestFlight beta)
Thrive for iPhone is a separate, native app, now in testing through TestFlight. It needs iOS 17 or later. It has three tabs at the bottom: **Chats**, **Rooms** and **Settings**.

### Signing in
1. Enter your username and password. The server is TappedIn (`im.tappedin.fm`).
2. Leave **Stay signed in** on to sign in automatically next time.
3. Tap **Sign in**.
- This version connects to the TappedIn server only. Settings says more servers, including your own, are coming in a later version.

### Chats and rooms
- **Chats** lists your contacts. VoiceOver reads each as "name, online or offline, status, unread count". Double-tap to open the chat.
- **Rooms** lists your rooms and public rooms, with a Search rooms field. Pull down to refresh. Opening a public room you're not in joins it. A private room needs an invitation. **Create room** (the plus button) asks for a name, a topic and whether it's private.
- In a chat, the top bar has **Go to**, **Links**, **Members** (rooms only) and, after a jump, **Back to where I was**.
- The bottom of the chat has the message box, **Record voice message** and **Send**. Activate Record again to stop and send. The first time, iOS asks for the microphone.
- **Load earlier messages** is at the top of the list.

### Messages with VoiceOver
- Each message is one item that reads "sender, time, text, edited, number of links, reactions, status".
- Swipe up or down on a message for its actions: **Copy**, **React**, **Thumbs up**, **Seen**, and when they apply, **Play voice message**, **Open link**, **Links in this message**, **Edit** and **Delete for everyone**. Double-tap to use the action you chose.
- Without VoiceOver, double-tapping a message opens its first link, or plays it if it's a voice message.
- Touching and holding a message shows a menu with Copy, React, Links in this message, Edit, Delete for everyone, and in a room, **Who has read this** for your own messages.
- In a list of links, swipe up or down for **Copy link** and **Copy title**.
- In Members, swipe up or down on a member for mute, remove, ban and role changes, when your room role allows it.

### iPhone settings
The Settings tab is a list of categories. Each one says in a line what's inside; nothing is changed on that list. Double-tap a category to open its own screen. At the top of that screen is a row of tabs (swipe to it, then double-tap a tab); VoiceOver says which tab you're on.
- **General:** tabs **Links** (Open links inside Thrive) and **About** (version, and how to send feedback through TestFlight).
- **Notifications:** tabs **Chats** and **Rooms**. **New message in the chat I'm in**: read it aloud (the default), play a sound, or nothing. **Messages in other chats**: read the message aloud (the default), say who it's from, or nothing (just count it). **Room messages when the room isn't open**: only when someone mentions me, every message, or nothing.
- **Privacy:** tabs **Messages** (Send read receipts) and **Links** (Fetch link titles).
- **Profile and Authentication:** tabs **Account** (who you're signed in as, the server, and **Sign out**) and **Servers**.
- If the connection drops, a "Reconnecting" banner shows at the top and VoiceOver says "Reconnecting", then "Reconnected". Thrive also checks the connection when you come back to the app.

## Notes
- Server-side account permissions are enforced by each server.
- This build includes TappedIn server defaults and multi-server profile selection.
