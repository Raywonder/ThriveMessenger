import SwiftUI

@main
struct ThriveApp: App {
    @State private var model = AppModel()
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(model)
                .onAppear { model.trySavedSignIn() }
        }
        .onChange(of: scenePhase) { _, phase in
            if phase == .active { model.appBecameActive() }
        }
    }
}

struct RootView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        switch model.phase {
        case .signedOut, .signingIn: SignInView()
        case .online, .reconnecting: MainView()
        }
    }
}

struct SignInView: View {
    @Environment(AppModel.self) private var model
    @State private var user = ""
    @State private var password = ""
    @State private var remember = true
    @State private var showForgotPassword = false
    @FocusState private var focus: Field?
    enum Field { case user, password }

    var body: some View {
        NavigationStack {
            Form {
                Section("Server") {
                    Text(model.server.name).accessibilityLabel("Server: \(model.server.name)")
                }
                Section {
                    TextField("Username", text: $user)
                        .textContentType(.username).textInputAutocapitalization(.never).autocorrectionDisabled()
                        .focused($focus, equals: .user)
                    SecureField("Password", text: $password)
                        .textContentType(.password).focused($focus, equals: .password)
                        .onSubmit(signIn)
                    Toggle("Stay signed in", isOn: $remember)
                }
                if !model.signInError.isEmpty {
                    Section { Text(model.signInError).foregroundStyle(.red) }
                }
                Section {
                    Button(model.phase == .signingIn ? "Signing in…" : "Sign in", action: signIn)
                        .disabled(user.isEmpty || password.isEmpty || model.phase == .signingIn)
                    Button("Forgot password?") { showForgotPassword = true }
                }
            }
            .navigationTitle("Thrive")
            .onAppear { user = model.username; focus = user.isEmpty ? .user : .password }
            .sheet(isPresented: $showForgotPassword) { ForgotPasswordView() }
        }
    }

    private func signIn() {
        guard !user.isEmpty, !password.isEmpty else { return }
        model.signIn(user: user, password: password, remember: remember)
    }
}

struct MainView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        TabView {
            NavigationStack { ContactsView() }
                .tabItem { Label("Chats", systemImage: "bubble.left.and.bubble.right") }
            RoomsView()
                .tabItem { Label("Rooms", systemImage: "person.3") }
            NavigationStack { SettingsView() }
                .tabItem { Label("Settings", systemImage: "gear") }
        }
        .safeAreaInset(edge: .top) {
            if model.phase == .reconnecting {
                Text("Reconnecting. Thrive keeps trying in the background.")
                    .font(.footnote).frame(maxWidth: .infinity).padding(6).background(.yellow.opacity(0.3))
                    .accessibilityAddTraits(.isStaticText)
            }
        }
    }
}

struct ContactsView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        List(model.contacts) { c in
            NavigationLink(value: ConversationKind.direct(c.user)) {
                VStack(alignment: .leading) {
                    Text(c.user).font(.headline)
                    Text(c.online ? (c.statusText.isEmpty ? "Online" : c.statusText) : "Offline").font(.subheadline).foregroundStyle(.secondary)
                }
                .accessibilityElement(children: .ignore)
                .accessibilityLabel("\(c.user), \(c.online ? "online" : "offline")\(c.statusText.isEmpty ? "" : ", \(c.statusText)")\(c.unread > 0 ? ", \(c.unread) unread" : "")")
            }
        }
        .overlay { if model.contacts.isEmpty { ContentUnavailableView("No contacts yet", systemImage: "person.crop.circle.badge.plus") } }
        .navigationTitle("Chats")
        .navigationDestination(for: ConversationKind.self) { kind in ChatView(kind: kind) }
    }
}
