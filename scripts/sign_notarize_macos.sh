#!/usr/bin/env bash
# Sign "dist/Thrive Messenger.app" with Dom's Developer ID (hardened runtime), notarise it with the App Store
# Connect API key, staple the ticket and zip it. Run on the Mac mini inside the logged-in session (for example via
# a one-off launch agent) so the login keychain holding the signing certificate is unlocked.
# Output: dist-macos/thrive_messenger-macos-universal2.zip (signed, notarised, stapled). Log lines end with "done".
set -uo pipefail
cd "$(dirname "$0")/.."
APP="dist/Thrive Messenger.app"
ID="${THRIVE_CODESIGN_IDENTITY:-63C895656F0AE945B9E24A41AF8DE2AC03ADB7DE}"  # Developer ID Application: Dominique Stansberry
OUT="dist-macos/thrive_messenger-macos-universal2.zip"
step() { echo "== $*"; }
step sign
codesign --force --deep --options runtime --timestamp --entitlements packaging/macos-thrive.entitlements --sign "$ID" "$APP" || { echo "sign failed"; echo done; exit 1; }
codesign --verify --deep --strict --verbose=1 "$APP" && echo "signature verified"
step notarise
rm -f dist-macos/notarize.zip
ditto -c -k --keepParent "$APP" dist-macos/notarize.zip
set -a; . "$HOME/dev/appstore/voicelink/appstoreconnect_api.env"; set +a
xcrun notarytool submit dist-macos/notarize.zip --key "$ASC_PRIVATE_KEY_PATH" --key-id "$ASC_KEY_ID" --issuer "$ASC_ISSUER_ID" \
  --wait --timeout 30m 2>&1 | grep -E "status:|id:|Processing complete|error" | tail -4
rm -f dist-macos/notarize.zip
step staple
xcrun stapler staple "$APP" 2>&1 | tail -1
spctl -a -t exec -vv "$APP" 2>&1 | head -3
rm -f "$OUT"
ditto -c -k --sequesterRsrc --keepParent "$APP" "$OUT"
shasum -a 256 "$OUT"
echo done
