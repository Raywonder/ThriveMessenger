import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var model: MessengerModel
    @State private var user = ""
    @State private var password = ""
    @State private var selectedGroup: Group?
    @State private var newMessage = ""
    @State private var showingCreate = false

    var body: some View {
        GroupNavigationView(selectedGroup: $selectedGroup, draft: $newMessage, showCreate: $showingCreate)
            .environmentObject(model)
            .alert("Create Group", isPresented: $showingCreate) {
                Button("Cancel", role: .cancel) {}
                Button("Create") { model.client.createGroup(name: "New Group", topic: "") }
            } message: {
                Text("The first iOS slice is connected to the existing Thrive group-chat protocol.")
            }
            .alert("Connection", isPresented: Binding(get: { model.client.errorMessage != nil }, set: { if !$0 { model.client.errorMessage = nil } })) {
                Button("OK", role: .cancel) {}
            } message: { Text(model.client.errorMessage ?? "") }
    }

    private func signIn() {
        guard !user.isEmpty else { return }
        model.client.connect(user: user, password: password)
    }
}

private struct GroupNavigationView: View {
    @EnvironmentObject private var model: MessengerModel
    @Binding var selectedGroup: Group?
    @Binding var draft: String
    @Binding var showCreate: Bool

    var body: some View {
        NavigationSplitView {
            GroupSidebar(groups: model.client.groups, contacts: model.client.contacts, selection: $selectedGroup)
                .navigationTitle("Thrive Messenger")
                .toolbar {
                    ToolbarItem(placement: .topBarLeading) { Button("Sign In") { model.client.connect(user: "", password: "") } }
                    ToolbarItem(placement: .topBarTrailing) { Button("New Group", systemImage: "person.3.fill") { showCreate = true } }
                }
        } detail: {
            if let group = selectedGroup {
                GroupChatView(group: group, client: model.client, draft: $draft)
            } else {
                ContentUnavailableView("Choose a group chat", systemImage: "bubble.left.and.bubble.right", description: Text("Group chats appear here with their names and member counts."))
            }
        }
    }
}

private struct GroupSidebar: View {
    let groups: [Group]
    let contacts: [Contact]
    @Binding var selection: Group?

    var body: some View {
        List(selection: $selection) {
            Section("Group Chats") {
                ForEach(groups) { group in
                    GroupRow(group: group).tag(group)
                }
            }
            Section("Contacts") {
                ForEach(contacts) { contact in
                    Label(contact.user, systemImage: contact.online ? "circle.fill" : "circle")
                }
            }
        }
    }
}

private struct GroupRow: View {
    let group: Group

    var body: some View {
        VStack(alignment: .leading) {
            Text(group.name).font(.headline)
            Text(memberSummary).font(.caption).foregroundStyle(.secondary)
        }
    }

    private var memberSummary: String {
        let topic = group.topic.isEmpty ? "" : " · \(group.topic)"
        return "\(group.memberCount) members\(topic)"
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
