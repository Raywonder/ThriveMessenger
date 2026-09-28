import Foundation
import Network

/// One TLS connection to a Thrive server: newline-delimited JSON in both directions.
/// Every connect is a fresh DNS lookup, TCP connection and TLS handshake; nothing is reused after a failure.
final class ThriveConnection {
    enum State { case idle, connecting, ready, failed(String) }

    var onLine: (([String: Any]) -> Void)?
    var onState: ((State) -> Void)?

    private let host: String
    private let port: UInt16
    private var conn: NWConnection?
    private var buffer = Data()
    private let queue = DispatchQueue(label: "fm.tappedin.thrive.connection")

    init(host: String, port: UInt16) {
        self.host = host
        self.port = port
    }

    func start() {
        let tcp = NWProtocolTCP.Options()
        tcp.enableKeepalive = true
        tcp.keepaliveIdle = 20
        tcp.keepaliveInterval = 10
        tcp.keepaliveCount = 3
        tcp.connectionTimeout = 10
        let params = NWParameters(tls: NWProtocolTLS.Options(), tcp: tcp)
        let c = NWConnection(host: NWEndpoint.Host(host), port: NWEndpoint.Port(rawValue: port) ?? 2005, using: params)
        conn = c
        c.stateUpdateHandler = { [weak self] state in
            guard let self else { return }
            switch state {
            case .ready:
                self.onState?(.ready)
                self.receive()
            case .failed(let error):
                self.onState?(.failed(error.localizedDescription))
            case .waiting(let error):
                // No route yet (offline, DNS not ready): give up this attempt so the caller's backoff decides.
                self.onState?(.failed(error.localizedDescription))
                c.cancel()
            case .cancelled:
                break
            default:
                break
            }
        }
        onState?(.connecting)
        c.start(queue: queue)
    }

    func stop() {
        conn?.stateUpdateHandler = nil
        conn?.cancel()
        conn = nil
        buffer.removeAll()
    }

    func send(_ payload: [String: Any]) {
        guard let conn, var data = try? JSONSerialization.data(withJSONObject: payload) else { return }
        data.append(0x0A)
        conn.send(content: data, completion: .contentProcessed { [weak self] error in
            if let error { self?.onState?(.failed(error.localizedDescription)) }
        })
    }

    private func receive() {
        conn?.receive(minimumIncompleteLength: 1, maximumLength: 256 * 1024) { [weak self] data, _, isComplete, error in
            guard let self else { return }
            if let data, !data.isEmpty {
                self.buffer.append(data)
                while let nl = self.buffer.firstIndex(of: 0x0A) {
                    let line = self.buffer[self.buffer.startIndex..<nl]
                    self.buffer.removeSubrange(self.buffer.startIndex...nl)
                    if let obj = try? JSONSerialization.jsonObject(with: line) as? [String: Any] {
                        self.onLine?(obj)
                    }
                }
            }
            if let error {
                self.onState?(.failed(error.localizedDescription))
                return
            }
            if isComplete {
                self.onState?(.failed("The server closed the connection."))
                return
            }
            self.receive()
        }
    }
}
