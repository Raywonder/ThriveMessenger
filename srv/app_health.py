"""app_health.py - report update results, errors and diagnostics to our app-health collector.

Drop-in, stdlib only, Python 3.6+. Never raises, never blocks the UI (sends on a thread),
keeps a small on-disk queue so reports made while offline go out later.

    from app_health import AppHealth
    health = AppHealth("thrive", APP_KEY, VERSION, data_dir=config_dir)
    health.set_enabled(user_settings.get("send_app_health", True))   # privacy toggle
    health.on_startup()                         # reports "updated to X" / "update failed" / "didn't relaunch"
    ...
    health.update_started(to_version="15.19")   # right before launching the installer and exiting
    health.update_failed("download", exc)       # classify() decides network vs server vs app
    health.report_error("crash", exc)           # e.g. from sys.excepthook
    ok, ref = health.submit_diagnostics(log_text, note="what the user typed")

Privacy: sends a random install id (not tied to any account), app, version, platform, OS name,
event, error class and a short error text. Never message contents, usernames, keys or passwords;
the server also redacts emails, tokens and user folder names.
"""
import json
import os
import platform as _platform
import socket
import ssl
import sys
import threading
import time
import uuid
import urllib.error
import urllib.request

ENDPOINT = "https://files.tappedin.fm/app-health/v1"
RELAUNCH_GRACE = 10 * 60      # seconds: new version must start this soon after the installer ran
QUEUE_MAX = 30


def classify(exc):
    """'network' = user's side (offline, DNS, timeout, TLS interception, captive portal): retry quietly, never alert.
    'server' = our side (HTTP 4xx/5xx, bad feed). 'disk'/'permission' = local. Else 'app'."""
    if isinstance(exc, urllib.error.HTTPError):
        return "server"
    if isinstance(exc, (socket.timeout, TimeoutError, ConnectionError, socket.gaierror)):
        return "network"
    if isinstance(exc, ssl.SSLError):
        return "network"              # usually interception/captive portal on the user's side
    if isinstance(exc, urllib.error.URLError):
        return "network"
    if isinstance(exc, PermissionError):
        return "permission"
    if isinstance(exc, OSError) and getattr(exc, "errno", None) in (28, 122):   # ENOSPC, EDQUOT
        return "disk"
    if isinstance(exc, (ValueError, KeyError)) and "json" in type(exc).__module__.lower():
        return "server"
    return "app"


def _platform_name():
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


class AppHealth:
    def __init__(self, app, key, version, data_dir, channel="", endpoint=ENDPOINT):
        self.app, self.key, self.version, self.channel = app, key, str(version), channel
        self.endpoint = endpoint.rstrip("/")
        self.path = os.path.join(data_dir, "app_health.json")
        self.lock = threading.Lock()
        self.flush_lock = threading.Lock()
        self.state = self._load()
        if not self.state.get("install_id"):
            self.state["install_id"] = str(uuid.uuid4())
            self._save()

    # ------------------------------------------------------------- state
    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                d = json.load(f)
                return d if isinstance(d, dict) else {}
        except Exception:
            return {}

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.state, f)
            os.replace(tmp, self.path)
        except Exception:
            pass

    @property
    def enabled(self):
        return self.state.get("enabled", True)

    def set_enabled(self, on):
        with self.lock:
            self.state["enabled"] = bool(on)
            if not on:
                self.state["queue"] = []
            self._save()

    # ------------------------------------------------------------- events
    def _base(self, event, **kw):
        rec = {"app": self.app, "install_id": self.state["install_id"], "platform": _platform_name(),
               "os": ("%s %s" % (_platform.system(), _platform.release()))[:80], "arch": _platform.machine()[:16],
               "channel": self.channel, "version": self.version, "event": event}
        for k, v in kw.items():
            if v is not None:
                rec[k] = v
        return rec

    def send(self, event, **kw):
        if not self.enabled:
            return
        rec = self._base(event, **kw)
        with self.lock:
            q = self.state.setdefault("queue", [])
            q.append(rec)
            del q[:-QUEUE_MAX]
            self._save()
        threading.Thread(target=self.flush, daemon=True).start()

    def flush(self):
        if not self.flush_lock.acquire(blocking=False):
            return                       # another thread is already sending; it picks up new items too
        try:
            while True:
                with self.lock:
                    q = self.state.get("queue", [])
                    if not q:
                        return
                    rec = q[0]
                try:
                    self._post("/event", rec, timeout=8)
                except urllib.error.HTTPError as e:
                    if e.code not in (400, 403, 413):
                        return           # throttled / server trouble: keep for next time
                except Exception:
                    return               # offline: keep for next time
                with self.lock:
                    q = self.state.get("queue", [])
                    if q and q[0] is rec:
                        q.pop(0)
                    self._save()
        finally:
            self.flush_lock.release()

    def _post(self, path, body, timeout):
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(self.endpoint + path, data=data, method="POST", headers={
            "Content-Type": "application/json", "X-App-Key": self.key,
            "User-Agent": "%s/%s app-health" % (self.app, self.version)})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8") or "{}")

    # ------------------------------------------------------------- update flow
    def on_startup(self):
        """Call once per launch, early. Works out what happened to the last update."""
        now = time.time()
        pend = self.state.pop("pending_update", None)
        last = self.state.get("last_version")
        self.state["last_version"] = self.version
        self._save()
        if pend:
            frm, to, ts = pend.get("from", ""), pend.get("to", ""), pend.get("ts", now)
            if self.version == to or (to and self.version != frm):
                late = now - ts > RELAUNCH_GRACE
                self.send("update_succeeded", from_version=frm, to_version=self.version, stage="relaunch",
                          detail={"seconds_to_relaunch": int(now - ts), "relaunched_automatically": not late})
                if late:
                    self.send("update_not_relaunched", from_version=frm, to_version=self.version, stage="relaunch",
                              error_class="app", error="Installed, but the app only started again %d minutes later (it didn't reopen by itself)." % ((now - ts) // 60))
            else:
                err = self.state.pop("installer_error", "") or "Still on %s after the installer ran." % self.version
                self.send("update_install_failed", from_version=frm, to_version=to, stage="install", error_class="app", error=err)
        elif last and last != self.version:
            self.send("update_succeeded", from_version=last, to_version=self.version, detail={"method": "manual or store"})
        day = time.strftime("%Y-%m-%d")
        if self.state.get("started_day") != day:
            self.state["started_day"] = day
            self._save()
            self.send("app_started")
        else:
            threading.Thread(target=self.flush, daemon=True).start()

    def update_started(self, to_version):
        """Call right before running the installer / quitting to update."""
        self.state["pending_update"] = {"from": self.version, "to": str(to_version), "ts": time.time()}
        self._save()
        if self.enabled:
            try:   # synchronous, short: the app is about to exit
                self._post("/event", self._base("update_started", from_version=self.version, to_version=str(to_version), stage="install"), timeout=4)
            except Exception:
                pass

    def update_failed(self, stage, exc_or_text, to_version="", error_class=None):
        """stage: check | download | verify | install. Network-class failures are recorded but never alert."""
        ec = error_class or (classify(exc_or_text) if isinstance(exc_or_text, BaseException) else "app")
        ev = {"check": "update_check_failed", "download": "update_download_failed", "verify": "update_download_failed"}.get(stage, "update_install_failed")
        self.send(ev, stage=stage, to_version=str(to_version or ""), error_class=ec, error=_short(exc_or_text))

    def report_error(self, kind, exc_or_text, stage="runtime"):
        """kind: 'error' or 'crash'."""
        self.send("crash" if kind == "crash" else "error", stage=stage, error_class="app", error=_short(exc_or_text))

    def submit_diagnostics(self, log_text, note="", timeout=20):
        """User-initiated. Returns (ok, reference_or_error). Sends even if the toggle is off (the user asked)."""
        import base64, gzip
        blob = base64.b64encode(gzip.compress((log_text or "")[-1500000:].encode("utf-8", "replace"))).decode("ascii")
        body = self._base("diagnostics", note=(note or "")[:2000], log=blob, log_encoding="gzip+base64")
        try:
            r = self._post("/diagnostics", body, timeout=timeout)
            return True, r.get("reference", "")
        except urllib.error.HTTPError as e:
            return False, "The server said %s." % e.code
        except Exception as e:
            return False, "Couldn't reach the server (%s)." % classify(e)


def _short(x):
    if isinstance(x, BaseException):
        return ("%s: %s" % (type(x).__name__, x))[:1000]
    return str(x or "")[:1000]
