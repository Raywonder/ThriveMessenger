import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var model: MessengerModel
    @State private var user = ""
    @State private var password = ""
    @State private var selectedGroup: Group?
    @State private var newMessage = ""
    @State private var showingCreate = false

    var body: some View {
        NavigationSplitView {
            List(selection: $selectedGroup) {
                Section("Group Chats") {
                    ForEach(model.client.groups) { group in
                        VStack(alignment: .leading) {
                            Text(group.name).font(.headline)
                            Text("\(group.memberCount) members" + (group.topic.isEmpty ? "" : " · \(group.topic)"))
                                .font(.caption).foregroundStyle(.secondary)
                        }.tag(group)
                    }
                }
                Section("Contacts") {
                    ForEach(model.client.contacts) { contact in
                        Label(contact.user, systemImage: contact.online ? "circle.fill" : "circle")
                    }
                }
            }
            .navigationTitle("Thrive Messenger")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) { Button("Sign In") { signIn() } }
                ToolbarItem(placement: .topBarTrailing) { Button("New Group", systemImage: "person.3.fill") { showingCreate = true } }
            }
        } detail: {
            if let group = selectedGroup {
                GroupChatView(group: group, client: model.client, draft: $newMessage)
            } else {
                ContentUnavailableView("Choose a group chat", systemImage: "bubble.left.and.bubble.right", description: Text("Group chats appear here with their names and member counts."))
            }
        }
        .alert("Create Group", isPresented: $showingCreate) {
            Button("Cancel", role: .cancel) {}
            Button("Create") { model.client.createGroup(name: "New Group", topic: "") }
        } message: { Text("Use the group controls to create a named room. The first iOS slice is connected to the existing Thrive group-chat protocol.") }
        .alert("Connection", isPresented: Binding(get: { model.client.errorMessage != nil }, set: { if !$0 { model.client.errorMessage = nil } })) {
            Button("OK", role: .cancel) {}
        } message: { Text(model.client.errorMessage ?? "") }
    }

    private func signIn() {
        guard !user.isEmpty else { return }
        model.client.connect(user: user, password: password)
    }
}

struct GroupChatView: View {
    let group: Group
    @ObservedObject var client: ThriveClient
    @Binding var draft: String

    var body: some View {
        VStack {
            List(client.groupMessages[group.name] ?? []) { message in
                VStack(alignment: .leading, spacing: 3) {
                    Text(message.sender).font(.headline)
                    Text(message.text)
                    if !message.time.isEmpty { Text(message.time).font(.caption).foregroundStyle(.secondary) }
                }
                .accessibilityElement(children: .combine)
            }
            HStack {
                TextField("Message", text: $draft, axis: .vertical)
                    .textFieldStyle(.roundedBorder)
                    .accessibilityLabel("Message for \(group.name)")
                Button("Send") {
                    let text = draft.trimmingCharacters(in: .whitespacesAndNewlines)
                    guard !text.isEmpty else { return }
                    client.sendMessage(text, to: group.name); draft = ""
                }
            }.padding()
        }
        .navigationTitle(group.name)
        .toolbar { ToolbarItem(placement: .topBarTrailing) { Button("Join") { client.join(group: group.name) } } }
        .onAppear { client.refreshGroups() }
    }
}
