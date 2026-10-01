import Foundation

/// A Thrive server the app knows. Everything is keyed by server id so several servers can live side by side
/// (see docs/own-server.md); this release signs in to one at a time.
struct ServerEntry: Codable, Hashable, Identifiable {
    var id: String            // stable id; for now "host:port"
    var name: String
    var host: String
    var port: UInt16

    static let tappedIn = ServerEntry(id: "im.tappedin.fm:2005", name: "TappedIn.fm", host: "im.tappedin.fm", port: 2005)
}

struct Contact: Identifiable, Hashable {
    var id: String { user }
    var user: String
    var online: Bool
    var statusText: String
    var isAdmin: Bool
    var blocked: Bool
    var unread: Int = 0
}

/// One row of the server's `feature_caps` table. `uiVisible` is the server saying whether the control
/// should be offered at all; `canUse` is whether this account may actually use it.
struct FeatureCap: Hashable {
    var enabled: Bool
    var uiVisible: Bool
    var scope: String
    var canUse: Bool

    init(_ d: [String: Any]) {
        enabled = d["enabled"] as? Bool ?? false
        uiVisible = d["ui_visible"] as? Bool ?? false
        scope = d["scope"] as? String ?? "all"
        canUse = d["can_use"] as? Bool ?? false
    }
}

struct ReactionGroup: Hashable {
    var emoji: String
    var users: [String]
}

struct VoiceInfo: Hashable {
    var duration: Double
    var stored: Bool
    var serverID: String
}

struct ChatMessage: Identifiable, Hashable {
    var id: String            // server id once known, otherwise the client id
    var clientID: String?
    var serverKnown: Bool
    var sender: String
    var text: String
    var time: Date
    var edited = false
    var deleted = false
    var delivered = false
    var readAt: Date?
    var readSent = false
    var reactions: [ReactionGroup] = []
    var voice: VoiceInfo?
    var mentions: [String] = []
    var fileName: String?
    var seq: Int?             // DM history paging
    var sentAt: Double?       // room history paging and group read receipts
    var queued = false
    var isSystem = false
}

struct RoomMember: Identifiable, Hashable {
    var id: String { username }
    var username: String
    var role: String
    var roleLabel: String
    var lastReadAt: Double
    var muted: Bool
}

struct RoomSummary: Identifiable, Hashable {
    var id: String            // room_id
    var name: String
    var topic: String
    var description: String
    var visibility: String
    var role: String
    var roleLabel: String
    var memberCount: Int
    var unread: Int

    init(_ d: [String: Any]) {
        id = d["room_id"] as? String ?? ""
        name = d["name"] as? String ?? "Room"
        topic = d["topic"] as? String ?? ""
        description = d["description"] as? String ?? ""
        visibility = d["visibility"] as? String ?? "public"
        role = d["role"] as? String ?? ""
        roleLabel = d["role_label"] as? String ?? (role.isEmpty ? "" : role)
        memberCount = d["member_count"] as? Int ?? 0
        unread = d["unread"] as? Int ?? 0
    }

    var spokenSummary: String {
        var parts = [name, roleLabel.isEmpty ? "not joined" : roleLabel, "\(memberCount) member\(memberCount == 1 ? "" : "s")"]
        if unread > 0 { parts.append("\(unread) unread") }
        if visibility == "private" { parts.append("private") }
        if !topic.isEmpty { parts.append("topic: \(topic)") }
        return parts.joined(separator: ", ")
    }
}

enum ConversationKind: Hashable {
    case direct(String)
    case room(String)

    var key: String {
        switch self {
        case .direct(let u): return "dm:" + u.lowercased()
        case .room(let id): return "room:" + id
        }
    }
}

let roleRank: [String: Int] = ["guest": 0, "user": 1, "moderator": 2, "admin": 3, "owner": 4]

enum Reactions {
    static let quick: [(String, String)] = [("\u{1F44D}", "thumbs up"), ("\u{1F44E}", "thumbs down"), ("\u{2764}\u{FE0F}", "heart"),
                                            ("\u{1F602}", "laugh"), ("\u{1F62E}", "wow"), ("\u{1F622}", "sad"),
                                            ("\u{1F389}", "celebrate"), ("\u{2705}", "check mark")]
    static func name(_ emoji: String) -> String {
        if let hit = quick.first(where: { $0.0 == emoji }) { return hit.1 }
        return emoji.unicodeScalars.first?.properties.name?.lowercased() ?? emoji
    }
}

/// Server times arrive as ISO strings (DMs, "…Z" is UTC) or epoch seconds (rooms).
enum ThriveTime {
    static func parse(_ value: Any?) -> Date {
        if let n = value as? Double { return Date(timeIntervalSince1970: n) }
        if let n = value as? Int { return Date(timeIntervalSince1970: Double(n)) }
        guard var s = value as? String, !s.isEmpty else { return Date() }
        let utc = s.hasSuffix("Z")
        if utc { s.removeLast() }
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = utc ? TimeZone(identifier: "UTC") : TimeZone.current
        for format in ["yyyy-MM-dd'T'HH:mm:ss.SSSSSS", "yyyy-MM-dd'T'HH:mm:ss", "yyyy-MM-dd HH:mm:ss.SSSSSS", "yyyy-MM-dd HH:mm:ss"] {
            f.dateFormat = format
            if let d = f.date(from: s) { return d }
        }
        return Date()
    }

    static func spoken(_ date: Date) -> String {
        let f = DateFormatter()
        if Calendar.current.isDateInToday(date) {
            f.dateFormat = "h:mm a"
            return "today at " + f.string(from: date)
        }
        f.dateFormat = "EEEE, MMMM d, yyyy 'at' h:mm a"
        return f.string(from: date)
    }

    static func iso(_ date: Date) -> String {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
        return f.string(from: date)
    }
}
