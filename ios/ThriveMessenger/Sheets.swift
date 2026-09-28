import SwiftUI

/// Go to: messages with links, from a person, mine, unread, or matching a search. Items read "sender, time, first words".
struct GoToSheet: View {
    let conv: Conversation
    let onPick: (String) -> Void
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss
    @State private var filter = "links"
    @State private var person = ""
    @State private var query = ""

    var body: some View {
        NavigationStack {
            List {
                Picker("Show", selection: $filter) {
                    Text("Messages with links").tag("links")
                    Text("From a person").tag("from")
                    Text("My messages").tag("mine")
                    Text("Unread").tag("unread")
                    Text("Search").tag("search")
                }
                if filter == "from" {
                    Picker("Person", selection: $person) {
                        ForEach(people, id: \.self) { Text($0).tag($0) }
                    }
                }
                if filter == "search" {
                    TextField("Find messages containing", text: $query).autocorrectionDisabled()
                }
                Section("\(results.count) message\(results.count == 1 ? "" : "s")") {
                    ForEach(results) { m in
                        Button("\(m.sender.lowercased() == model.username.lowercased() ? "you" : m.sender), \(ThriveTime.spoken(m.time)), \(m.text.firstWords)") {
                            dismiss(); onPick(m.id)
                        }
                    }
                }
            }
            .navigationTitle("Go to")
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Close") { dismiss() } } }
            .onAppear { person = people.first ?? "" }
        }
    }

    private var people: [String] {
        Array(Set(conv.messages.filter { !$0.isSystem }.map(\.sender))).sorted()
    }

    private var results: [ChatMessage] {
        let me = model.username.lowercased()
        let real = conv.messages.filter { !$0.isSystem }.reversed()
        switch filter {
        case "links": return real.filter { !LinkFinder.find($0.text).isEmpty }
        case "from": return real.filter { $0.sender == person }
        case "mine": return real.filter { $0.sender.lowercased() == me }
        case "unread": return real.filter { $0.sender.lowercased() != me && !$0.readSent }
        default:
            let words = query.lowercased().split(separator: " ")
            guard !words.isEmpty else { return [] }
            return real.filter { m in words.allSatisfy { (m.text + " " + m.sender).lowercased().contains($0) } }
        }
    }
}

/// Links in one message or the whole conversation. Each reads "title, address, sender, time".
struct LinksSheet: View {
    let conv: Conversation
    let messageID: String?
    let onOpen: (String) -> Void
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss

    private struct Item: Identifiable { var id: String; var url: String; var sender: String; var time: Date }

    var body: some View {
        NavigationStack {
            List(items) { item in
                let title = model.linkTitles[item.url]
                Button {
                    dismiss(); onOpen(item.url)
                } label: {
                    VStack(alignment: .leading) {
                        Text(title ?? item.url).font(.headline)
                        if title != nil { Text(item.url).font(.caption) }
                    }
                }
                .accessibilityLabel("\(title.map { "\($0), " } ?? "")\(item.url), \(item.sender), \(ThriveTime.spoken(item.time))")
                .accessibilityAction(named: "Copy link") { UIPasteboard.general.string = item.url; Announce.say("Link copied") }
                .accessibilityAction(named: "Copy title") {
                    UIPasteboard.general.string = title ?? item.url
                    Announce.say(title == nil ? "No title found, copied the link instead" : "Title copied")
                }
                .contextMenu {
                    Button("Copy link") { UIPasteboard.general.string = item.url }
                    Button("Copy title") { UIPasteboard.general.string = title ?? item.url }
                }
            }
            .overlay { if items.isEmpty { ContentUnavailableView("No links", systemImage: "link") } }
            .navigationTitle(messageID == nil ? "Links in this conversation" : "Links in this message")
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Close") { dismiss() } } }
        }
    }

    private var items: [Item] {
        conv.messages.filter { messageID == nil || $0.id == messageID }.reversed().flatMap { m in
            LinkFinder.find(m.text).map { Item(id: m.id + $0.url, url: $0.url, sender: m.sender, time: m.time) }
        }
    }
}

struct ReactionSheet: View {
    let onPick: (String) -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var custom = ""

    var body: some View {
        NavigationStack {
            List {
                ForEach(Reactions.quick, id: \.0) { r in
                    Button("\(r.0) \(r.1)") { dismiss(); onPick(r.0) }.accessibilityLabel(r.1)
                }
                Section("Any emoji") {
                    TextField("Type or pick an emoji", text: $custom)
                    Button("React with it") { dismiss(); onPick(String(custom.prefix(4))) }.disabled(custom.isEmpty)
                }
            }
            .navigationTitle("React")
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Close") { dismiss() } } }
        }
    }
}
