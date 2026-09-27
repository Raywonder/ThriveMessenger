import base64
import io
import math
import os
import sqlite3
import struct
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

from srv import server


def _wav_bytes(seconds=1.2, rate=16000):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        frames = b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / rate))) for i in range(int(seconds * rate)))
        w.writeframes(frames)
    return buf.getvalue()


class VoiceMessageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db = server.DB
        self.original_voice_dir = server.VOICE_DIR
        server.DB = str(Path(self.temp_dir.name) / "server.db")
        server.VOICE_DIR = str(Path(self.temp_dir.name) / "voice")
        server.init_db()

    def tearDown(self):
        server.DB = self.original_db
        server.VOICE_DIR = self.original_voice_dir
        self.temp_dir.cleanup()

    def test_wav_becomes_small_mp3_with_label(self):
        msg = {"voice": {"b64": base64.b64encode(_wav_bytes()).decode(), "mime": "audio/wav"}}
        ok, reason, mp3 = server._prepare_voice_message(msg)
        self.assertTrue(ok, reason)
        self.assertEqual(msg["voice"]["mime"], "audio/mpeg")
        self.assertTrue(mp3[:3] == b"ID3" or mp3[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"))
        self.assertAlmostEqual(msg["voice"]["duration"], 1.2, delta=0.3)
        self.assertEqual(msg["msg"], "Voice message (0:01)")

    def test_voicemail_label_and_rejects_bad_audio(self):
        msg = {"voice": {"b64": base64.b64encode(_wav_bytes(2.0)).decode(), "mime": "audio/wav", "voicemail": True}}
        self.assertTrue(server._prepare_voice_message(msg)[0])
        self.assertTrue(msg["msg"].startswith("Voicemail (0:02)"))
        self.assertFalse(server._prepare_voice_message({"voice": {"b64": "not base64!!"}})[0])
        self.assertFalse(server._prepare_voice_message({"voice": {"b64": ""}})[0])
        too_big = "A" * ((server.MAX_VOICE_BYTES * 4) // 3 + 64)
        self.assertFalse(server._prepare_voice_message({"voice": {"b64": too_big}})[0])

    def test_pending_voicemail_round_trip_and_delete_removes_file(self):
        msg = {"voice": {"b64": base64.b64encode(_wav_bytes()).decode(), "mime": "audio/wav", "voicemail": True}}
        ok, _, mp3 = server._prepare_voice_message(msg)
        path = server._store_voice_file("vm1", mp3)
        self.assertTrue(os.path.isfile(path))
        server._record_direct_message_history("alice", "bob", msg["msg"], msg_uid="vm1", attachment_path=path)
        con = sqlite3.connect(server.DB)
        con.execute("INSERT INTO pending_voicemail(msg_uid,to_user,created_at) VALUES('vm1','bob','x')")
        con.commit(); con.close()
        payload = server._voice_payload_from_history("vm1")
        self.assertEqual(payload["from"], "alice")
        self.assertTrue(payload["voice"]["voicemail"])
        self.assertEqual(base64.b64decode(payload["voice"]["b64"]), mp3)
        sent = []
        with mock.patch.object(server, "_send_json_line", lambda sock, p: sent.append(p)):
            server._deliver_pending_voicemail(object(), "BOB")
        self.assertEqual(len(sent), 1)
        con = sqlite3.connect(server.DB)
        self.assertEqual(con.execute("SELECT count(*) FROM pending_voicemail").fetchone()[0], 0)
        con.close()
        ok, reason, _ = server._apply_direct_message_change("alice", "vm1", False)
        self.assertTrue(ok, reason)
        self.assertFalse(os.path.exists(path))

    def test_emoji_survive_history_and_edit(self):
        text = "Hi 👋🏽 family: 👨‍👩‍👧 flags 🇺🇸 and ❤️"
        server._record_direct_message_history("alice", "bob", text, msg_uid="e1")
        edited = text + " 🎉"
        self.assertTrue(server._apply_direct_message_change("alice", "e1", True, edited)[0])
        con = sqlite3.connect(server.DB)
        body = con.execute("SELECT body FROM direct_message_history WHERE msg_uid='e1'").fetchone()[0]
        con.close()
        self.assertEqual(body, edited)


if __name__ == "__main__":
    unittest.main()
