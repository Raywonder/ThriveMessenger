import GameController
import SafariServices
import SwiftUI

/// Composer layout constants.
private enum Composer {
    /// Apple's minimum touch target (Human Interface Guidelines). The composer's mic and send
    /// buttons are bare SF Symbols, so without this their tappable area is only the ~20pt glyph.
    /// Applied to the button *label* with a matching `contentShape`, so the hit rect grows while
    /// the drawn icon stays its natural size.
    static let minHitTarget: CGFloat = 44
}

/// One conversation (direct or room). Every message is a single VoiceOver element that reads
/// "sender, time, text, links, reactions, status", with actions for everything the desktop menu offers.
struct ChatView: View {
    let kind: ConversationKind
    @Environment(AppModel.self) private var model
    @State private var conv: Conversation?
    @State private var draft = ""
    @State private var editing: ChatMessage?
    @State private var sheet: SheetKind?
    @State private var recorder = VoiceRecorder()
    @State private var recording = false
    @State private var backStack: [String] = []
    @AccessibilityFocusState private var focusedMessage: String?
    @FocusState private var composerFocused: Bool
    @State private var scrollTarget: String?

    enum SheetKind: Identifiable {
        case goTo, links(String?), react(String), members, web(URL)
        var id: String {
            switch self {
            case .goTo: return "goto"
            case .links(let m): return "links\(m ?? "")"
            case .react(let m): return "react\(m)"
            case .members: return "members"
            case .web(let u): return u.absoluteString
            }
        }
    }

    var body: some View {
        Group {
            if let conv {
                content(conv)
            } else {
                ProgressView()
            }
        }
        .onAppear {
            conv = model.open(kind)
            if let conv, let last = conv.messages.last { model.markRead(upTo: last, in: conv) }
            // Arrived from the contact row's "Voice message" action: start recording straight away.
            if case .direct(let user) = kind, model.startRecordingIn?.lowercased() == user.lowercased() {
                model.startRecordingIn = nil
                if let conv { Task { await toggleRecording(conv) } }
            }
        }
        .onDisappear { if model.openConversation == kind.key { model.openConversation = nil } }
    }

    @ViewBuilder
    private func content(_ c: Conversation) -> some View {
        VStack(spacing: 0) {
            ScrollViewReader { proxy in
                List {
                    if c.hasMore {
                        Button("Load earlier messages") { model.loadEarlier(c) }
                    }
                    ForEach(c.messages) { m in
                        row(m, c).id(m.id)
                    }
                }
                .listStyle(.plain)
                .scrollDismissesKeyboard(.immediately)
                .onChange(of: c.messages.count) { _, _ in
                    if let last = c.messages.last {
                        if scrollTarget == nil { proxy.scrollTo(last.id, anchor: .bottom) }
                        if last.sender.lowercased() != model.username.lowercased() { model.markRead(upTo: last, in: c) }
                    }
                }
                .onChange(of: scrollTarget) { _, target in
                    guard let target else { return }
                    proxy.scrollTo(target, anchor: .center)
                    focusedMessage = target
                    scrollTarget = nil
                }
                .onAppear { if let last = c.messages.last { proxy.scrollTo(last.id, anchor: .bottom) } }
            }
            if !c.typing.isEmpty {
                Text("\(c.typing.joined(separator: ", ")) \(c.typing.count == 1 ? "is" : "are") typing…")
                    .font(.footnote).foregroundStyle(.secondary).padding(.horizontal)
            }
            composer(c)
        }
        .onKeyPress(phases: .down) { press in handleMessageReturnKey(press, c) }
        .navigationTitle(c.title)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItemGroup(placement: .topBarTrailing) {
                Button { sheet = .goTo } label: { Label("Go to", systemImage: "arrow.turn.down.right") }
                Button { sheet = .links(nil) } label: { Label("Links", systemImage: "link") }
                if case .room = kind {
                    Button { sheet = .members } label: { Label("Members", systemImage: "person.3") }
                }
                if !backStack.isEmpty {
                    Button { jumpBack() } label: { Label("Back to where I was", systemImage: "arrow.uturn.backward") }
                }
            }
        }
        .sheet(item: $sheet) { s in
            switch s {
            case .goTo: GoToSheet(conv: c) { id in jump(to: id) }
            case .links(let mid): LinksSheet(conv: c, messageID: mid) { url in openLink(url) }
            case .react(let mid): ReactionSheet { emoji in
                if let m = c.messages.first(where: { $0.id == mid }) { model.toggleReaction(emoji, on: m, in: c) }
            }
            case .members: MembersView(conv: c)
            case .web(let url): SafariView(url: url).ignoresSafeArea()
            }
        }
    }

    private func row(_ m: ChatMessage, _ c: Conversation) -> some View {
        let links = LinkFinder.find(m.text)
        let mine = m.sender.lowercased() == model.username.lowercased()
        return VStack(alignment: mine ? .trailing : .leading, spacing: 2) {
            if !m.isSystem {
                Text("\(mine ? "You" : m.sender) · \(m.time.formatted(date: .omitted, time: .shortened))")
                    .font(.caption).foregroundStyle(.secondary)
            }
            Text(m.deleted ? "(message deleted)" : m.text)
                .italic(m.isSystem)
            if !m.reactions.isEmpty {
                Text(m.reactions.map { "\($0.emoji) \($0.users.count)" }.joined(separator: "  ")).font(.caption)
            }
            let status = model.statusText(m, in: c)
            if !status.isEmpty { Text(status).font(.caption2).foregroundStyle(.secondary) }
        }
        .frame(maxWidth: .infinity, alignment: mine ? .trailing : .leading)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(model.spokenLabel(m, in: c))
        .accessibilityFocused($focusedMessage, equals: m.id)
        .accessibilityAction(named: "Copy") { UIPasteboard.general.string = m.text; Announce.say("Copied") }
        .accessibilityAction(named: "React") { sheet = .react(m.id) }
        .accessibilityAction(named: "Thumbs up") { model.toggleReaction("\u{1F44D}", on: m, in: c) }
        // The unnamed default action. With VoiceOver on, a double-tap on the focused row arrives as
        // accessibilityActivate(), not as a two-count tap gesture, so onTapGesture alone never fires and
        // there would be no way at all to play a voice message. Activation opens a lone link, or
        // plays/pauses a voice message.
        .accessibilityAction {
            if let first = links.first { openLink(first.url) }
            else if m.voice != nil { model.toggleVoice(m, in: c) }
        }
        .modifier(OptionalActions(m: m, c: c, links: links, host: self))
        .contextMenu { menu(m, c, links) }
        .onTapGesture(count: 2) { if let first = links.first { openLink(first.url) } else if m.voice != nil { model.toggleVoice(m, in: c) } }
    }

    @ViewBuilder
    private func menu(_ m: ChatMessage, _ c: Conversation, _ links: [LinkFinder.Link]) -> some View {
        Button("Copy") { UIPasteboard.general.string = m.text }
        Menu("React") {
            ForEach(Reactions.quick, id: \.0) { r in Button("\(r.0) \(r.1)") { model.toggleReaction(r.0, on: m, in: c) } }
            Button("More…") { sheet = .react(m.id) }
        }
        if !links.isEmpty {
            Menu("Links in this message (\(links.count))") {
                ForEach(links, id: \.url) { l in
                    Button(model.linkTitles[l.url].map { "\($0), \(l.url)" } ?? l.url) { openLink(l.url) }
                }
            }
        }
        if model.canEdit(m, in: c) {
            Button("Edit") { editing = m; draft = m.text }
            Button("Delete for everyone", role: .destructive) { model.delete(m, in: c) }
        }
        if case .room(let id) = c.kind, m.sender.lowercased() == model.username.lowercased() {
            Button("Who has read this") { model.roomAction("group_room_read_status", room: id, ["message_id": m.id]) }
        }
    }

    private func composer(_ c: Conversation) -> some View {
        HStack(alignment: .bottom) {
            TextField(editing == nil ? "Message" : "Edit message", text: $draft, axis: .vertical)
                .lineLimit(1...5)
                .textFieldStyle(.roundedBorder)
                .focused($composerFocused)
                .onChange(of: draft) { _, text in sendTyping(c, typing: !text.isEmpty) }
                .onKeyPress(phases: .down) { press in handleReturnKey(press, c) }
            Button {
                Task { await toggleRecording(c) }
            } label: {
                Image(systemName: recording ? "stop.circle.fill" : "mic.circle")
                    .frame(minWidth: Composer.minHitTarget, minHeight: Composer.minHitTarget)
                    .contentShape(Rectangle())
            }
            .accessibilityLabel(recording ? "Stop and send voice message" : "Record voice message")
            Button {
                send(c)
            } label: {
                Image(systemName: "paperplane.fill")
                    .frame(minWidth: Composer.minHitTarget, minHeight: Composer.minHitTarget)
                    .contentShape(Rectangle())
            }
            .accessibilityLabel(editing == nil ? "Send" : "Save edit")
            .disabled(draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
        }
        .padding(8)
    }

    private func send(_ c: Conversation) {
        if let e = editing {
            model.edit(e, to: draft, in: c)
            editing = nil
        } else {
            model.sendText(draft, in: c)
        }
        draft = ""
        sendTyping(c, typing: false)
    }

    /// Hardware keyboard Return: setting off, or no hardware keyboard, leaves Return alone (inserts a new line).
    /// Shift+Return or Option+Return always makes a new line; Command+Return always sends.
    private func handleReturnKey(_ press: KeyPress, _ c: Conversation) -> KeyPress.Result {
        guard press.key == .return, GCKeyboard.coalesced != nil else { return .ignored }
        let sendsMessage = press.modifiers.contains(.command) || model.enterKeySendsMessage
        guard sendsMessage, !press.modifiers.contains(.shift), !press.modifiers.contains(.option) else { return .ignored }
        guard !draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return .ignored }
        send(c)
        return .handled
    }

    /// Hardware keyboard Return while a message row has focus rather than the composer: play, pause
    /// or resume the focused voice message. This goes through `AppModel.toggleVoice`, the same single
    /// state machine the VoiceOver default action uses, so the key and the double-tap share one
    /// player and one notion of what is paused. Plain Return only; Shift+Return is left alone until
    /// Thrive has a reply feature to attach a voice reply to.
    private func handleMessageReturnKey(_ press: KeyPress, _ c: Conversation) -> KeyPress.Result {
        guard press.key == .return, GCKeyboard.coalesced != nil else { return .ignored }
        guard !composerFocused, press.modifiers.isEmpty else { return .ignored }
        guard let id = focusedMessage,
              let m = c.messages.first(where: { $0.id == id }), m.voice != nil else { return .ignored }
        model.toggleVoice(m, in: c)
        return .handled
    }

    private func sendTyping(_ c: Conversation, typing: Bool) {
        switch c.kind {
        case .direct(let u): model.send(["action": "typing", "to": u, "typing": typing])
        case .room(let id): model.send(["action": "group_room_typing", "room_id": id, "typing": typing])
        }
    }

    private func toggleRecording(_ c: Conversation) async {
        if recording {
            recording = false
            if let (wav, secs) = recorder.stop() { model.sendVoice(wav: wav, seconds: secs, in: c) }
            else { Announce.say("That was too short to send.") }
        } else if await recorder.start() {
            recording = true
            Announce.say("Recording. Activate the button again to stop and send.")
        }
    }

    func openLink(_ url: String) {
        guard let u = URL(string: url) else { return }
        if model.linkOpenInApp, ["http", "https"].contains(u.scheme?.lowercased() ?? "") { sheet = .web(u) }
        else { UIApplication.shared.open(u) }
    }

    func jump(to id: String) {
        if let current = focusedMessage { backStack.append(current) }
        scrollTarget = id
    }

    private func jumpBack() {
        if let id = backStack.popLast() { scrollTarget = id }
    }

    fileprivate func showLinks(_ id: String) { sheet = .links(id) }
    fileprivate func startEdit(_ m: ChatMessage) { editing = m; draft = m.text }
}

/// VoiceOver actions that only apply to some messages.
private struct OptionalActions: ViewModifier {
    let m: ChatMessage
    let c: Conversation
    let links: [LinkFinder.Link]
    let host: ChatView
    @Environment(AppModel.self) private var model

    func body(content: Content) -> some View {
        content
            .accessibilityActions {
                if links.count == 1 { Button("Open link") { host.openLink(links[0].url) } }
                if !links.isEmpty { Button("Links in this message") { host.showLinks(m.id) } }
                if model.canEdit(m, in: c) {
                    Button("Edit") { host.startEdit(m) }
                    Button("Delete for everyone") { model.delete(m, in: c) }
                }
            }
    }
}

struct SafariView: UIViewControllerRepresentable {
    let url: URL
    func makeUIViewController(context: Context) -> SFSafariViewController { SFSafariViewController(url: url) }
    func updateUIViewController(_ vc: SFSafariViewController, context: Context) {}
}
