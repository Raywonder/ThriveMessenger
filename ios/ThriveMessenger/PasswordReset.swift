import SwiftUI

enum NetworkOutcome {
    case success([String: Any])
    case failure(String)
}

/// One request/response over a fresh, short-lived connection: used for password reset, which happens
/// before sign-in, so it must not disturb AppModel's own connection or signed-in state.
@MainActor
final class PasswordResetClient {
    private var conn: ThriveConnection?

    func send(_ payload: [String: Any], host: String, port: UInt16, timeout: TimeInterval = 10,
              completion: @escaping (NetworkOutcome) -> Void) {
        let c = ThriveConnection(host: host, port: port)
        conn = c
        var done = false
        func finish(_ result: NetworkOutcome) {
            guard !done else { return }
            done = true
            c.stop()
            Task { @MainActor in completion(result) }
        }
        c.onState = { [weak c] state in
            guard let c else { return }
            switch state {
            case .ready: c.send(payload)
            case .failed(let why): finish(.failure(why))
            default: break
            }
        }
        c.onLine = { obj in finish(.success(obj)) }
        c.start()
        DispatchQueue.main.asyncAfter(deadline: .now() + timeout) {
            finish(.failure("That took too long. Check your connection and try again."))
        }
    }
}

struct ForgotPasswordView: View {
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss
    @State private var identifier = ""
    @State private var code = ""
    @State private var newPassword = ""
    @State private var confirmPassword = ""
    @State private var resolvedUser = ""
    @State private var step: Step = .identify
    @State private var busy = false
    @State private var message = ""
    @State private var isError = false
    private let client = PasswordResetClient()

    private enum Step { case identify, reset }

    var body: some View {
        NavigationStack {
            Form {
                if step == .identify {
                    Section {
                        TextField("Email or username", text: $identifier)
                            .textContentType(.username).textInputAutocapitalization(.never).autocorrectionDisabled()
                    } footer: {
                        Text("If that account has an email on file, we'll send a reset code to it.")
                    }
                } else {
                    Section {
                        LabeledContent("Account", value: resolvedUser)
                        TextField("6-digit reset code", text: $code)
                            .keyboardType(.numberPad).textInputAutocapitalization(.never).autocorrectionDisabled()
                        SecureField("New password", text: $newPassword).textContentType(.newPassword)
                        SecureField("Confirm new password", text: $confirmPassword).textContentType(.newPassword)
                    } footer: {
                        Text("The code expires 15 minutes after it's sent.")
                    }
                }
                if !message.isEmpty {
                    Section { Text(message).foregroundStyle(isError ? .red : .primary) }
                }
                Section {
                    Button(primaryLabel, action: primaryAction)
                        .disabled(busy || !canSubmit)
                }
            }
            .navigationTitle("Reset Password")
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } } }
        }
    }

    private var primaryLabel: String {
        busy ? "Please wait…" : (step == .identify ? "Request reset code" : "Change password")
    }

    private var canSubmit: Bool {
        switch step {
        case .identify: return !identifier.trimmingCharacters(in: .whitespaces).isEmpty
        case .reset: return !code.isEmpty && !newPassword.isEmpty && newPassword == confirmPassword
        }
    }

    private func primaryAction() {
        switch step {
        case .identify: requestCode()
        case .reset: resetPassword()
        }
    }

    private func requestCode() {
        busy = true; message = ""; isError = false
        let ident = identifier.trimmingCharacters(in: .whitespaces)
        client.send(["action": "request_reset", "identifier": ident], host: model.server.host, port: model.server.port) { result in
            busy = false
            switch result {
            case .success(let obj) where (obj["status"] as? String) == "ok":
                resolvedUser = obj["user"] as? String ?? ident
                message = "If that account exists, a reset code has been sent to its email."
                isError = false
                step = .reset
                Announce.say(message, important: true)
            case .success(let obj):
                isError = true
                message = obj["reason"] as? String ?? "Something went wrong. Try again."
                Announce.say(message, important: true)
            case .failure(let why):
                isError = true
                message = why
                Announce.say(why, important: true)
            }
        }
    }

    private func resetPassword() {
        guard newPassword == confirmPassword else {
            isError = true; message = "Those passwords don't match."
            Announce.say(message, important: true)
            return
        }
        busy = true; message = ""; isError = false
        let payload: [String: Any] = ["action": "reset_password", "user": resolvedUser, "code": code, "new_pass": newPassword]
        client.send(payload, host: model.server.host, port: model.server.port) { result in
            busy = false
            switch result {
            case .success(let obj) where (obj["status"] as? String) == "ok":
                Announce.say("Password changed. Sign in with your new password.", important: true)
                dismiss()
            case .success(let obj):
                isError = true
                message = obj["reason"] as? String ?? "That code didn't work. Try again."
                Announce.say(message, important: true)
            case .failure(let why):
                isError = true
                message = why
                Announce.say(why, important: true)
            }
        }
    }
}
