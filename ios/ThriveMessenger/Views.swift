import SwiftUI

struct LoginView: View {
    @Bindable var session: ThriveSession
    var body: some View {
        NavigationStack {
            Form {
                Section("Server") {
                    TextField("Host", text: $session.host).textContentType(.URL).textInputAutocapitalization(.never)
                    TextField("Port", value: $session.port, format: .number).keyboardType(.numberPad)
                }
                Section("Account") {
                    TextField("Username", text: $session.username).textContentType(.username).textInputAutocapitalization(.never)
                    SecureField("Password", text: $session.password).textContentType(.password)
                }
                if let error = session.errorMessage { Text(error).foregroundStyle(.red).accessibilityLabel("Sign in error: \(error)") }
                Button(session.isBusy ? "Signing In…" : "Sign In") { Task { await session.signIn() } }
                    .disabled(session.isBusy).accessibilityHint("Connects securely to the selected Thrive server")
            }.navigationTitle("Thrive Messenger")
        }
    }
}

struct ContactsView: View {
    @Bindable var session: ThriveSession
    var body: some View {
        List(session.contacts) { contact in
            Label(contact.name, systemImage: contact.online ? "circle.fill" : "circle")
                .accessibilityLabel("\(contact.name), \(contact.online ? "online" : "offline")")
        }.navigationTitle("Contacts").overlay { if session.contacts.isEmpty { ContentUnavailableView("No Contacts", systemImage: "person.2") } }
    }
}

struct GroupsView: View {
    @Bindable var session: ThriveSession
    var body: some View {
        List(session.rooms) { room in
            Button { Task { await session.openRoom(room) } } label: {
                VStack(alignment: .leading) { Text(room.name); if let role = room.role { Text(role.capitalized).font(.caption).foregroundStyle(.secondary) } }
            }
        }.navigationTitle("Groups").refreshable { await session.refreshRooms() }
          .overlay { if session.rooms.isEmpty { ContentUnavailableView("No Group Rooms", systemImage: "bubble.left.and.bubble.right", description: Text("Pull to refresh.")) } }
    }
}

struct SettingsView: View {
    @Bindable var session: ThriveSession
    var body: some View {
        Form {
            Section("Connected Server") { LabeledContent("Host", value: session.host); LabeledContent("Port", value: String(session.port)) }
            Section { Button("Sign Out", role: .destructive) { session.disconnect() } }
            Section("About") { LabeledContent("Version", value: "Alpha 15.10") }
        }.navigationTitle("Settings")
    }
}
