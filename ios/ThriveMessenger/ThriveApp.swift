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
    @FocusState private var focus: Field?
    enum Field { case user, password }

    var body: some View {
        NavigationStack {
            Form {
                Section("Server") {
                    Text(model.server.name).accessibilityLabel("Server: \(model.server.name)")
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
        }
    }

    private func signIn() {
        guard !user.isEmpty, !password.isEmpty else { return }
        model.signIn(user: user, password: password, remember: remember)
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
    @State private var showFindPeople = false
    @State private var showCreateAccount = false
    @State private var showPendingAccounts = false

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
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Menu("Contacts") {
                    Button("Find people") { showFindPeople = true }
                    if model.isAdmin && model.canUseFeature("admin_create_account") && model.featureVisible("admin_create_account") {
                        Button("Create new account") { showCreateAccount = true }
                        Button("Pending accounts") { showPendingAccounts = true }
                    }
                }
            }
        }
        .sheet(isPresented: $showFindPeople) { FindPeopleView() }
        .sheet(isPresented: $showCreateAccount) { CreateAccountView() }
        .sheet(isPresented: $showPendingAccounts) { PendingAccountsView() }
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

struct FindPeopleView: View {
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss
    @State private var search = ""

    private var matches: [DirectoryPerson] {
        let q = search.trimmingCharacters(in: .whitespacesAndNewlines)
        return q.isEmpty ? model.directoryPeople : model.directoryPeople.filter { $0.user.localizedCaseInsensitiveContains(q) }
    }

    var body: some View {
        NavigationStack {
            List(matches) { person in
                HStack {
                    VStack(alignment: .leading) {
                        Text(person.user)
                        Text(person.online ? "Online" : "Offline").foregroundStyle(.secondary)
                    }
                    Spacer()
                    if person.isContact { Text("Contact").foregroundStyle(.secondary) }
                    else { Button("Add") { model.addContact(person.user) }.accessibilityLabel("Add \(person.user) to contacts") }
                }
                .accessibilityElement(children: .combine)
            }
            .searchable(text: $search, prompt: "Username or display name")
            .navigationTitle("Find People")
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Close") { dismiss() } } }
            .onAppear { model.findPeople() }
        }
    }
}

struct CreateAccountView: View {
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss
    @State private var username = ""
    @State private var displayName = ""
    @State private var email = ""
    @State private var note = ""

    var body: some View {
        NavigationStack {
            Form {
                Section("Person") {
                    TextField("Username", text: $username).textInputAutocapitalization(.never).autocorrectionDisabled()
                    TextField("Display name (optional)", text: $displayName)
                    TextField("Email", text: $email).textContentType(.emailAddress).keyboardType(.emailAddress).textInputAutocapitalization(.never).autocorrectionDisabled()
                }
                Section("Private admin note") { TextField("Note (optional)", text: $note, axis: .vertical) }
                Section { Text("The person receives the setup email, chooses their own password, verifies their email, and completes any authentication this server requires. You never see their password.") }
            }
            .navigationTitle("Create New Account")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Send invitation") { model.createPendingAccount(username: username, displayName: displayName, email: email, note: note); dismiss() }
                        .disabled(username.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || email.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }
        }
    }
}

struct PendingAccountsView: View {
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            List(model.pendingAccounts) { account in
                VStack(alignment: .leading) {
                    Text(account.username).font(.headline)
                    Text(account.email).foregroundStyle(.secondary)
                    Text("Expires \(account.expiresAt)").font(.footnote).foregroundStyle(.secondary)
                    HStack {
                        Button("Resend") { model.resendPendingAccount(account.username) }
                        Button("Cancel", role: .destructive) { model.cancelPendingAccount(account.username) }
                    }
                }
                .accessibilityElement(children: .contain)
            }
            .overlay { if model.pendingAccounts.isEmpty { ContentUnavailableView("No pending accounts", systemImage: "person.crop.circle.badge.clock") } }
            .navigationTitle("Pending Accounts")
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Close") { dismiss() } } }
            .onAppear { model.loadPendingAccounts() }
        }
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
