import AudioToolbox
import Foundation
import Network
import Observation
import UIKit

@MainActor
@Observable
final class Conversation: Identifiable {
    let kind: ConversationKind
    var id: String { kind.key }
    var messages: [ChatMessage] = []
    var hasMore = false
    var loaded = false
    var loading = false
    var typing: [String] = []
    var room: RoomSummary?
    var members: [RoomMember] = []
    var bans: [[String: Any]] = []
    var announcedAllRead: String?
    var lastReadSentAt: Double = 0

    init(kind: ConversationKind) { self.kind = kind }

    var title: String {
        switch kind {
        case .direct(let u): return u
        case .room: return room?.name ?? "Room"
        }
    }
    func index(of id: String) -> Int? { messages.firstIndex { $0.id == id } }
}

/// Everything the app knows about the signed-in server, and the connection to it.
/// Reconnect rules match desktop 15.17: heartbeat after 20 s of silence, 45 s of silence means the connection is dead,
/// retry forever with backoff capped at 30 s, and try again at once when the network changes or the app comes forward.
@MainActor
@Observable
final class AppModel {
    enum Phase: Equatable { case signedOut, signingIn, online, reconnecting }

    var phase: Phase = .signedOut
    var signInError = ""
    var server = ServerEntry.tappedIn
    var servers: [ServerEntry] = [ServerEntry.tappedIn]
    var username = ""
    var isAdmin = false
    var contacts: [Contact] = []
    var rooms: [RoomSummary] = []
    var conversations: [String: Conversation] = [:]
    var linkTitles: [String: String] = [:]
    var openConversation: String?

    // Settings (the same names as desktop where they exist)
    var sendReadReceipts: Bool { didSet { defaults.set(sendReadReceipts, forKey: "send_read_receipts") } }
    var fetchLinkTitles: Bool { didSet { defaults.set(fetchLinkTitles, forKey: "fetch_link_titles") } }
    var linkOpenInApp: Bool { didSet { defaults.set(linkOpenInApp, forKey: "link_open_in_app") } }
    var roomAlerts: String { didSet { defaults.set(roomAlerts, forKey: "room_alerts") } }
    /// A new message in the conversation on screen: "read" it aloud, play a "sound", or "none" (desktop 15.19 parity).
    var openChatAlert: String { didSet { defaults.set(openChatAlert, forKey: "open_chat_new_message") } }
    /// A direct message in another conversation: "read" it aloud, say only the "name", or "none" (unread count only).
    var otherChatAlert: String { didSet { defaults.set(otherChatAlert, forKey: "other_chat_new_message") } }
    /// Hardware keyboard only: Return sends the message. Shift+Return or Option+Return always makes a new line;
    /// Command+Return always sends even when this is off. Ignored with no hardware keyboard connected.
    var enterKeySendsMessage: Bool { didSet { defaults.set(enterKeySendsMessage, forKey: "enter_key_sends_message") } }

    private let defaults = UserDefaults.standard
    private var connection: ThriveConnection?
    private var password = ""
    private var loginPending = false
    private var lastActivity = Date()
    private var lastPing = Date.distantPast
    private var probed = false
    private var heartbeat: Timer?
    private var attempt = 0
    private var retryTask: Task<Void, Never>?
    private var saidReconnecting = false
    private let pathMonitor = NWPathMonitor()
    private var titlesAsked = Set<String>()
    private var pendingReaction: (String, String, Bool)?
    var voicePlayer = VoicePlayer()
    private var pendingVoice: String?
    private var pendingVoiceLabel = "Voice message"
    /// Feature switches the server reports in `feature_caps`; actions that need one stay hidden until it says so.
    var featureCaps: [String: FeatureCap] = [:]
    /// Set by the contact-row "Voice message" action: the chat opens and starts recording straight away.
    var startRecordingIn: String?

    init() {
        sendReadReceipts = defaults.object(forKey: "send_read_receipts") as? Bool ?? true
        fetchLinkTitles = defaults.object(forKey: "fetch_link_titles") as? Bool ?? true
        linkOpenInApp = defaults.object(forKey: "link_open_in_app") as? Bool ?? true
        roomAlerts = defaults.string(forKey: "room_alerts") ?? "mentions"
        openChatAlert = defaults.string(forKey: "open_chat_new_message") ?? "read"
        otherChatAlert = defaults.string(forKey: "other_chat_new_message") ?? "read"
        enterKeySendsMessage = defaults.object(forKey: "enter_key_sends_message") as? Bool ?? true
        username = defaults.string(forKey: "username") ?? ""
        if ProcessInfo.processInfo.arguments.contains("--reset-for-tests") {
            Keychain.delete(server: server.id, user: username)
            username = ""
        }
        pathMonitor.pathUpdateHandler = { [weak self] path in
            guard path.status == .satisfied else { return }
            Task { @MainActor in self?.networkChanged() }
        }
        pathMonitor.start(queue: DispatchQueue(label: "fm.tappedin.thrive.path"))
    }

    // MARK: sign-in and connection

    func trySavedSignIn() {
        guard phase == .signedOut, !username.isEmpty, let saved = Keychain.password(server: server.id, user: username) else { return }
        signIn(user: username, password: saved, remember: true)
    }

    func signIn(user: String, password: String, remember: Bool) {
        username = user.trimmingCharacters(in: .whitespaces)
        self.password = password
        defaults.set(username, forKey: "username")
        if remember { Keychain.save(password: password, server: server.id, user: username) }
        signInError = ""
        phase = .signingIn
        connect()
    }

    func signOut() {
        retryTask?.cancel()
        heartbeat?.invalidate()
        connection?.send(["action": "logout"])
        connection?.stop()
        connection = nil
        Keychain.delete(server: server.id, user: username)
        password = ""
        phase = .signedOut
        contacts = []; rooms = []; conversations = [:]
    }

    private func connect() {
        connection?.stop()
        let c = ThriveConnection(host: server.host, port: server.port)
        connection = c
        c.onLine = { [weak self] obj in Task { @MainActor in self?.handle(obj) } }
        c.onState = { [weak self, weak c] state in
            Task { @MainActor in
                guard let self, let c, c === self.connection else { return }
                switch state {
                case .ready: self.sendLogin()
                case .failed(let why): self.connectionLost(why)
                default: break
                }
            }
        }
        c.start()
    }

    private func sendLogin() {
        loginPending = true
        let device = UIDevice.current
        connection?.send(["action": "login", "user": username, "pass": password,
                          "device_id": device.identifierForVendor?.uuidString ?? UUID().uuidString,
                          "device_name": device.name, "platform": "iOS \(device.systemVersion)",
                          "client_version": "ios-" + (Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "15.17"),
                          "session_duration": "month"])
    }

    private func loginResult(_ obj: [String: Any]) {
        loginPending = false
        if obj["status"] as? String == "ok" {
            isAdmin = obj["is_admin"] as? Bool ?? false
            let wasReconnecting = phase == .reconnecting
            phase = .online
            attempt = 0
            lastActivity = Date()
            startHeartbeat()
            if wasReconnecting {
                saidReconnecting = false
                Announce.say("Reconnected")
                resyncOpen()
            }
            send(["action": "get_feature_caps"])
            send(["action": "group_room_list"])
        } else {
            let reason = obj["reason"] as? String ?? "Sign-in failed."
            connection?.stop()
            connection = nil
            if phase == .reconnecting && !reason.lowercased().contains("invalid") {
                scheduleRetry()
            } else {
                phase = .signedOut
                signInError = reason
                Announce.say(reason, important: true)
            }
        }
    }

    private func connectionLost(_ why: String) {
        if loginPending && phase == .signingIn {
            loginPending = false
            phase = .signedOut
            signInError = "Couldn't reach the server: \(why)"
            Announce.say(signInError, important: true)
            return
        }
        guard phase == .online || phase == .reconnecting else { return }
        heartbeat?.invalidate()
        connection?.stop()
        connection = nil
        if phase == .online {
            phase = .reconnecting
            if !saidReconnecting { saidReconnecting = true; Announce.say("Reconnecting") }
        }
        scheduleRetry()
    }

    private func scheduleRetry(now: Bool = false) {
        retryTask?.cancel()
        attempt += 1
        let delay = now ? 0.5 : min(30.0, pow(2.0, Double(min(attempt, 5)))) * Double.random(in: 0.8...1.1)
        retryTask = Task { [weak self] in
            try? await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
            guard !Task.isCancelled, let self, self.phase == .reconnecting else { return }
            self.connect()
        }
    }

    private func networkChanged() {
        if phase == .reconnecting { scheduleRetry(now: true) }
        else if phase == .online { probeNow() }
    }

    /// The app came to the foreground: the old connection may be dead after sleep.
    func appBecameActive() {
        switch phase {
        case .reconnecting: scheduleRetry(now: true)
        case .online: probeNow()
        case .signedOut: trySavedSignIn()
        default: break
        }
    }

    private func probeNow() {
        send(["action": "ping", "t": Date().timeIntervalSince1970])
        let sentAt = Date()
        Task { [weak self] in
            try? await Task.sleep(nanoseconds: 12_000_000_000)
            guard let self, self.phase == .online, self.lastActivity < sentAt else { return }
            self.connectionLost("no answer after waking")
        }
    }

    private func startHeartbeat() {
        heartbeat?.invalidate()
        probed = false
        heartbeat = Timer.scheduledTimer(withTimeInterval: 5, repeats: true) { [weak self] _ in
            Task { @MainActor in self?.beat() }
        }
    }

    private func beat() {
        guard phase == .online else { return }
        let idle = Date().timeIntervalSince(lastActivity)
        if idle >= 45 { connectionLost("silent for \(Int(idle)) seconds"); return }
        if idle >= 25 && !probed { send(["action": "get_feature_caps"]); probed = true }
        if idle < 25 { probed = false }
        if idle >= 20 && Date().timeIntervalSince(lastPing) >= 20 {
            send(["action": "ping", "t": Date().timeIntervalSince1970]); lastPing = Date()
        }
    }

    func send(_ payload: [String: Any]) {
        connection?.send(payload)
    }

    private func resyncOpen() {
        for conv in conversations.values where conv.loaded {
            switch conv.kind {
            case .direct(let u): send(["action": "history_request", "with": u, "limit": 200, "request_id": UUID().uuidString])
            case .room(let id): send(["action": "group_room_open", "room_id": id, "limit": 200])
            }
        }
        send(["action": "group_room_list"])
    }

    // MARK: conversations

    func conversation(_ kind: ConversationKind) -> Conversation {
        if let c = conversations[kind.key] { return c }
        let c = Conversation(kind: kind)
        conversations[kind.key] = c
        return c
    }

    func open(_ kind: ConversationKind) -> Conversation {
        let c = conversation(kind)
        openConversation = kind.key
        if !c.loaded && !c.loading {
            c.loading = true
            switch kind {
            case .direct(let u):
                send(["action": "history_request", "with": u, "limit": 200, "tz_offset": TimeZone.current.secondsFromGMT() / 60,
                      "request_id": UUID().uuidString])
                if let i = contacts.firstIndex(where: { $0.user.lowercased() == u.lowercased() }) { contacts[i].unread = 0 }
            case .room(let id):
                send(["action": "group_room_open", "room_id": id, "limit": 200])
            }
        }
        return c
    }

    func loadEarlier(_ c: Conversation) {
        guard c.hasMore, !c.loading else { Announce.say("No earlier messages"); return }
        c.loading = true
        switch c.kind {
        case .direct(let u):
            if let seq = c.messages.compactMap({ $0.seq }).min() {
                send(["action": "history_request", "with": u, "limit": 200, "before": seq, "request_id": UUID().uuidString])
            }
        case .room(let id):
            if let t = c.messages.compactMap({ $0.sentAt }).min() {
                send(["action": "group_room_history", "room_id": id, "limit": 200, "before": t])
            }
        }
    }

    func sendText(_ text: String, in c: Conversation) {
        let body = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !body.isEmpty else { return }
        let cid = UUID().uuidString.replacingOccurrences(of: "-", with: "")
        var msg = ChatMessage(id: cid, clientID: cid, serverKnown: false, sender: username, text: body, time: Date())
        if phase != .online { msg.queued = true }
        c.messages.append(msg)
        switch c.kind {
        case .direct(let u):
            send(["action": "msg", "to": u, "from": username, "msg": body, "time": ThriveTime.iso(Date()), "client_id": cid])
        case .room(let id):
            send(["action": "group_room_message", "room_id": id, "body": body, "client_id": cid])
        }
        requestTitles(for: body)
    }

    func sendVoice(wav: Data, seconds: Double, in c: Conversation) {
        let cid = UUID().uuidString.replacingOccurrences(of: "-", with: "")
        let voice: [String: Any] = ["b64": wav.base64EncodedString(), "mime": "audio/wav", "voicemail": false]
        var msg = ChatMessage(id: cid, clientID: cid, serverKnown: false, sender: username,
                              text: "Voice message (\(Int(seconds)) seconds)", time: Date())
        msg.voice = VoiceInfo(duration: seconds, stored: false, serverID: "")
        c.messages.append(msg)
        switch c.kind {
        case .direct(let u):
            send(["action": "msg", "to": u, "from": username, "msg": "", "time": ThriveTime.iso(Date()), "client_id": cid, "voice": voice])
        case .room(let id):
            send(["action": "group_room_message", "room_id": id, "client_id": cid, "voice": voice])
        }
        Announce.say("Voice message sent")
    }

    /// Play, pause or resume one voice message. The single entry point: the VoiceOver default action on the
    /// message row and the hardware Return key both call this, so there is only ever one playback path.
    func toggleVoice(_ m: ChatMessage, in c: Conversation) {
        guard let v = m.voice, !v.serverID.isEmpty else { Announce.say("This voice message isn't available yet."); return }
        let label = "Voice message from \(m.sender.lowercased() == username.lowercased() ? "you" : m.sender)"
        if let data = voicePlayer.cached(v.serverID) {
            voicePlayer.toggle(id: v.serverID, data: data, label: label)
            return
        }
        guard pendingVoice != v.serverID else { return }   // already fetching it; don't ask twice
        pendingVoice = v.serverID
        pendingVoiceLabel = label
        Announce.say("Getting the voice message")
        switch c.kind {
        case .direct: send(["action": "voice_fetch", "id": v.serverID])
        case .room(let id): send(["action": "group_room_voice_fetch", "room_id": id, "message_id": v.serverID])
        }
    }

    func edit(_ m: ChatMessage, to text: String, in c: Conversation) {
        switch c.kind {
        case .direct: send(["action": "msg_edit", "id": m.id, "msg": text])
        case .room(let id): send(["action": "group_room_edit", "room_id": id, "message_id": m.id, "body": text])
        }
    }

    func delete(_ m: ChatMessage, in c: Conversation) {
        switch c.kind {
        case .direct: send(["action": "msg_delete", "id": m.id])
        case .room(let id): send(["action": "group_room_delete", "room_id": id, "message_id": m.id])
        }
        c.messages.removeAll { $0.id == m.id }
    }

    func canEdit(_ m: ChatMessage, in c: Conversation) -> Bool {
        guard m.serverKnown, !m.isSystem else { return false }
        if m.sender.lowercased() == username.lowercased() { return true }
        switch c.kind {
        case .direct: return isAdmin
        case .room: return (roleRank[c.room?.role ?? ""] ?? -1) >= 2
        }
    }

    func toggleReaction(_ emoji: String, on m: ChatMessage, in c: Conversation) {
        guard m.serverKnown else { Announce.say("You can react once the message has reached the server."); return }
        let mine = m.reactions.first(where: { $0.emoji == emoji })?.users.contains { $0.lowercased() == username.lowercased() } ?? false
        var payload: [String: Any] = ["action": "react", "message_id": m.id, "emoji": emoji, "on": !mine, "scope": "dm"]
        if case .room(let id) = c.kind { payload["scope"] = "room"; payload["room_id"] = id }
        pendingReaction = (m.id, emoji, !mine)
        send(payload)
    }

    /// Mark as read up to this message (read receipts), the way desktop does after a message stays selected.
    func markRead(upTo m: ChatMessage, in c: Conversation) {
        guard sendReadReceipts, let idx = c.index(of: m.id) else { return }
        switch c.kind {
        case .direct:
            var ids: [String] = []
            for i in 0...idx where !c.messages[i].readSent && c.messages[i].serverKnown
                && c.messages[i].sender.lowercased() != username.lowercased() {
                c.messages[i].readSent = true
                ids.append(c.messages[i].id)
            }
            if !ids.isEmpty { send(["action": "msg_read", "ids": ids]) }
        case .room(let id):
            guard let t = c.messages[0...idx].last(where: { $0.sender.lowercased() != username.lowercased() && $0.sentAt != nil }),
                  let sentAt = t.sentAt, sentAt > c.lastReadSentAt else { return }
            c.lastReadSentAt = sentAt
            send(["action": "group_room_read", "room_id": id, "message_id": t.id])
        }
    }

    func requestTitles(for text: String) {
        guard fetchLinkTitles else { return }
        let urls = LinkFinder.find(text).map(\.url).filter { $0.hasPrefix("http") && linkTitles[$0] == nil && !titlesAsked.contains($0) }
        guard !urls.isEmpty else { return }
        titlesAsked.formUnion(urls)
        send(["action": "link_titles", "urls": Array(urls.prefix(25))])
    }

    func statusText(_ m: ChatMessage, in c: Conversation) -> String {
        guard sendReadReceipts, m.sender.lowercased() == username.lowercased(), m.serverKnown else { return m.queued ? "not sent yet" : "" }
        switch c.kind {
        case .direct:
            if let r = m.readAt {
                let f = DateFormatter(); f.dateFormat = "h:mm a"
                return "read \(f.string(from: r))"
            }
            return m.delivered ? "delivered" : "sent"
        case .room:
            guard let sentAt = m.sentAt else { return "sent" }
            let others = c.members.filter { $0.username.lowercased() != m.sender.lowercased() }
            let n = others.filter { $0.lastReadAt >= sentAt }.count
            if others.isEmpty { return "" }
            if n == 0 { return "sent" }
            return n >= others.count ? "read by everyone" : "read by \(n) of \(others.count)"
        }
    }

    /// What VoiceOver reads for a message: sender, time, text, links, reactions and delivery or read status.
    func spokenLabel(_ m: ChatMessage, in c: Conversation) -> String {
        let who = m.sender.lowercased() == username.lowercased() ? "You" : m.sender
        var parts = [m.isSystem ? m.text : "\(who), \(ThriveTime.spoken(m.time)), \(m.deleted ? "message deleted" : m.text)"]
        if m.edited && !m.deleted { parts.append("edited") }
        let links = LinkFinder.find(m.text).count
        if links > 0 { parts.append("\(links) link\(links == 1 ? "" : "s")") }
        for g in m.reactions where !g.users.isEmpty {
            let names = g.users.map { $0.lowercased() == username.lowercased() ? "you" : $0 }
            parts.append("\(Reactions.name(g.emoji)) from \(names.joined(separator: " and "))")
        }
        let status = statusText(m, in: c)
        if !status.isEmpty { parts.append(status) }
        return parts.joined(separator: ", ")
    }

    // MARK: server events

    private func announceInOpenChat(_ text: String) {
        switch openChatAlert {
        case "sound": AudioServicesPlaySystemSound(1003)
        case "none": break
        default: Announce.say(text)
        }
    }

    private func handle(_ obj: [String: Any]) {
        lastActivity = Date()
        if loginPending, obj["status"] != nil { loginResult(obj); return }
        guard let act = obj["action"] as? String else { return }
        switch act {
        case "contact_list":
            contacts = (obj["contacts"] as? [[String: Any]] ?? []).map {
                Contact(user: $0["user"] as? String ?? "", online: $0["online"] as? Bool ?? false, statusText: $0["status_text"] as? String ?? "",
                        isAdmin: $0["is_admin"] as? Bool ?? false, blocked: ($0["blocked"] as? Int ?? 0) != 0)
            }.sorted { ($0.online ? 0 : 1, $0.user.lowercased()) < ($1.online ? 0 : 1, $1.user.lowercased()) }
        case "contact_status":
            if let u = obj["user"] as? String, let i = contacts.firstIndex(where: { $0.user.lowercased() == u.lowercased() }) {
                contacts[i].online = obj["online"] as? Bool ?? contacts[i].online
                contacts[i].statusText = obj["status_text"] as? String ?? contacts[i].statusText
            }
        case "feature_caps":
            if let a = obj["is_admin"] as? Bool { isAdmin = a }
            if let caps = obj["caps"] as? [String: [String: Any]] {
                featureCaps = caps.mapValues { FeatureCap($0) }
            }
        case "msg": incomingDirect(obj)
        case "msg_sent":
            guard let to = obj["to"] as? String, let cid = obj["client_id"] as? String, let id = obj["id"] as? String else { return }
            let c = conversation(.direct(to))
            if let i = c.messages.firstIndex(where: { $0.clientID == cid }) {
                c.messages[i].id = id; c.messages[i].serverKnown = true; c.messages[i].queued = false
                c.messages[i].delivered = obj["delivered"] as? Bool ?? false
                // DM voice messages are sent with an empty serverID (not known until this ack); without this,
                // tapping your own just-sent voice message says "not available yet" forever.
                if c.messages[i].voice != nil { c.messages[i].voice?.serverID = id }
            }
        case "msg_failed":
            Announce.say(obj["reason"] as? String ?? "A message couldn't be sent.", important: true)
        case "history": applyHistory(obj)
        case "msg_read_update":
            guard let by = obj["by"] as? String else { return }
            let c = conversation(.direct(by))
            let ids = Set(obj["ids"] as? [String] ?? [])
            let when = ThriveTime.parse(obj["read_at"])
            let newestOwn = c.messages.last { $0.sender.lowercased() == username.lowercased() && $0.serverKnown }?.id
            var newestChanged = false
            for i in c.messages.indices where ids.contains(c.messages[i].id) && c.messages[i].readAt == nil {
                c.messages[i].readAt = when; c.messages[i].delivered = true
                if c.messages[i].id == newestOwn { newestChanged = true }
            }
            if newestChanged && sendReadReceipts { Announce.say("Read by \(by)") }
        case "msg_read_sync":
            let ids = Set(obj["ids"] as? [String] ?? [])
            for c in conversations.values { for i in c.messages.indices where ids.contains(c.messages[i].id) { c.messages[i].readSent = true } }
        case "msg_edited", "msg_deleted":
            let id = obj["id"] as? String ?? ""
            for c in conversations.values {
                guard let i = c.index(of: id) else { continue }
                if act == "msg_edited" { c.messages[i].text = obj["msg"] as? String ?? ""; c.messages[i].edited = true }
                else { c.messages.remove(at: i) }
            }
        case "msg_edit_result", "msg_delete_result":
            if obj["ok"] as? Bool == false { Announce.say(obj["reason"] as? String ?? "That didn't work.", important: true) }
            else { Announce.say(act == "msg_edit_result" ? "Message edited" : "Deleted for everyone") }
        case "reaction_update": applyReaction(obj)
        case "reaction_failed": Announce.say(obj["reason"] as? String ?? "Reaction failed.")
        case "link_titles":
            for (u, t) in obj["titles"] as? [String: String] ?? [:] where !t.isEmpty { linkTitles[u] = t }
        case "voice_data", "group_room_voice_data":
            let id = (obj["id"] ?? obj["message_id"]) as? String
            guard id == pendingVoice else { return }
            pendingVoice = nil
            if obj["ok"] as? Bool == true, let b64 = obj["b64"] as? String, let data = Data(base64Encoded: b64) {
                voicePlayer.store(id ?? "", data)
                voicePlayer.play(id: id ?? "", data: data, label: pendingVoiceLabel)
            } else { Announce.say("This voice message isn't available any more.") }
        case "typing":
            guard let from = obj["from"] as? String else { return }
            let c = conversation(.direct(from))
            c.typing = (obj["typing"] as? Bool ?? false) ? [from] : []
        case "pong": break
        case "voice_call_result":
            if obj["ok"] as? Bool == false {
                Announce.say(obj["reason"] as? String ?? "That call couldn't be placed.", important: true)
            } else if let ev = obj["event"] as? String {
                Announce.say(ev == "ringing" ? "Ringing" : ev.replacingOccurrences(of: "_", with: " "))
            }
        case "voice_call_request":
            Announce.say("Incoming call from \(obj["from"] as? String ?? "someone")", important: true)
        case "voice_call_event":
            let ev = obj["event"] as? String ?? ""
            let who = (obj["by"] ?? obj["from"]) as? String ?? ""
            switch ev {
            case "accepted": Announce.say("\(who) answered")
            case "declined": Announce.say("\(who) declined the call")
            case "ended": Announce.say("Call ended")
            default: if !ev.isEmpty { Announce.say(ev.replacingOccurrences(of: "_", with: " ")) }
            }
        case "feature_denied":
            Announce.say(obj["reason"] as? String ?? "That isn't switched on for your account.", important: true)
        default:
            if act.hasPrefix("group_room_") { handleRoom(act, obj) }
        }
    }

    private func dmMessage(_ item: [String: Any]) -> ChatMessage {
        let me = username.lowercased()
        let from = item["from"] as? String ?? ""
        var m = ChatMessage(id: item["id"] as? String ?? UUID().uuidString, clientID: nil, serverKnown: !(item["id"] as? String ?? "h").hasPrefix("h"),
                            sender: from.lowercased() == me ? username : from, text: item["msg"] as? String ?? "", time: ThriveTime.parse(item["time"]))
        m.edited = item["edited"] as? Bool ?? false
        m.delivered = item["delivered"] as? Bool ?? false
        if let r = item["read_at"] as? String { m.readAt = ThriveTime.parse(r); m.readSent = true }
        m.seq = item["seq"] as? Int
        m.reactions = (item["reactions"] as? [[String: Any]] ?? []).map { ReactionGroup(emoji: $0["emoji"] as? String ?? "", users: $0["users"] as? [String] ?? []) }
        if let v = item["voice"] as? [String: Any] {
            m.voice = VoiceInfo(duration: (v["duration"] as? Double) ?? Double(v["duration"] as? Int ?? 0), stored: v["stored"] as? Bool ?? true,
                                serverID: item["id"] as? String ?? "")
            if let b64 = v["b64"] as? String, let data = Data(base64Encoded: b64) { voicePlayer.store(m.id, data) }
        }
        return m
    }

    private func incomingDirect(_ obj: [String: Any]) {
        let me = username.lowercased()
        let from = obj["from"] as? String ?? ""
        let to = obj["to"] as? String ?? ""
        let other = from.lowercased() == me ? to : from
        guard !other.isEmpty else { return }
        let c = conversation(.direct(other))
        let m = dmMessage(obj)
        if c.index(of: m.id) != nil { return }
        c.messages.append(m)
        requestTitles(for: m.text)
        if from.lowercased() != me {
            let spoken = "\(from): \(m.voice != nil ? "voice message" : m.text)"
            if openConversation == c.id {
                // Used to arrive silently in the chat on screen, so people missed it.
                announceInOpenChat(spoken)
                if UIApplication.shared.applicationState == .active { markRead(upTo: m, in: c) }
            } else if let i = contacts.firstIndex(where: { $0.user.lowercased() == other.lowercased() }) {
                contacts[i].unread += 1
                switch otherChatAlert {
                case "name": Announce.say("New message from \(from)")
                case "none": break
                default: Announce.say(spoken)
                }
            }
        }
    }

    private func applyHistory(_ obj: [String: Any]) {
        guard let with = obj["with"] as? String else { return }
        let c = conversation(.direct(with))
        c.loading = false
        c.loaded = true
        c.hasMore = obj["has_more"] as? Bool ?? false
        let known = Set(c.messages.map(\.id))
        let items = (obj["messages"] as? [[String: Any]] ?? []).map(dmMessage).filter { !known.contains($0.id) }
        c.messages = (c.messages + items).sorted { $0.time < $1.time }
        items.forEach { requestTitles(for: $0.text) }
        if obj["before"] != nil { Announce.say(items.isEmpty ? "No earlier messages" : "Loaded \(items.count) earlier messages") }
    }

    private func applyReaction(_ obj: [String: Any]) {
        let id = obj["message_id"] as? String ?? ""
        let groups = (obj["reactions"] as? [[String: Any]] ?? []).map { ReactionGroup(emoji: $0["emoji"] as? String ?? "", users: $0["users"] as? [String] ?? []) }
        let who = obj["username"] as? String ?? ""
        let emoji = obj["emoji"] as? String ?? ""
        let on = obj["on"] as? Bool ?? true
        for c in conversations.values {
            guard let i = c.index(of: id) else { continue }
            c.messages[i].reactions = groups
            if who.lowercased() == username.lowercased() {
                if let p = pendingReaction, p.0 == id, p.1 == emoji, p.2 == on {
                    pendingReaction = nil
                    Announce.say("\(Reactions.name(emoji)) \(on ? "added" : "removed")")
                }
            } else if on {
                let mine = c.messages[i].sender.lowercased() == username.lowercased()
                if openConversation == c.id || mine {
                    Announce.say("\(who) reacted \(Reactions.name(emoji))\(mine ? " to your message" : "")")
                }
            }
        }
    }

    // MARK: rooms

    func roomMessage(_ item: [String: Any]) -> ChatMessage {
        let sentAt = (item["sent_at"] as? Double) ?? Double(item["sent_at"] as? Int ?? 0)
        let id = item["message_id"] as? String ?? UUID().uuidString
        var m = ChatMessage(id: id, clientID: item["client_id"] as? String, serverKnown: true, sender: item["sender"] as? String ?? "",
                            text: item["body"] as? String ?? "", time: Date(timeIntervalSince1970: sentAt))
        m.sentAt = sentAt
        m.edited = item["edited_at"] != nil && !(item["edited_at"] is NSNull)
        m.deleted = item["deleted"] as? Bool ?? false
        m.mentions = item["mentions"] as? [String] ?? []
        m.reactions = (item["reactions"] as? [[String: Any]] ?? []).map { ReactionGroup(emoji: $0["emoji"] as? String ?? "", users: $0["users"] as? [String] ?? []) }
        if item["kind"] as? String == "file" { m.fileName = item["filename"] as? String; m.text = "shared a file: \(m.fileName ?? "")" }
        if item["kind"] as? String == "voice", let v = item["voice"] as? [String: Any] {
            m.voice = VoiceInfo(duration: (v["duration"] as? Double) ?? 0, stored: v["stored"] as? Bool ?? false, serverID: id)
        }
        if m.sender.lowercased() == username.lowercased() { m.readSent = true }
        return m
    }

    private func handleRoom(_ act: String, _ obj: [String: Any]) {
        let item = obj["message"] as? [String: Any] ?? [:]
        let roomID = (obj["room_id"] as? String) ?? (item["room_id"] as? String) ?? ((obj["room"] as? [String: Any])?["room_id"] as? String) ?? ""
        switch act {
        case "group_room_list_response":
            rooms = (obj["rooms"] as? [[String: Any]] ?? []).map(RoomSummary.init)
        case "group_room_open_response":
            guard obj["ok"] as? Bool == true, let r = obj["room"] as? [String: Any] else { return }
            let c = conversation(.room(r["room_id"] as? String ?? roomID))
            c.room = RoomSummary(r)
            c.members = (obj["members"] as? [[String: Any]] ?? []).map(member)
            c.bans = obj["bans"] as? [[String: Any]] ?? []
            let first = !c.loaded
            c.loaded = true; c.loading = false
            if first { c.hasMore = obj["has_more"] as? Bool ?? false }
            merge((obj["messages"] as? [[String: Any]] ?? []).map(roomMessage), into: c)
        case "group_room_history_response":
            let c = conversation(.room(roomID))
            c.loading = false
            c.hasMore = obj["has_more"] as? Bool ?? false
            let before = c.messages.count
            merge((obj["messages"] as? [[String: Any]] ?? []).map(roomMessage), into: c)
            let added = c.messages.count - before
            Announce.say(added == 0 ? "No earlier messages" : "Loaded \(added) earlier messages")
        case "group_room_message", "group_room_file":
            let m = roomMessage(item)
            let c = conversation(.room(roomID))
            if let cid = m.clientID, m.sender.lowercased() == username.lowercased(),
               let i = c.messages.firstIndex(where: { $0.clientID == cid && !$0.serverKnown }) {
                var updated = m
                updated.voice = m.voice ?? c.messages[i].voice
                c.messages[i] = updated
                return
            }
            if c.index(of: m.id) != nil { return }
            c.messages.append(m)
            requestTitles(for: m.text)
            guard m.sender.lowercased() != username.lowercased() else { return }
            let mentioned = m.mentions.contains { $0.lowercased() == username.lowercased() }
            let roomName = c.room?.name ?? rooms.first { $0.id == roomID }?.name ?? "a room"
            if openConversation == c.id {
                if mentioned { Announce.say("\(m.sender) mentioned you: \(m.text)", important: true) }
                else { announceInOpenChat("\(m.sender): \(m.text)") }
                if UIApplication.shared.applicationState == .active { markRead(upTo: m, in: c) }
            } else if mentioned {
                Announce.say("\(m.sender) mentioned you in \(roomName): \(m.text)", important: true)
            } else if roomAlerts == "all" {
                Announce.say("\(m.sender) in \(roomName): \(m.text)")
            }
            if openConversation != c.id, let i = rooms.firstIndex(where: { $0.id == roomID }) { rooms[i].unread += 1 }
        case "group_room_read":
            let c = conversation(.room(roomID))
            let who = obj["username"] as? String ?? ""
            let at = (obj["read_at"] as? Double) ?? 0
            if let i = c.members.firstIndex(where: { $0.username.lowercased() == who.lowercased() }) {
                c.members[i].lastReadAt = max(c.members[i].lastReadAt, at)
            }
            if sendReadReceipts, let newest = c.messages.last(where: { $0.sender.lowercased() == username.lowercased() && $0.serverKnown }),
               statusText(newest, in: c) == "read by everyone", c.announcedAllRead != newest.id {
                c.announcedAllRead = newest.id
                Announce.say("Read by everyone in \(c.title)")
            }
        case "group_room_typing":
            let c = conversation(.room(roomID))
            let who = obj["username"] as? String ?? ""
            guard who.lowercased() != username.lowercased() else { return }
            c.typing.removeAll { $0 == who }
            if obj["typing"] as? Bool == true { c.typing.append(who) }
        case "group_room_edited":
            let c = conversation(.room(roomID))
            let m = roomMessage(item)
            if let i = c.index(of: m.id) { c.messages[i].text = m.text; c.messages[i].edited = true; c.messages[i].deleted = m.deleted }
        case "group_room_deleted":
            conversation(.room(roomID)).messages.removeAll { $0.id == obj["message_id"] as? String }
        case "group_room_members":
            let c = conversation(.room(roomID))
            c.members = (obj["members"] as? [[String: Any]] ?? []).map(member)
            if let me = c.members.first(where: { $0.username.lowercased() == username.lowercased() }) { c.room?.role = me.role }
        case "group_room_event":
            roomEvent(obj, roomID: roomID)
            send(["action": "group_room_list"])
        case "group_room_result":
            if obj["ok"] as? Bool == false {
                Announce.say(obj["reason"] as? String ?? "That room action didn't work.", important: true)
            } else {
                if let ev = obj["event"] as? String, let r = obj["room"] as? [String: Any], ["created", "joined"].contains(ev) {
                    Announce.say(ev == "created" ? "Room created" : "Joined \(r["name"] as? String ?? "the room")")
                    NotificationCenter.default.post(name: .thriveOpenRoom, object: r["room_id"] as? String)
                }
                send(["action": "group_room_list"])
            }
        case "group_room_read_status":
            let readers = obj["read_by"] as? [String] ?? []
            Announce.say("Read by \(readers.count) of \(obj["total"] as? Int ?? 0): \(readers.isEmpty ? "nobody yet" : readers.joined(separator: ", "))")
        default: break
        }
    }

    private func member(_ d: [String: Any]) -> RoomMember {
        RoomMember(username: d["username"] as? String ?? "", role: d["role"] as? String ?? "user", roleLabel: d["role_label"] as? String ?? "member",
                   lastReadAt: (d["last_read_at"] as? Double) ?? 0, muted: d["muted"] as? Bool ?? false)
    }

    private func merge(_ items: [ChatMessage], into c: Conversation) {
        let known = Set(c.messages.map(\.id))
        let fresh = items.filter { !known.contains($0.id) }
        c.messages = (c.messages + fresh).sorted { $0.time < $1.time }
        fresh.forEach { requestTitles(for: $0.text) }
    }

    private func roomEvent(_ obj: [String: Any], roomID: String) {
        let ev = obj["event"] as? String ?? ""
        let who = obj["username"] as? String ?? ""
        let by = obj["by"] as? String ?? ""
        if ev == "invited" {
            let name = (obj["room"] as? [String: Any])?["name"] as? String ?? "a room"
            Announce.say("\(by) added you to the room \(name).")
            return
        }
        guard let c = conversations["room:" + roomID] else { return }
        let me = who.lowercased() == username.lowercased()
        let whoText = me ? "You" : who
        let text: String? = [
            "joined": "\(whoText) joined the room.", "left": "\(whoText) left the room.",
            "kicked": "\(whoText) \(me ? "were" : "was") removed from the room by \(by).",
            "banned": "\(whoText) \(me ? "were" : "was") banned from the room by \(by).",
            "muted": "\(whoText) \(me ? "are" : "is") muted by \(by).", "unmuted": "\(whoText) can post again.",
            "topic": "\(by) changed the topic: \((obj["room"] as? [String: Any])?["topic"] as? String ?? "")",
            "deleted": "\(by) deleted this room.",
        ][ev]
        if let r = obj["room"] as? [String: Any] {
            let role = c.room?.role
            c.room = RoomSummary(r)
            if let role { c.room?.role = role }
        }
        if let text {
            var m = ChatMessage(id: UUID().uuidString, clientID: nil, serverKnown: false, sender: "System", text: text, time: Date())
            m.isSystem = true
            c.messages.append(m)
            if openConversation == c.id { Announce.say(text) }
        }
        if ["joined", "left", "kicked", "banned", "unbanned", "muted", "unmuted"].contains(ev), !(me && ["kicked", "banned", "left"].contains(ev)) {
            send(["action": "group_room_open", "room_id": roomID, "limit": 1])
        }
    }

    // MARK: contacts

    func canUseFeature(_ key: String) -> Bool { featureCaps[key]?.canUse ?? false }

    /// Whether an action should appear at all. The server hides features it isn't ready to offer
    /// (`voice_call` ships switched off because call audio needs a media engine), and an action that is
    /// always there but always fails is worse than no action with VoiceOver.
    func featureVisible(_ key: String) -> Bool { featureCaps[key]?.uiVisible ?? false }

    /// Rooms where you are a moderator or above, so "Add to group" only offers rooms the server will accept.
    var roomsICanAddTo: [RoomSummary] { rooms.filter { (roleRank[$0.role] ?? -1) >= 2 } }

    /// Block or unblock a contact. The server stores the flag and sends nothing back, so update the row
    /// here and say what happened — a silent action reads as a broken one with VoiceOver.
    func setBlocked(_ blocked: Bool, user: String) {
        send(["action": blocked ? "block_contact" : "unblock_contact", "to": user])
        if let i = contacts.firstIndex(where: { $0.user.lowercased() == user.lowercased() }) {
            contacts[i].blocked = blocked
        }
        Announce.say(blocked ? "Blocked \(user)" : "Unblocked \(user)")
    }

    /// Remove a contact. Destructive, so the caller confirms first. The server sends no reply here either.
    func deleteContact(_ user: String) {
        send(["action": "delete_contact", "to": user])
        contacts.removeAll { $0.user.lowercased() == user.lowercased() }
        let key = ConversationKind.direct(user).key
        conversations[key] = nil
        if openConversation == key { openConversation = nil }
        Announce.say("Removed \(user) from your contacts")
    }

    func callContact(_ user: String) {
        guard canUseFeature("voice_call") else {
            Announce.say("Calling isn't switched on for your account on this server.", important: true)
            return
        }
        send(["action": "voice_call_request", "to": user, "mode": "voice"])
        Announce.say("Calling \(user)")
    }

    func addContactToRoom(_ user: String, room: RoomSummary) {
        roomAction("group_room_add_member", room: room.id, ["username": user, "role": "user"])
        Announce.say("Adding \(user) to \(room.name)")
    }

    func roomAction(_ action: String, room: String, _ extra: [String: Any] = [:]) {
        var p: [String: Any] = ["action": action, "room_id": room]
        extra.forEach { p[$0.key] = $0.value }
        send(p)
    }
}

extension Notification.Name {
    static let thriveOpenRoom = Notification.Name("thriveOpenRoom")
}
