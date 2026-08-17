# Thrive Messenger iOS

This is the first native SwiftUI iOS target for Thrive Messenger. It uses the
existing newline-delimited JSON/TLS server protocol and currently covers the
foundation needed for TestFlight work: sign-in transport, contact discovery,
group-chat listing, named groups, member counts, joining, and group messages.

## Generate and build

On the Mac mini with Xcode and XcodeGen installed:

```sh
xcodegen generate --spec ios/project.yml --project ios/ThriveMessenger.xcodeproj
xcodebuild -project ios/ThriveMessenger.xcodeproj -scheme ThriveMessenger \
  -sdk iphonesimulator -configuration Debug CODE_SIGNING_ALLOWED=NO build
```

The bundle identifier is `fm.tappedin.thrive-messenger`. Apple Developer team
selection, signing, App Store Connect metadata, device VoiceOver checks, and
TestFlight upload remain release steps after the simulator build is clean.
