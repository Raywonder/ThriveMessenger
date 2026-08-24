import Foundation
import Security

enum PasskeyStore {
    private static let service = "fm.tappedin.thrive.passkey"

    static func save(_ token: String, username: String, server: ServerConfiguration) -> Bool {
        let account = "\(username)@\(server.host):\(server.port)"
        let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: service, kSecAttrAccount as String: account]
        let data = Data(token.utf8)
        SecItemDelete(query as CFDictionary)
        var item = query
        item[kSecValueData as String] = data
        return SecItemAdd(item as CFDictionary, nil) == errSecSuccess
    }

    static func load(username: String, server: ServerConfiguration) -> String? {
        let account = "\(username)@\(server.host):\(server.port)"
        let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: service, kSecAttrAccount as String: account, kSecReturnData as String: true, kSecMatchLimit as String: kSecMatchLimitOne]
        var result: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &result) == errSecSuccess,
              let data = result as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }
}

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

struct Group: Codable, Identifiable, Hashable {
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
