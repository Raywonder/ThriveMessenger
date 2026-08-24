import Foundation
import Network

@MainActor
final class ThriveClient: ObservableObject {
    @Published private(set) var isConnected = false
    @Published private(set) var username = ""
    @Published private(set) var contacts: [Contact] = []
    @Published private(set) var groups: [Group] = []
    @Published private(set) var groupMessages: [String: [GroupMessage]] = [:]
    @Published var errorMessage: String?
    @Published var passkeyMessage: String?

    private var connection: NWConnection?
    private var buffer = Data()
    private var configuration = ServerConfiguration()
    private var pendingPasskeyToken: String?

    func connect(user: String, password: String, server: ServerConfiguration = .init()) {
        disconnect()
        configuration = server
        username = user
        let params = NWParameters.tcp
        params.defaultProtocolStack.applicationProtocols.insert(NWProtocolTLS.Options(), at: 0)
        let endpoint = NWEndpoint.hostPort(host: NWEndpoint.Host(server.host), port: NWEndpoint.Port(rawValue: server.port)!)
        let connection = NWConnection(to: endpoint, using: params)
        self.connection = connection
        connection.stateUpdateHandler = { [weak self] state in
            Task { @MainActor in
                switch state {
                case .ready:
                    self?.isConnected = true
                    self?.send(["action": "login", "user": user, "pass": password])
                case .failed(let error):
                    self?.isConnected = false
                    self?.errorMessage = error.localizedDescription
                case .cancelled:
                    self?.isConnected = false
                default: break
                }
            }
        }
        connection.start(queue: .global(qos: .userInitiated))
        receive()
    }

    func connectWithSavedPasskey(user: String, server: ServerConfiguration = .init()) {
        guard let token = PasskeyStore.load(username: user, server: server) else {
            errorMessage = "No passkey is saved for this account on this device."
            return
        }
        disconnect()
        configuration = server
        username = user
        let params = NWParameters.tcp
        params.defaultProtocolStack.applicationProtocols.insert(NWProtocolTLS.Options(), at: 0)
        let endpoint = NWEndpoint.hostPort(host: NWEndpoint.Host(server.host), port: NWEndpoint.Port(rawValue: server.port)!)
        let connection = NWConnection(to: endpoint, using: params)
        self.connection = connection
        connection.stateUpdateHandler = { [weak self] state in
            Task { @MainActor in
                switch state {
                case .ready:
                    self?.isConnected = true
                    self?.send(["action": "login_passkey", "user": user, "passkey_token": token])
                case .failed(let error):
                    self?.isConnected = false
                    self?.errorMessage = error.localizedDescription
                case .cancelled:
                    self?.isConnected = false
                default: break
                }
            }
        }
        connection.start(queue: .global(qos: .userInitiated))
        receive()
    }

    func registerPasskey(label: String = "Thrive Messenger iPhone") {
        guard isConnected else {
            errorMessage = "Connect with your password before registering a passkey."
            return
        }
        let token = UUID().uuidString + UUID().uuidString
        pendingPasskeyToken = token
        send(["action": "register_passkey", "label": label, "passkey_token": token])
    }

    func disconnect() {
        connection?.cancel()
        connection = nil
        isConnected = false
    }

    func refreshGroups() { send(["action": "group_list"]) }
    func createGroup(name: String, topic: String) { send(["action": "group_create", "group": name, "topic": topic]) }
    func join(group: String) { send(["action": "group_join", "group": group]) }
    func leave(group: String) { send(["action": "group_leave", "group": group]) }
    func sendMessage(_ text: String, to group: String) { send(["action": "group_msg", "group": group, "msg": text]) }

    private func send(_ object: [String: Any]) {
        guard let connection, JSONSerialization.isValidJSONObject(object),
              let data = try? JSONSerialization.data(withJSONObject: object) else { return }
        connection.send(content: data + Data([10]), completion: .contentProcessed { [weak self] error in
            if let error { Task { @MainActor in self?.errorMessage = error.localizedDescription } }
        })
    }

    private func receive() {
        connection?.receive(minimumIncompleteLength: 1, maximumLength: 256 * 1024) { [weak self] data, _, isComplete, error in
            Task { @MainActor in
                guard let self else { return }
                if let data { self.buffer.append(data); self.consumeLines() }
                if let error { self.errorMessage = error.localizedDescription }
                if !isComplete && error == nil { self.receive() }
            }
        }
    }

    private func consumeLines() {
        while let newline = buffer.firstIndex(of: 10) {
            let line = buffer.prefix(upTo: newline)
            buffer.removeSubrange(...newline)
            guard let object = try? JSONSerialization.jsonObject(with: line) as? [String: Any],
                  let action = object["action"] as? String else { continue }
            switch action {
            case "passkey_register_result":
                if object["ok"] as? Bool == true, let token = pendingPasskeyToken,
                   PasskeyStore.save(token, username: username, server: configuration) {
                    passkeyMessage = "Passkey registered on this device."
                } else {
                    errorMessage = object["reason"] as? String ?? "The passkey could not be saved on this device."
                }
                pendingPasskeyToken = nil
            case "contact_list": contacts = decode(object["contacts"])
            case "group_list_response": groups = decode(object["groups"])
            case "group_msg":
                guard let group = object["group"] as? String,
                      let sender = object["from"] as? String,
                      let text = object["msg"] as? String else { continue }
                groupMessages[group, default: []].append(GroupMessage(sender: sender, text: text, time: object["time"] as? String ?? ""))
            case "group_create_result", "group_join_result": refreshGroups()
            case "group_msg_failed", "group_create_failed": errorMessage = object["reason"] as? String
            default: break
            }
        }
    }

    private func decode<T: Decodable>(_ value: Any?) -> [T] {
        guard JSONSerialization.isValidJSONObject(value as Any),
              let data = try? JSONSerialization.data(withJSONObject: value as Any) else { return [] }
        return (try? JSONDecoder().decode([T].self, from: data)) ?? []
    }
}

@MainActor
final class MessengerModel: ObservableObject {
    let client = ThriveClient()
}
