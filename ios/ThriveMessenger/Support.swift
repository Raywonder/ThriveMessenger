import Foundation
import Security
import UIKit

/// Passwords live only in the iOS keychain, one item per server and account.
enum Keychain {
    private static let service = "fm.tappedin.thrive"

    static func save(password: String, server: String, user: String) {
        let account = "\(server)|\(user.lowercased())"
        let base: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: service,
                                   kSecAttrAccount as String: account]
        SecItemDelete(base as CFDictionary)
        var add = base
        add[kSecValueData as String] = Data(password.utf8)
        add[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlock
        SecItemAdd(add as CFDictionary, nil)
    }

    static func password(server: String, user: String) -> String? {
        let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: service,
                                    kSecAttrAccount as String: "\(server)|\(user.lowercased())",
                                    kSecReturnData as String: true, kSecMatchLimit as String: kSecMatchLimitOne]
        var out: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &out) == errSecSuccess, let data = out as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    static func delete(server: String, user: String) {
        let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: service,
                                    kSecAttrAccount as String: "\(server)|\(user.lowercased())"]
        SecItemDelete(query as CFDictionary)
    }
}

/// VoiceOver announcements (the iPhone version of the desktop's speak_text).
enum Announce {
    static func say(_ text: String, important: Bool = false) {
        guard !text.isEmpty else { return }
        DispatchQueue.main.async {
            if #available(iOS 17.0, *) {
                var attributed = AttributedString(text)
                attributed.accessibilitySpeechAnnouncementPriority = important ? .high : .default
                AccessibilityNotification.Announcement(attributed).post()
            } else {
                UIAccessibility.post(notification: .announcement, argument: text)
            }
        }
    }
}

/// The same link rules as the desktop client and the server (find_links), so counts and removal agree.
enum LinkFinder {
    struct Link: Hashable { var raw: String; var url: String }
    private static let scheme = try! NSRegularExpression(pattern: #"(?:https?|ipfs|ipns|web3)://[^\s<>()"']+"#, options: [.caseInsensitive])
    private static let bare = try! NSRegularExpression(
        pattern: #"(?<![\w@./:-])((?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+([a-z]{2,63})(?::\d{1,5})?(?:/[^\s<>()"']*)?)"#,
        options: [.caseInsensitive])
    private static let tlds: Set<String> = ["com", "org", "net", "io", "fm", "cc", "app", "dev", "co", "uk", "us", "ca", "edu", "gov", "info",
        "me", "tv", "ai", "software", "blog", "xyz", "de", "au", "nz", "ie", "eu", "biz", "site", "online", "store", "tech", "news", "link",
        "live", "page", "social", "eth", "gg", "ly", "to", "be", "nl", "fr", "es", "it", "in", "jp"]
    private static let trail = CharacterSet(charactersIn: ".,;:!?'\"")

    static func find(_ text: String) -> [Link] {
        let ns = text as NSString
        var found: [(Int, String, String)] = []
        var taken: [NSRange] = []
        for m in scheme.matches(in: text, range: NSRange(location: 0, length: ns.length)) {
            let raw = ns.substring(with: m.range).trimmingCharacters(in: trail)
            if let r = raw.range(of: "://"), !raw[r.upperBound...].isEmpty {
                found.append((m.range.location, raw, raw))
                taken.append(NSRange(location: m.range.location, length: (raw as NSString).length))
            }
        }
        for m in bare.matches(in: text, range: NSRange(location: 0, length: ns.length)) {
            let r1 = m.range(at: 1)
            if taken.contains(where: { NSLocationInRange(r1.location, $0) }) { continue }
            let raw = ns.substring(with: r1).trimmingCharacters(in: trail)
            let tld = ns.substring(with: m.range(at: 2)).lowercased()
            if raw.lowercased().hasPrefix("www.") || tlds.contains(tld) {
                found.append((r1.location, raw, "https://" + raw))
            }
        }
        var seen = Set<String>()
        return found.sorted { $0.0 < $1.0 }.compactMap { item in
            let key = item.2.lowercased()
            if seen.contains(key) { return nil }
            seen.insert(key)
            return Link(raw: item.1, url: item.2)
        }
    }
}

extension String {
    var firstWords: String {
        let words = split(whereSeparator: { $0.isWhitespace })
        return words.prefix(10).joined(separator: " ") + (words.count > 10 ? "…" : "")
    }
}
