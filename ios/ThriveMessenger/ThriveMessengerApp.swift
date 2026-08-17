import SwiftUI

@main
struct ThriveMessengerApp: App {
    @StateObject private var model = MessengerModel()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(model)
        }
    }
}
