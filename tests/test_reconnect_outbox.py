import ast
import json
import os
import textwrap
import time
import types
import unittest
from unittest import mock

try:
    import main
except Exception:
    main = None


def _client_app_methods(names):
    """The real ClientApp methods, even when wx is stubbed (the stubbed base class hides them)."""
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py"), encoding="utf-8").read()
    cls = next(n for n in ast.parse(src).body if isinstance(n, ast.ClassDef) and n.name == "ClientApp")
    ns = {}
    for fn in cls.body:
        if isinstance(fn, ast.FunctionDef) and fn.name in names:
            exec(textwrap.dedent(ast.get_source_segment(src, fn)), main.__dict__, ns)
    return ns


class FakeSock:
    def __init__(self, fail=False):
        self.sent, self.fail = [], fail
    def sendall(self, data):
        if self.fail:
            raise OSError("connection reset")
        self.sent.append(json.loads(data.decode()))


class FakePanel:
    def __init__(self):
        self.marks = []
    def mark_row_queued(self, cid, queued):
        self.marks.append((cid, queued))


@unittest.skipIf(main is None, "main.py needs wxPython (or a stub) to import")
class ReconnectOutboxTests(unittest.TestCase):
    def make_app(self, sock):
        app = types.SimpleNamespace(sock=sock, reconnect_in_progress=False, intentional_disconnect=False,
                                    outbox=[], pending_acks={}, disconnects=0)
        names = ("send_chat_payload", "message_acknowledged", "message_rejected", "_ack_watchdog", "_flush_outbox")
        for name, fn in _client_app_methods(names).items():
            setattr(app, name, types.MethodType(fn, app))
        app.ACK_TIMEOUT_SECONDS = 12
        app._ensure_ack_watchdog = lambda: None
        def disconnect():
            app.disconnects += 1
            app.reconnect_in_progress = True
        app.on_server_disconnect = disconnect
        return app

    def setUp(self):
        self.patches = [mock.patch.object(main, "speak_text", lambda *a, **k: None),
                        mock.patch.object(main, "log_event", lambda *a, **k: None),
                        mock.patch.object(main.wx, "CallLater", lambda *a, **k: None),
                        mock.patch.object(main.wx, "CallAfter", lambda fn, *a, **k: fn(*a, **k))]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def msg(self, cid, to="bob"):
        return {"action": "msg", "to": to, "msg": "hi " + cid, "client_id": cid}

    def test_sent_then_acknowledged(self):
        app = self.make_app(FakeSock())
        self.assertEqual(app.send_chat_payload(FakePanel(), self.msg("a")), "sent")
        self.assertIn("a", app.pending_acks)
        app.message_acknowledged("a")
        self.assertEqual(app.pending_acks, {})

    def test_queued_while_reconnecting_then_flushed(self):
        app = self.make_app(FakeSock())
        app.reconnect_in_progress = True
        panel = FakePanel()
        self.assertEqual(app.send_chat_payload(panel, self.msg("q")), "queued")
        self.assertEqual(len(app.outbox), 1)
        app.reconnect_in_progress = False
        app.sock = FakeSock()
        app._flush_outbox()
        self.assertEqual([m["client_id"] for m in app.sock.sent], ["q"])
        self.assertIn(("q", False), panel.marks)

    def test_dead_socket_queues_and_starts_reconnect(self):
        app = self.make_app(FakeSock(fail=True))
        self.assertEqual(app.send_chat_payload(FakePanel(), self.msg("d")), "queued")
        self.assertEqual(app.disconnects, 1)

    def test_missing_ack_forces_reconnect_and_requeues(self):
        app = self.make_app(FakeSock())
        panel = FakePanel()
        app.send_chat_payload(panel, self.msg("s"))
        app.pending_acks["s"]["sent_at"] = time.time() - 60
        app._ack_watchdog()
        self.assertEqual(app.disconnects, 1)
        self.assertEqual([i["payload"]["client_id"] for i in app.outbox], ["s"])
        self.assertIn(("s", True), panel.marks)

    def test_server_rejection_clears_pending(self):
        app = self.make_app(FakeSock())
        app.send_chat_payload(FakePanel(), self.msg("r", to="Carol"))
        app.message_rejected("carol")
        self.assertEqual(app.pending_acks, {})


if __name__ == "__main__":
    unittest.main()
