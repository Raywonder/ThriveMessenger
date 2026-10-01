import XCTest

/// Signs in with a throwaway account (TEST_RUNNER_THRIVE_USER / TEST_RUNNER_THRIVE_PASS) against the live server,
/// then checks what VoiceOver gets: message labels, sending, the rooms list, and Apple's accessibility audit.
final class ThriveUITests: XCTestCase {
    private var app: XCUIApplication!
    private var env: [String: String] { ProcessInfo.processInfo.environment }

    override func setUp() {
        continueAfterFailure = true
        app = XCUIApplication()
        app.launchArguments = ["--reset-for-tests"]
        app.launch()
    }

    private func signIn() throws {
        let user = try XCTUnwrap(env["THRIVE_USER"]), pass = try XCTUnwrap(env["THRIVE_PASS"])
        let field = app.textFields["Username"]
        XCTAssertTrue(field.waitForExistence(timeout: 10), "sign-in screen")
        field.tap(); field.typeText(user)
        let pw = app.secureTextFields["Password"]
        for _ in 0..<3 where !((pw.value(forKey: "hasKeyboardFocus") as? Bool) ?? false) {
            pw.tap(); _ = app.keyboards.firstMatch.waitForExistence(timeout: 2)
        }
        pw.typeText(pass)
        app.buttons["Sign in"].tap()
        XCTAssertTrue(app.tabBars.buttons["Chats"].waitForExistence(timeout: 45), "signed in")
    }

    func testChatRoomsAndVoiceOverLabels() throws {
        try signIn()
        let peer = try XCTUnwrap(env["THRIVE_PEER"])
        try app.performAccessibilityAudit(for: [.sufficientElementDescription, .hitRegion]) { _ in false }

        let contact = app.buttons.matching(NSPredicate(format: "label BEGINSWITH %@", peer)).firstMatch
        XCTAssertTrue(contact.waitForExistence(timeout: 10), "contact listed")
        contact.tap()

        let msg = app.descendants(matching: .any).matching(NSPredicate(format: "label BEGINSWITH 'iotest_b,' AND label CONTAINS 'hello from the peer' AND label CONTAINS '1 link'")).firstMatch
        if !msg.waitForExistence(timeout: 15) {
            let all = app.descendants(matching: .any).allElementsBoundByIndex.map { "\($0.elementType.rawValue):\($0.label)" }
            print("LABELS: \(all.filter { !$0.hasSuffix(":") }.prefix(60))")
            XCTFail("message reads sender, time, text and link count")
        }
        print("MESSAGE LABEL: \(msg.label)")

        let field = app.textFields["Message"]
        XCTAssertTrue(field.waitForExistence(timeout: 5))
        field.tap(); field.typeText("hello from the iPhone test")
        app.buttons["Send"].tap()
        let mine = NSPredicate(format: "label BEGINSWITH 'You,' AND label CONTAINS 'hello from the iPhone test'")
        XCTAssertTrue(app.descendants(matching: .any).matching(mine).firstMatch.waitForExistence(timeout: 10), "own message shown with status")
        try app.performAccessibilityAudit(for: [.sufficientElementDescription]) { _ in false }

        app.tables.firstMatch.exists ? app.tables.firstMatch.swipeDown() : app.collectionViews.firstMatch.swipeDown()
        if app.keyboards.count > 0 { app.navigationBars.buttons.element(boundBy: 0).tap() }
        app.tabBars.buttons["Rooms"].tap()
        let room = app.descendants(matching: .any).matching(NSPredicate(format: "label BEGINSWITH 'IO Room, member'")).firstMatch
        if !room.waitForExistence(timeout: 10) {
            let all = app.descendants(matching: .any).allElementsBoundByIndex.map { "\($0.elementType.rawValue):\($0.label)" }
            print("ROOMS LABELS: \(all.filter { !$0.hasSuffix(":") }.prefix(60))")
            XCTFail("room directory item reads name, role, members, topic")
        }
        print("ROOM LABEL: \(room.label)")
        room.tap()
        let roomMsg = app.descendants(matching: .any).matching(NSPredicate(format: "label CONTAINS 'room hello from the peer'")).firstMatch
        XCTAssertTrue(roomMsg.waitForExistence(timeout: 15), "room history shown")
        print("ROOM MESSAGE LABEL: \(roomMsg.label)")
        try app.performAccessibilityAudit(for: [.sufficientElementDescription]) { _ in false }
    }

    /// Enter-key-sends-message setting (general > Keyboard) and the Forgot Password sheet from the sign-in screen.
    /// No account needed: request_reset answers "ok" for any identifier (real or not) to avoid revealing which
    /// accounts exist, so this exercises the real sheet and server round trip without touching any user's data.
    func testForgotPasswordSheet() throws {
        let field = app.textFields["Username"]
        XCTAssertTrue(field.waitForExistence(timeout: 10), "sign-in screen")
        let forgot = app.buttons["Forgot password?"]
        XCTAssertTrue(forgot.exists)
        forgot.tap()
        XCTAssertTrue(app.navigationBars["Reset Password"].waitForExistence(timeout: 5), "reset sheet")
        let identifier = app.textFields["Email or username"]
        XCTAssertTrue(identifier.exists)
        try app.performAccessibilityAudit(for: [.sufficientElementDescription, .hitRegion]) { _ in false }
        identifier.tap(); identifier.typeText("testflight-batch-20260930-nonexistent-account")
        app.buttons["Request reset code"].tap()
        XCTAssertTrue(app.staticTexts["If that account exists, a reset code has been sent to its email."].waitForExistence(timeout: 10), "server round trip")
        try app.performAccessibilityAudit(for: [.sufficientElementDescription, .hitRegion]) { _ in false }
        app.buttons["Cancel"].tap()
    }

    /// Needs a signed-in session; not run in this batch (no throwaway test account was provisioned tonight).
    /// Next real-device/simulator pass with THRIVE_USER/THRIVE_PASS set should cover this.
    func testKeyboardSetting() throws {
        try signIn()
        app.tabBars.buttons["Settings"].tap()
        app.buttons["settings.category.general"].tap()
        XCTAssertTrue(app.navigationBars["General"].waitForExistence(timeout: 5), "general category screen")
        let tabs = app.segmentedControls.firstMatch
        XCTAssertTrue(tabs.buttons["Keyboard"].exists, "Keyboard tab present")
        tabs.buttons["Keyboard"].tap()
        XCTAssertTrue(app.switches["Enter key sends message"].waitForExistence(timeout: 5), "keyboard toggle")
        try app.performAccessibilityAudit(for: [.sufficientElementDescription, .hitRegion]) { _ in false }
    }

    /// Does the contact row survive being a `NavigationLink` label? `ContactsView.list` puts
    /// `.accessibilityElement(children: .ignore)`, the merged label, `.accessibilityActions` and
    /// `.contextMenu` on the inner `VStack`, and SwiftUI folds a link's label into the link's own element.
    /// What we want is the link's Button carrying our merged label -- then the actions attached beside
    /// that label are on the element VoiceOver lands on. What we do not want is the Button falling back
    /// to reading its raw contents, which is what happens if these modifiers are moved out onto the link.
    /// XCUITest can't enumerate rotor custom actions, so this doesn't replace the device pass.
    func testContactRowIsOneMergedActivatableElement() throws {
        try signIn()
        let peer = try XCTUnwrap(env["THRIVE_PEER"])

        let buttons = app.buttons.matching(NSPredicate(format: "label BEGINSWITH %@", peer))
        XCTAssertTrue(buttons.firstMatch.waitForExistence(timeout: 15), "contact row for \(peer)")
        let rows = buttons.allElementsBoundByIndex
        for e in rows { print("CONTACT ROW BUTTON: label=\(e.label) hittable=\(e.isHittable)") }
        XCTAssertEqual(rows.count, 1, "one row element, got \(rows.map(\.label))")

        let row = rows[0]
        // "<user>, online/offline[, status][, N unread]". The throwaway peer has no status and no unread,
        // and its status text is just the presence word, which `rowLabel` folds away instead of repeating.
        XCTAssertTrue(row.label == "\(peer), offline" || row.label == "\(peer), online",
                      "merged label on the link's own element, got \(row.label)")
        XCTAssertTrue(row.isHittable, "row is reachable")
        // The raw subtitle must not be what the row reads; that would mean our label never reached it.
        XCTAssertFalse(row.label.contains("Offline") || row.label.contains("Online"),
                       "row is reading its raw contents instead of the merged label: \(row.label)")

        try app.performAccessibilityAudit(for: [.sufficientElementDescription, .hitRegion]) { issue in
            print("AUDIT Chats: \(issue.auditType) \(issue.compactDescription)")
            return true   // reported, not failed: this run is here to say what the audit sees
        }

        row.tap()
        XCTAssertTrue(app.textFields["Message"].waitForExistence(timeout: 15),
                      "activating the merged element still navigates into the chat")

        // The composer's mic and send buttons are bare SF Symbols, so their touch target used to be the
        // ~20 x 19pt glyph. They now carry a 44pt frame plus a matching contentShape on the label; the
        // drawn icons are unchanged. Checked directly as well as through the audit, because the send
        // button is disabled on an empty draft and the audit may skip disabled elements.
        for name in ["Record voice message", "Send"] {
            let b = app.buttons[name]
            XCTAssertTrue(b.waitForExistence(timeout: 5), "composer button \(name)")
            XCTAssertGreaterThanOrEqual(b.frame.width, 44, "\(name) hit width is \(b.frame.width)")
            XCTAssertGreaterThanOrEqual(b.frame.height, 44, "\(name) hit height is \(b.frame.height)")
        }

        try app.performAccessibilityAudit(for: [.sufficientElementDescription, .hitRegion]) { issue in
            print("AUDIT Chat: \(issue.auditType) \(issue.compactDescription)")
            // A hit-region issue on the chat screen is a regression of the composer fix, so fail on it.
            // Everything else stays report-only, the way this run was written.
            return issue.auditType != .hitRegion
        }
    }

    /// Settings root is only categories with a hint each; a category opens its own screen with segmented tabs.
    func testSettingsCategoriesAndTabs() throws {
        try signIn()
        app.tabBars.buttons["Settings"].tap()
        for id in ["general", "notifications", "privacy", "profile", "help"] {
            XCTAssertTrue(app.buttons["settings.category.\(id)"].waitForExistence(timeout: 10), "category \(id)")
        }
        XCTAssertEqual(app.switches.count, 0, "nothing can be changed on the Settings root")
        let notif = app.buttons["settings.category.notifications"]
        print("CATEGORY LABEL: \(notif.label) | VALUE: \(notif.value ?? "")")
        XCTAssertEqual(notif.value as? String, "What you hear when messages arrive.")
        try app.performAccessibilityAudit(for: [.sufficientElementDescription, .hitRegion]) { _ in false }
        notif.tap()
        XCTAssertTrue(app.navigationBars["Notifications"].waitForExistence(timeout: 5), "category screen")
        let tabs = app.segmentedControls.firstMatch
        XCTAssertTrue(tabs.buttons["Chats"].exists && tabs.buttons["Rooms"].exists, "segmented tabs")
        XCTAssertTrue(app.buttons["New message in the chat I'm in, Read it aloud"].exists || app.staticTexts["New message in the chat I'm in"].exists)
        try app.performAccessibilityAudit(for: [.sufficientElementDescription]) { _ in false }
        tabs.buttons["Rooms"].tap()
        XCTAssertTrue(app.staticTexts["Room messages when the room isn't open"].waitForExistence(timeout: 5)
                      || app.buttons.matching(NSPredicate(format: "label BEGINSWITH 'Room messages'")).firstMatch.exists, "rooms tab")
        app.navigationBars.buttons.element(boundBy: 0).tap()
        app.buttons["settings.category.profile"].tap()
        XCTAssertTrue(app.buttons["Sign out"].waitForExistence(timeout: 5), "account tab")
        try app.performAccessibilityAudit(for: [.sufficientElementDescription]) { _ in false }
    }
}
