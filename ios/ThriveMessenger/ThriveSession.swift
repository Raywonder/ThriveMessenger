import Foundation
import Network
import Observation

@MainActor @Observable
final class ThriveSession {
    var host = "im.tappedin.fm"
    var port = 2005
    var username = ""
    var password = ""
    var isSignedIn = false
    var isBusy = false
    var errorMessage: String?
    var contacts: [Contact] = []
    var rooms: [Room] = []
    private var connection: NWConnection?
    private var buffer = Data()

    func signIn() async {
        guard !username.isEmpty, !password.isEmpty else { errorMessage = "Enter a username and password."; return }
        isBusy = true; errorMessage = nil
        do {
            let connection = NWConnection(host: NWEndpoint.Host(host), port: NWEndpoint.Port(rawValue: UInt16(port))!, using: .tls)
            self.connection = connection
            try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
                connection.stateUpdateHandler = { state in
                    switch state {
                    case .ready: continuation.resume()
                    case .failed(let error): continuation.resume(throwing: error)
                    default: break
                    }
                }
                connection.start(queue: .global(qos: .userInitiated))
            }
            receiveNext()
            try await send(["action": "login", "user": username, "pass": password])
        } catch { errorMessage = error.localizedDescription; disconnect() }
        isBusy = false
    }

    func refreshRooms() async { try? await send(["action": "group_room_list"]) }
    func openRoom(_ room: Room) async { try? await send(["action": "group_room_open", "room_id": room.id]) }
    func disconnect() { connection?.cancel(); connection = nil; isSignedIn = false; contacts = []; rooms = [] }

    private func send(_ object: [String: Any]) async throws {
        guard let connection else { throw URLError(.notConnectedToInternet) }
        var data = try JSONSerialization.data(withJSONObject: object); data.append(0x0A)
        try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
            connection.send(content: data, completion: .contentProcessed { error in
                if let error { continuation.resume(throwing: error) } else { continuation.resume() }
            })
        }
    }

    private func receiveNext() {
        connection?.receive(minimumIncompleteLength: 1, maximumLength: 1_048_576) { [weak self] data, _, complete, error in
            guard let self else { return }
            Task { @MainActor in
                if let data { self.buffer.append(data); self.consumeLines() }
                if error != nil || complete { self.disconnect() } else { self.receiveNext() }
            }
        }
    }

    private func consumeLines() {
        while let newline = buffer.firstIndex(of: 0x0A) {
            let line = buffer[..<newline]; buffer.removeSubrange(...newline)
            guard let json = try? JSONSerialization.jsonObject(with: line) as? [String: Any] else { continue }
            handle(json)
        }
    }

    private func handle(_ json: [String: Any]) {
        if let status = json["status"] as? String {
            if status == "ok" { isSignedIn = true; Task { await refreshRooms() } }
            else { errorMessage = json["reason"] as? String ?? "Sign in failed." }
        }
        switch json["action"] as? String {
        case "contact_list": contacts = (json["contacts"] as? [[String: Any]] ?? []).compactMap(Contact.init)
        case "group_room_list_response": rooms = (json["rooms"] as? [[String: Any]] ?? []).compactMap(Room.init)
        default: break
        }
    }
}

struct Contact: Identifiable, Hashable {
    let name: String; let online: Bool; var id: String { name }
    init?(_ json: [String: Any]) { guard let name = json["user"] as? String else { return nil }; self.name = name; online = json["online"] as? Bool ?? false }
}

struct Room: Identifiable, Hashable {
    let id: String; let name: String; let role: String?
    init?(_ json: [String: Any]) { guard let id = json["room_id"] as? String, let name = json["name"] as? String else { return nil }; self.id = id; self.name = name; role = json["role"] as? String }
}
