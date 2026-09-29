import SwiftUI

/// The room directory: your rooms and public rooms, with search. Opening a public room you're not in joins it.
struct RoomsView: View {
    @Environment(AppModel.self) private var model
    @State private var query = ""
    @State private var creating = false
    @State private var path: [ConversationKind] = []

    var body: some View {
        NavigationStack(path: $path) { list }
    }

    private var list: some View {
        List(filtered) { r in
            Button {
                if r.role.isEmpty {
                    if r.visibility == "public" { model.roomAction("group_room_join", room: r.id) }
                    else { Announce.say("That private room needs an invitation from a member.") }
                } else {
                    path.append(.room(r.id))
                }
            } label: {
                VStack(alignment: .leading) {
                    Text(r.name).font(.headline)
                    Text([r.roleLabel.isEmpty ? "not joined" : r.roleLabel, "\(r.memberCount) members", r.unread > 0 ? "\(r.unread) unread" : ""]
                        .filter { !$0.isEmpty }.joined(separator: " · ")).font(.caption)
                    if !r.topic.isEmpty { Text(r.topic).font(.caption).foregroundStyle(.secondary) }
                }
            }
            .accessibilityLabel(r.spokenSummary)
            .contextMenu {
                if !r.role.isEmpty { Button("Leave room", role: .destructive) { model.roomAction("group_room_leave", room: r.id) } }
                if r.role == "owner" { Button("Delete room", role: .destructive) { model.roomAction("group_room_delete_room", room: r.id) } }
            }
        }
        .searchable(text: $query, prompt: "Search rooms")
        .refreshable { model.send(["action": "group_room_list"]) }
        .navigationTitle("Rooms")
        .toolbar { Button { creating = true } label: { Label("Create room", systemImage: "plus") } }
        .sheet(isPresented: $creating) { CreateRoomSheet() }
        .navigationDestination(for: ConversationKind.self) { ChatView(kind: $0) }
        .onReceive(NotificationCenter.default.publisher(for: .thriveOpenRoom)) { note in
            if let id = note.object as? String { path.append(.room(id)) }
        }
        .onAppear { model.send(["action": "group_room_list"]) }
    }

    private var filtered: [RoomSummary] {
        let words = query.lowercased().split(separator: " ")
        guard !words.isEmpty else { return model.rooms }
        return model.rooms.filter { r in words.allSatisfy { (r.name + " " + r.topic + " " + r.description).lowercased().contains($0) } }
    }
}

struct CreateRoomSheet: View {
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss
    @State private var name = ""
    @State private var topic = ""
    @State private var isPrivate = false

    var body: some View {
        NavigationStack {
            Form {
                TextField("Room name", text: $name)
                TextField("Topic", text: $topic)
                Toggle("Private (invite only)", isOn: $isPrivate)
            }
            .navigationTitle("Create room")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Create") {
                        model.send(["action": "group_room_create", "name": name, "topic": topic, "visibility": isPrivate ? "private" : "public"])
                        dismiss()
                    }.disabled(name.trimmingCharacters(in: .whitespaces).isEmpty)
                }
            }
        }
    }
}

/// Topic and members with role, muted, and whether they've read the newest message; moderation for moderators and up.
struct MembersView: View {
    let conv: Conversation
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss
    @State private var invitee = ""
    @State private var topic = ""

    var body: some View {
        NavigationStack {
            List {
                Section("Topic") {
                    Text(conv.room?.topic.isEmpty == false ? conv.room!.topic : "No topic set.")
                    if myRank >= 2 {
                        TextField("New topic", text: $topic)
                        Button("Change topic") { model.roomAction("group_room_topic", room: roomID, ["topic": topic]) }.disabled(topic.isEmpty)
                    }
                }
                Section("Members, \(conv.members.count)") {
                    ForEach(conv.members) { m in
                        Text(label(m))
                            .accessibilityActions { actions(m) }
                            .contextMenu { actions(m) }
                    }
                }
                Section("Invite") {
                    TextField("Username", text: $invitee).textInputAutocapitalization(.never).autocorrectionDisabled()
                    Button("Invite") { model.roomAction("group_room_add_member", room: roomID, ["username": invitee, "role": "user"]); invitee = "" }
                        .disabled(invitee.isEmpty)
                }
                Section {
                    Button("Leave room", role: .destructive) { model.roomAction("group_room_leave", room: roomID); dismiss() }
                }
            }
            .navigationTitle("Members")
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Close") { dismiss() } } }
        }
    }

    private var roomID: String { if case .room(let id) = conv.kind { return id }; return "" }
    private var myRank: Int { roleRank[conv.room?.role ?? ""] ?? -1 }

    private func label(_ m: RoomMember) -> String {
        let me = m.username.lowercased() == model.username.lowercased()
        var parts = [me ? "you" : m.username, m.roleLabel]
        if m.muted { parts.append("muted") }
        if !me, let newest = conv.messages.compactMap(\.sentAt).max() {
            parts.append(m.lastReadAt >= newest ? "has read the newest message" : "hasn't read the newest message")
        }
        return parts.joined(separator: ", ")
    }

    @ViewBuilder
    private func actions(_ m: RoomMember) -> some View {
        let theirs = roleRank[m.role] ?? 0
        let canModerate = myRank >= 2 && theirs < myRank && m.username.lowercased() != model.username.lowercased()
        if canModerate {
            Button("Mute for 1 hour") { model.roomAction("group_room_mute", room: roomID, ["username": m.username, "minutes": 60]) }
            if m.muted { Button("Unmute") { model.roomAction("group_room_mute", room: roomID, ["username": m.username, "minutes": 0]) } }
            Button("Remove from room") { model.roomAction("group_room_kick", room: roomID, ["username": m.username]) }
            Button("Ban from room") { model.roomAction("group_room_ban", room: roomID, ["username": m.username]) }
        }
        if myRank >= 3 && theirs < myRank && m.username.lowercased() != model.username.lowercased() {
            ForEach(["guest", "user", "moderator"], id: \.self) { role in
                Button("Make \(role == "user" ? "member" : role)") {
                    model.roomAction("group_room_set_role", room: roomID, ["username": m.username, "role": role])
                }
            }
        }
    }
}
