import Foundation

struct ServerConfiguration: Codable, Equatable {
    var host: String = "im.tappedin.fm"
    var port: UInt16 = 2005
}

struct Contact: Codable, Identifiable {
    var user: String
    var online: Bool = false
    var statusText: String = ""
    var isAdmin: Bool = false

    var id: String { user }
    enum CodingKeys: String, CodingKey {
        case user, online, statusText = "status_text", isAdmin = "is_admin"
    }
}

struct Group: Codable, Identifiable {
    var name: String
    var topic: String = ""
    var memberCount: Int = 0
    var isMember: Bool = false

    var id: String { name }
    enum CodingKeys: String, CodingKey {
        case name, topic, memberCount = "member_count", isMember = "is_member"
    }
}

struct GroupMessage: Identifiable {
    let id = UUID()
    let sender: String
    let text: String
    let time: String
}

enum ServerEvent {
    case loggedIn
    case contacts([Contact])
    case groups([Group])
    case groupMessage(GroupMessage)
    case error(String)
}
