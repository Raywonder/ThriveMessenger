#!/usr/bin/env python3
"""App Store Connect helper for Thrive TestFlight (runs on the Mac mini; reads the API key env, never prints secrets).

  asc_beta.py status                 app, latest builds, beta groups, review details (no changes)
  asc_beta.py submit BUILD_NUMBER    wait for processing, set What to Test, add to the external group, submit for beta review
"""
import json, os, sys, time, urllib.request, urllib.error
import ssl
import certifi
import jwt  # PyJWT

CTX = ssl.create_default_context(cafile=certifi.where())

BUNDLE = "fm.tappedin.thrivemessenger"
GROUP = "Public"
WHAT_TO_TEST = ("Thrive 15.17 for iPhone: chats and chat rooms, reactions, links (opened inside Thrive), Go to, "
                "voice messages, read receipts, and automatic reconnecting. Please try it with VoiceOver and tell us "
                "anything that is hard to reach or not spoken clearly.")

def env():
    vals = {}
    for line in open(os.path.expanduser("~/dev/appstore/voicelink/appstoreconnect_api.env")):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip().strip('"').strip("'")
    return vals

E = env()
def token():
    key = open(os.path.expanduser(E["ASC_PRIVATE_KEY_PATH"])).read()
    now = int(time.time())
    return jwt.encode({"iss": E["ASC_ISSUER_ID"], "iat": now, "exp": now + 1200, "aud": "appstoreconnect-v1"}, key,
                      algorithm="ES256", headers={"kid": E["ASC_KEY_ID"], "typ": "JWT"})

def api(method, path, body=None):
    req = urllib.request.Request("https://api.appstoreconnect.apple.com/v1/" + path.lstrip("/"), method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + token(), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60, context=CTX) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        raise SystemExit(f"{method} {path} -> {e.code}: {detail[:800]}")

def app_id():
    data = api("GET", f"apps?filter[bundleId]={BUNDLE}")["data"]
    if not data:
        raise SystemExit("no app record for " + BUNDLE)
    return data[0]["id"]

def status():
    aid = app_id()
    builds = api("GET", f"builds?filter[app]={aid}&sort=-uploadedDate&limit=5")["data"]
    print("builds:", [(b["attributes"]["version"], b["attributes"]["processingState"]) for b in builds])
    groups = api("GET", f"apps/{aid}/betaGroups")["data"]
    print("groups:", [(g["attributes"]["name"], "internal" if g["attributes"]["isInternalGroup"] else "external") for g in groups])
    det = api("GET", f"apps/{aid}/betaAppReviewDetail")["data"]["attributes"]
    print("review detail set:", {k: bool(v) for k, v in det.items()})
    locs = api("GET", f"apps/{aid}/betaAppLocalizations")["data"]
    print("beta localizations:", [(l["attributes"]["locale"], bool(l["attributes"].get("feedbackEmail")), bool(l["attributes"].get("description"))) for l in locs])

def others():
    """Which of Dom's other apps have beta review contact details and beta localizations (booleans only)."""
    for a in api("GET", "apps?limit=50")["data"]:
        det = api("GET", f"apps/{a['id']}/betaAppReviewDetail")["data"]["attributes"]
        locs = api("GET", f"apps/{a['id']}/betaAppLocalizations")["data"]
        print(a["attributes"]["bundleId"], {k: bool(v) for k, v in det.items() if k.startswith("contact")},
              [(l["attributes"]["locale"], bool(l["attributes"].get("feedbackEmail"))) for l in locs])

def prepare_review(demo_user, demo_pass):
    """Copy contact details from another app of Dom's, add the beta description, and set the reviewer demo account."""
    aid = app_id()
    src = None
    for a in api("GET", "apps?limit=50")["data"]:
        if a["id"] == aid:
            continue
        det = api("GET", f"apps/{a['id']}/betaAppReviewDetail")["data"]["attributes"]
        if det.get("contactPhone") and det.get("contactEmail"):
            src = det; break
    if not src:
        raise SystemExit("no other app has beta review contact details to copy")
    attrs = {k: src[k] for k in ("contactFirstName", "contactLastName", "contactPhone", "contactEmail")}
    attrs.update(demoAccountRequired=True, demoAccountName=demo_user, demoAccountPassword=demo_pass,
                 notes=("Thrive is an accessible messenger for blind and low-vision people. Sign in with the demo account "
                        "(server TappedIn.fm is preselected). The demo account has a contact and a room to try chats, rooms, "
                        "reactions, links and voice messages. Everything works with VoiceOver."))
    det_id = api("GET", f"apps/{aid}/betaAppReviewDetail")["data"]["id"]
    api("PATCH", f"betaAppReviewDetails/{det_id}", {"data": {"type": "betaAppReviewDetails", "id": det_id, "attributes": attrs}})
    locs = api("GET", f"apps/{aid}/betaAppLocalizations")["data"]
    loc = {"description": "Thrive Messenger: an accessible chat app with direct messages, chat rooms, voice messages, reactions "
                          "and links, built for VoiceOver first.",
           "feedbackEmail": src["contactEmail"]}
    if locs:
        api("PATCH", f"betaAppLocalizations/{locs[0]['id']}", {"data": {"type": "betaAppLocalizations", "id": locs[0]["id"], "attributes": loc}})
    else:
        api("POST", "betaAppLocalizations", {"data": {"type": "betaAppLocalizations", "attributes": dict(loc, locale="en-US"),
                                                      "relationships": {"app": {"data": {"type": "apps", "id": aid}}}}})
    print("review details and beta description set (contact copied from another app)")

def submit(build_number):
    aid = app_id()
    build = None
    for _ in range(90):
        data = api("GET", f"builds?filter[app]={aid}&filter[version]={build_number}")["data"]
        if data and data[0]["attributes"]["processingState"] == "VALID":
            build = data[0]; break
        state = data[0]["attributes"]["processingState"] if data else "not uploaded yet"
        print("waiting for processing:", state, flush=True)
        time.sleep(60)
    if not build:
        raise SystemExit("build never finished processing")
    bid = build["id"]
    # Export compliance is answered in Info.plist (ITSAppUsesNonExemptEncryption = NO).
    locs = api("GET", f"builds/{bid}/betaBuildLocalizations")["data"]
    en = next((l for l in locs if l["attributes"]["locale"].startswith("en")), None)
    if en:
        api("PATCH", f"betaBuildLocalizations/{en['id']}", {"data": {"type": "betaBuildLocalizations", "id": en["id"], "attributes": {"whatsNew": WHAT_TO_TEST}}})
    else:
        api("POST", "betaBuildLocalizations", {"data": {"type": "betaBuildLocalizations", "attributes": {"locale": "en-US", "whatsNew": WHAT_TO_TEST},
                                                        "relationships": {"build": {"data": {"type": "builds", "id": bid}}}}})
    groups = api("GET", f"apps/{aid}/betaGroups")["data"]
    group = next((g for g in groups if g["attributes"]["name"] == GROUP), None)
    if not group:
        group = api("POST", "betaGroups", {"data": {"type": "betaGroups", "attributes": {"name": GROUP, "publicLinkEnabled": True, "publicLinkLimit": 500},
                                                    "relationships": {"app": {"data": {"type": "apps", "id": aid}}}}})["data"]
    api("POST", f"betaGroups/{group['id']}/relationships/builds", {"data": [{"type": "builds", "id": bid}]})
    # Internal testers get it straight away too.
    for g in groups:
        if g["attributes"]["isInternalGroup"]:
            try:
                api("POST", f"betaGroups/{g['id']}/relationships/builds", {"data": [{"type": "builds", "id": bid}]})
            except SystemExit:
                pass
    sub = api("POST", "betaAppReviewSubmissions", {"data": {"type": "betaAppReviewSubmissions",
                                                            "relationships": {"build": {"data": {"type": "builds", "id": bid}}}}})
    print("submitted for beta review:", sub["data"]["attributes"].get("betaReviewState"))
    g2 = api("GET", f"betaGroups/{group['id']}")["data"]["attributes"]
    print("public link:", g2.get("publicLink") or "(appears after approval)")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "submit":
        submit(sys.argv[2])
    elif len(sys.argv) > 1 and sys.argv[1] == "others":
        others()
    elif len(sys.argv) > 1 and sys.argv[1] == "prepare":
        u, p = sys.stdin.read().split("\n", 1)
        prepare_review(u.strip(), p.strip())
    else:
        status()
