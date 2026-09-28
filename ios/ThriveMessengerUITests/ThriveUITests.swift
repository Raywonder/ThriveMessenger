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
        app.secureTextFields["Password"].tap(); app.secureTextFields["Password"].typeText(pass)
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
}
