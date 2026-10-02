import SwiftUI
import UIKit

@main
struct ThriveApp: App {
    @State private var model = AppModel()
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(model)
                .onAppear { model.trySavedSignIn() }
        }
        .onChange(of: scenePhase) { _, phase in
            if phase == .active { model.appBecameActive() }
        }
    }
}

struct RootView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        switch model.phase {
        case .signedOut, .signingIn: SignInView()
        case .online, .reconnecting: MainView()
        }
    }
}

struct SignInView: View {
    @Environment(AppModel.self) private var model
    @State private var user = ""
    @State private var password = ""
    @State private var remember = true
    @State private var showForgotPassword = false
    @State private var showServers = false
    @FocusState private var focus: Field?
    enum Field { case user, password }

    var body: some View {
        NavigationStack {
            Form {
                Section("Server") {
                    Button { showServers = true } label: {
                        LabeledContent("Server", value: model.server.name)
                    }
                    .accessibilityHint("Opens the Thrive server directory. You can also add a server manually.")
                    if !model.serverCompatibilityNote.isEmpty {
                        Text(model.serverCompatibilityNote).foregroundStyle(.orange)
                    }
                }
                Section {
                    TextField("Username", text: $user)
                        .textContentType(.username).textInputAutocapitalization(.never).autocorrectionDisabled()
                        .focused($focus, equals: .user)
                    SecureField("Password", text: $password)
                        .textContentType(.password).focused($focus, equals: .password)
                        .onSubmit(signIn)
                    Toggle("Stay signed in", isOn: $remember)
                }
                if !model.signInError.isEmpty {
                    Section { Text(model.signInError).foregroundStyle(.red) }
                }
                Section {
                    Button(model.phase == .signingIn ? "Signing in…" : "Sign in", action: signIn)
                        .disabled(user.isEmpty || password.isEmpty || model.phase == .signingIn)
                    Button("Forgot password?") { showForgotPassword = true }
                }
            }
            .navigationTitle("Thrive")
            .onAppear { user = model.username; focus = user.isEmpty ? .user : .password }
            .sheet(isPresented: $showForgotPassword) { ForgotPasswordView() }
            .sheet(isPresented: $showServers) { ServerDirectoryView() }
        }
    }

    private func signIn() {
        guard !user.isEmpty, !password.isEmpty else { return }
        model.signIn(user: user, password: password, remember: remember)
    }
}

struct ServerDirectoryView: View {
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss
    @State private var manual = false
    @State private var name = ""
    @State private var host = ""
    @State private var port = "2005"

    var body: some View {
        NavigationStack {
            List {
                Section("Thrive servers") {
                    ForEach(model.servers.filter(\.listed)) { server in
                        Button {
                            model.chooseServer(server); dismiss()
                        } label: {
                            VStack(alignment: .leading) {
                                Text(server.name)
                                Text(server.description.isEmpty ? server.host : server.description).font(.footnote).foregroundStyle(.secondary)
                                Text(server.allowsSignUp ? "Sign-up available" : "Sign-up by invitation only").font(.footnote)
                            }
                        }
                        .accessibilityLabel("\(server.name). \(server.description). \(server.allowsSignUp ? "Sign-up available" : "Sign-up by invitation only")")
                    }
                } footer: { Text("The list refreshes quietly and is cached. A server can choose not to be listed.") }
                Section("Add a server manually") {
                    if manual {
                        TextField("Name", text: $name)
                        TextField("Address", text: $host).textInputAutocapitalization(.never).autocorrectionDisabled()
                        TextField("Port", text: $port).keyboardType(.numberPad)
                        Button("Add server") {
                            model.addManualServer(name: name, host: host, port: UInt16(port) ?? 2005); dismiss()
                        }.disabled(name.isEmpty || host.isEmpty)
                    } else { Button("Add a server manually") { manual = true } }
                }
            }
            .navigationTitle("Server directory")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) { Button("Close") { dismiss() } }
                ToolbarItem(placement: .topBarTrailing) { Button("Refresh") { model.refreshServerDirectory(quiet: false) } }
            }
        }
    }
}

struct MainView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        TabView {
            ContactsView()
                .tabItem { Label("Chats", systemImage: "bubble.left.and.bubble.right") }
            RoomsView()
                .tabItem { Label("Rooms", systemImage: "person.3") }
            NavigationStack { SettingsView() }
                .tabItem { Label("Settings", systemImage: "gear") }
        }
        .safeAreaInset(edge: .top) {
            if model.phase == .reconnecting {
                Text("Reconnecting. Thrive keeps trying in the background.")
                    .font(.footnote).frame(maxWidth: .infinity).padding(6).background(.yellow.opacity(0.3))
                    .accessibilityAddTraits(.isStaticText)
            }
        }
    }
}

struct ContactsView: View {
    @Environment(AppModel.self) private var model
    @State private var path: [ConversationKind] = []
    @State private var addingToGroup: Contact?
    @State private var removing: Contact?

    var body: some View {
        NavigationStack(path: $path) { list }
    }

    private var list: some View {
        List(model.contacts) { c in
            NavigationLink(value: ConversationKind.direct(c.user)) {
                VStack(alignment: .leading) {
                    Text(c.user).font(.headline)
                    Text(c.online ? (c.statusText.isEmpty ? "Online" : c.statusText) : "Offline").font(.subheadline).foregroundStyle(.secondary)
                }
                .accessibilityElement(children: .ignore)
                .accessibilityLabel(rowLabel(c))
                // Both of these go on the VStack that owns the accessibility element. Confirmed on the
                // simulator: with them here the NavigationLink's own Button element takes over this label,
                // so the row is one item. Moved out onto the NavigationLink instead, the Button falls back
                // to reading its raw contents ("a11ytest_b, Offline") and the label set here is lost.
                .accessibilityActions { actions(c) }
                .contextMenu { actions(c) }
            }
        }
        .overlay { if model.contacts.isEmpty { ContentUnavailableView("No contacts yet", systemImage: "person.crop.circle.badge.plus") } }
        .navigationTitle("Chats")
        .navigationDestination(for: ConversationKind.self) { kind in ChatView(kind: kind) }
        .sheet(item: $addingToGroup) { c in AddToGroupSheet(contact: c) }
        .confirmationDialog("Remove \(removing?.user ?? "this contact")?", isPresented: removingConfirm, titleVisibility: .visible) {
            Button("Remove contact", role: .destructive) { if let r = removing { model.deleteContact(r.user) }; removing = nil }
            Button("Keep contact", role: .cancel) { removing = nil }
        } message: {
            Text("This takes \(removing?.user ?? "them") off your contact list on this server.")
        }
    }

    private var removingConfirm: Binding<Bool> {
        Binding(get: { removing != nil }, set: { if !$0 { removing = nil } })
    }

    /// "<user>, online/offline[, status][, N unread]". The server's status text usually starts with the
    /// presence word already ("offline", "online - AI chat assistant ..."), and saying both made every row
    /// read "a11ytest_b, offline, offline" / "Clawdia, online, online - AI chat assistant ...". When the
    /// status already covers presence, it speaks for itself.
    private func rowLabel(_ c: Contact) -> String {
        let presence = c.online ? "online" : "offline"
        let status = c.statusText.trimmingCharacters(in: .whitespacesAndNewlines)
        var parts = [c.user]
        if status.lowercased().hasPrefix(presence) {
            parts.append(status)
        } else {
            parts.append(presence)
            if !status.isEmpty { parts.append(status) }
        }
        if c.unread > 0 { parts.append("\(c.unread) unread") }
        return parts.joined(separator: ", ")
    }

    /// Same set for touch (context menu) and VoiceOver (Actions rotor). Every one of them speaks a result.
    @ViewBuilder
    private func actions(_ c: Contact) -> some View {
        Button("Message") { path.append(.direct(c.user)) }
        Button("Voice message") { model.startRecordingIn = c.user; path.append(.direct(c.user)) }
        if model.featureVisible("voice_call") {
            Button("Call") { model.callContact(c.user) }
        }
        if !model.roomsICanAddTo.isEmpty {
            Button("Add to group") { addingToGroup = c }
        }
        Button(c.blocked ? "Unblock" : "Block") { model.setBlocked(!c.blocked, user: c.user) }
        Button("Remove contact", role: .destructive) { removing = c }
        Button("Copy username") { UIPasteboard.general.string = c.user; Announce.say("Copied") }
    }
}

/// Picks which of your rooms to add a contact to. Only rooms where you're a moderator or above are listed,
/// because those are the only ones the server will accept `group_room_add_member` for.
struct AddToGroupSheet: View {
    let contact: Contact
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            List {
                if model.roomsICanAddTo.isEmpty {
                    Text("You aren't a moderator or owner of any room, so there's nowhere to add \(contact.user).")
                } else {
                    ForEach(model.roomsICanAddTo) { r in
                        Button(r.name) {
                            model.addContactToRoom(contact.user, room: r)
                            dismiss()
                        }
                        .accessibilityLabel("\(r.name), \(r.roleLabel), \(r.memberCount) member\(r.memberCount == 1 ? "" : "s")")
                    }
                }
            }
            .navigationTitle("Add \(contact.user)")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Close") { dismiss() } } }
            .onAppear { model.send(["action": "group_room_list"]) }
        }
    }
}
