#!/bin/bash
set -a; . ~/dev/appstore/voicelink/appstoreconnect_api.env; . ~/dev/appstore/voicelink/macos_signing.env; set +a
K=$(eval echo "$ASC_PRIVATE_KEY_PATH")
AUTH=(-allowProvisioningUpdates -authenticationKeyPath "$K" -authenticationKeyID "$ASC_KEY_ID" -authenticationKeyIssuerID "$ASC_ISSUER_ID")
KC=~/Library/Keychains/login.keychain-db
security unlock-keychain -p "$MACOS_SIGNING_KEYCHAIN_PASSWORD" "$KC" >/dev/null 2>&1 && echo "keychain unlocked"
# The distribution identity whose key codesign may use without a prompt (the one tCast signs with).
ID=AF38D9CB4929E14F7AA917DFA68FB063F70D9DAF
cd ~/builds/thrive-ios/ios || exit 1
rm -rf ../Thrive.xcarchive ../export
nice -n 10 xcodebuild archive -project ThriveMessenger.xcodeproj -scheme ThriveMessenger -destination "generic/platform=iOS" \
  -archivePath ../Thrive.xcarchive CURRENT_PROJECT_VERSION="${1:-3}" CODE_SIGN_STYLE=Manual CODE_SIGN_IDENTITY="$ID" OTHER_CODE_SIGN_FLAGS="--keychain $KC" \
  PROVISIONING_PROFILE_SPECIFIER="Thrive Messenger App Store 2026" DEVELOPMENT_TEAM=G5232LU4Z7 > ../archive.log 2>&1
echo "archive exit $?"; grep -E "error:|ARCHIVE SUCCEEDED|ARCHIVE FAILED" ../archive.log | sort -u | head -8
[ -d ../Thrive.xcarchive ] || exit 1
cat > ../ExportManual.plist <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>method</key><string>app-store-connect</string><key>destination</key><string>upload</string>
<key>teamID</key><string>G5232LU4Z7</string><key>signingStyle</key><string>manual</string>
<key>signingCertificate</key><string>$ID</string>
<key>provisioningProfiles</key><dict><key>fm.tappedin.thrivemessenger</key><string>Thrive Messenger App Store 2026</string></dict>
<key>uploadSymbols</key><true/><key>manageAppVersionAndBuildNumber</key><false/>
</dict></plist>
PL
nice -n 10 xcodebuild -exportArchive -archivePath ../Thrive.xcarchive -exportOptionsPlist ../ExportManual.plist -exportPath ../export "${AUTH[@]}" > ../export.log 2>&1
echo "export exit $?"; grep -iE "error|upload|EXPORT SUCCEEDED|EXPORT FAILED" ../export.log | sort -u | head -10
echo done
