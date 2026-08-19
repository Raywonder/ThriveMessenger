import SwiftUI

@main
struct ThriveMessengerApp: App {
    @State private var session = ThriveSession()

    var body: some Scene {
        WindowGroup {
            RootView(session: session)
        }
    }
}

struct RootView: View {
    @Bindable var session: ThriveSession

    var body: some View {
        if session.isSignedIn {
            TabView {
                NavigationStack { ContactsView(session: session) }
                    .tabItem { Label("Contacts", systemImage: "person.2") }
                NavigationStack { GroupsView(session: session) }
                    .tabItem { Label("Groups", systemImage: "bubble.left.and.bubble.right") }
                NavigationStack { SettingsView(session: session) }
                    .tabItem { Label("Settings", systemImage: "gear") }
            }
        } else {
            LoginView(session: session)
        }
    }
}
