import SwiftUI

/// Settings, the VoiceLink way: the root is only a list of categories with a one-line hint each (nothing can be
/// changed there). A category opens its own screen, with its settings grouped into tabs by a segmented control.
enum SettingsCategory: String, CaseIterable, Identifiable, Hashable {
    case general, notifications, privacy, profile, help
    var id: String { rawValue }

    var title: String {
        switch self {
        case .general: return "General"
        case .notifications: return "Notifications"
        case .privacy: return "Privacy"
        case .profile: return "Profile and Authentication"
        case .help: return "Help and What's New"
        }
    }
    var hint: String {
        switch self {
        case .general: return "How links open, and the app version."
        case .notifications: return "What you hear when messages arrive."
        case .privacy: return "Read receipts and link titles."
        case .profile: return "Your account, servers and signing out."
        case .help: return "Every action on a chat, a message and a contact, plus what changed."
        }
    }
    var icon: String {
        switch self {
        case .general: return "gearshape"
        case .notifications: return "bell"
        case .privacy: return "lock.shield"
        case .profile: return "person.circle"
        case .help: return "questionmark.circle"
        }
    }
    var tabs: [String] {
        switch self {
        case .general: return ["Links", "Keyboard", "About"]
        case .notifications: return ["Chats", "Rooms"]
        case .privacy: return ["Messages", "Links"]
        case .profile: return ["Account", "Servers"]
        case .help: return ["Messages", "Contacts", "Keyboard", "What's new"]
        }
    }
}

struct SettingsView: View {
    var body: some View {
        List {
            Section {
                ForEach(SettingsCategory.allCases) { cat in
                    NavigationLink(value: cat) {
                        HStack(spacing: 12) {
                            Image(systemName: cat.icon).frame(width: 24).accessibilityHidden(true)
                            VStack(alignment: .leading, spacing: 2) {
                                Text(cat.title).font(.body)
                                Text(cat.hint).font(.footnote).foregroundStyle(.secondary)
                            }
                        }
                        .padding(.vertical, 2)
                    }
                    .accessibilityElement(children: .ignore)
                    .accessibilityLabel(cat.title)
                    .accessibilityValue(cat.hint)
                    .accessibilityHint("Opens \(cat.title) settings.")
                    .accessibilityAddTraits(.isButton)
                    .accessibilityIdentifier("settings.category.\(cat.rawValue)")
                }
            } footer: {
                Text("Choose a category to change its settings. Each one has tabs at the top.")
            }
        }
        .navigationTitle("Settings")
        .navigationDestination(for: SettingsCategory.self) { SettingsCategoryView(category: $0) }
    }
}

struct SettingsCategoryView: View {
    let category: SettingsCategory
    @Environment(AppModel.self) private var model
    @State private var tab = 0

    var body: some View {
        @Bindable var model = model
        Form {
            Section {
                Picker("Section", selection: $tab) {
                    ForEach(Array(category.tabs.enumerated()), id: \.offset) { i, name in Text(name).tag(i) }
                }
                .pickerStyle(.segmented)
                .accessibilityLabel("\(category.title) tabs")
                .accessibilityIdentifier("settings.tabs")
            }
            content(model: $model)
        }
        .navigationTitle(category.title)
        .navigationBarTitleDisplayMode(.inline)
        .onChange(of: tab) { _, new in Announce.say("\(category.tabs[new]) tab") }
    }

    @ViewBuilder
    private func content(model: Bindable<AppModel>) -> some View {
        let tabName = category.tabs[min(tab, category.tabs.count - 1)]
        switch (category, tabName) {
        case (.general, "Links"):
            Section {
                Toggle("Open links inside Thrive", isOn: model.linkOpenInApp)
            } header: { Text("Links").accessibilityAddTraits(.isHeader) } footer: {
                Text("On: links open in a browser view inside Thrive, and Done brings you back to the chat. Off: they open in Safari.")
            }
        case (.general, "Keyboard"):
            Section {
                Toggle("Enter key sends message", isOn: model.enterKeySendsMessage)
            } header: { Text("Keyboard").accessibilityAddTraits(.isHeader) } footer: {
                Text("With a hardware keyboard: Shift+Enter or Option+Enter always makes a new line, and Command+Enter always sends. Has no effect on the on-screen keyboard.")
            }
        case (.general, _):
            Section {
                LabeledContent("Version", value: appVersion)
                Text("To send feedback, open TestFlight, choose Thrive Messenger, then Send Beta Feedback.")
            } header: { Text("About").accessibilityAddTraits(.isHeader) }
        case (.notifications, "Chats"):
            Section {
                Picker("New message in the chat I'm in", selection: model.openChatAlert) {
                    Text("Read it aloud").tag("read")
                    Text("Play a sound").tag("sound")
                    Text("Nothing").tag("none")
                }
                Picker("Messages in other chats", selection: model.otherChatAlert) {
                    Text("Read the message aloud").tag("read")
                    Text("Say who it's from").tag("name")
                    Text("Nothing, just count it").tag("none")
                }
            } header: { Text("Chats").accessibilityAddTraits(.isHeader) } footer: {
                Text("VoiceOver reads new messages as they arrive. Unread messages are counted in the Chats list either way.")
            }
        case (.notifications, _):
            Section {
                Picker("Room messages when the room isn't open", selection: model.roomAlerts) {
                    Text("Only when someone mentions me").tag("mentions")
                    Text("Announce every message").tag("all")
                    Text("Nothing").tag("none")
                }
            } header: { Text("Rooms").accessibilityAddTraits(.isHeader) } footer: {
                Text("In the room you have open, new messages are handled like the chat you're in.")
            }
        case (.privacy, "Messages"):
            Section {
                Toggle("Send read receipts", isOn: model.sendReadReceipts)
            } header: { Text("Messages").accessibilityAddTraits(.isHeader) } footer: {
                Text("Lets people see when you've read their messages. When this is off, you don't see theirs either.")
            }
        case (.privacy, _):
            Section {
                Toggle("Fetch link titles", isOn: model.fetchLinkTitles)
            } header: { Text("Links").accessibilityAddTraits(.isHeader) } footer: {
                Text("The Thrive server looks up each link's page title, so links are read by name. Sites see the server, not you.")
            }
        case (.profile, "Account"):
            Section {
                LabeledContent("Signed in as", value: model.wrappedValue.username)
                LabeledContent("Server", value: model.wrappedValue.server.name)
                Button("Sign out", role: .destructive) { model.wrappedValue.signOut() }
            } header: { Text("Account").accessibilityAddTraits(.isHeader) }
        case (.profile, _):
            Section {
                ForEach(model.wrappedValue.servers) { s in
                    Text(s.id == model.wrappedValue.server.id ? "\(s.name), current" : s.name)
                }
            } header: { Text("Servers").accessibilityAddTraits(.isHeader) } footer: {
                Text("More servers, including your own, are coming in a later version.")
            }
        case (.help, "Messages"):
            Section {
                Text("Double-tap a message to use it: a message with one link opens that link, and a voice message starts playing. Double-tap the same voice message again to pause it, and once more to carry on from where it stopped.")
                Text("Swipe up or down with one finger on a message to hear its other actions: Copy, React, Thumbs up, Links in this message, and Edit or Delete for everyone on your own recent messages.")
                Text("There is no separate Play action. Playing is what activating a voice message does.")
                Text("With a hardware keyboard you can press Enter on the message instead of double-tapping it.")
            } header: { Text("In a chat").accessibilityAddTraits(.isHeader) } footer: {
                Text("Messages are marked read for you automatically a few seconds after you reach them.")
            }
        case (.help, "Contacts"):
            Section {
                Text("Double-tap a contact to open the chat. Swipe up or down on a contact for the rest: Message, Voice message, Call when your server offers it, Add to group, Block or Unblock, Remove contact, and Copy username.")
                Text("Voice message opens the chat and starts recording straight away. Activate the same button again to stop and send it.")
                Text("Remove contact asks you to confirm first. Block and Unblock are one action that changes name, so you always see the one that applies.")
            } header: { Text("Chats list").accessibilityAddTraits(.isHeader) } footer: {
                Text("Touch and hold a contact for the same list without VoiceOver.")
            }
        case (.help, "Keyboard"):
            Section {
                Text("Enter sends the message you're typing, unless you turn that off in General, Keyboard.")
                Text("Shift+Enter or Option+Enter always makes a new line. Command+Enter always sends.")
                Text("Enter on a voice message, when you're on the message itself and not in the typing box, plays it. Enter again pauses it, and once more carries on from where it stopped. It's the same play and pause as double-tapping the message.")
            } header: { Text("Hardware keyboard").accessibilityAddTraits(.isHeader) } footer: {
                Text("These only apply with a hardware keyboard connected.")
            }
        case (.help, _):
            Section {
                Text("Voice messages now pause and carry on. Activating one starts it, activating it again pauses it, and again resumes it instead of jumping back to the beginning.")
                Text("The separate \"Play voice message\" action is gone from messages, because activating the message already plays it.")
                Text("The \"Seen\" reaction is gone. Thrive already tells the sender you've read a message a few seconds after you reach it.")
                Text("Contacts in the Chats list now have actions: Message, Voice message, Call, Add to group, Block, Remove contact and Copy username.")
                Text("With a hardware keyboard, Enter on a voice message plays, pauses and resumes it, so you don't have to double-tap.")
            } header: { Text("What's new in this version").accessibilityAddTraits(.isHeader) } footer: {
                Text("Version \(appVersion).")
            }
        }
    }

    private var appVersion: String {
        let v = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? ""
        let b = Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion") as? String ?? ""
        return "\(v) (\(b))"
    }
}
