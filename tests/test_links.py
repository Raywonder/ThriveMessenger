import socket
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock

from srv import server


class FindLinksTests(unittest.TestCase):
    def test_finds_scheme_and_familiar_bare_links_once_each(self):
        text = "see https://example.com/a?b=1, www.test.org and blind.software. Not server.py or a@mail.com. https://example.com/a?b=1"
        links = server._find_links(text)
        self.assertEqual([l["url"] for l in links],
                         ["https://example.com/a?b=1", "https://www.test.org", "https://blind.software"])
        self.assertEqual(links[2]["raw"], "blind.software")

    def test_no_links(self):
        self.assertEqual(server._find_links("main.py and notes.txt, v1.2.3"), [])


class TitleSafetyTests(unittest.TestCase):
    def test_private_and_odd_addresses_are_refused_without_connecting(self):
        with mock.patch.object(server.socket, "create_connection", side_effect=AssertionError("must not connect")):
            for url in ("http://127.0.0.1/", "http://localhost/", "http://10.0.0.5/", "http://192.168.1.1/",
                        "http://100.64.0.2/", "http://169.254.169.254/latest/meta-data/", "http://[::1]/",
                        "file:///etc/passwd", "ftp://example.com/", "http://user:pw@example.com/",
                        "http://example.com:22/", "gopher://example.com/"):
                self.assertEqual(server._fetch_link_title(url), "", url)

    def test_name_resolving_to_private_is_refused(self):
        fake = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.1.2.3", 80))]
        with mock.patch.object(server.socket, "getaddrinfo", return_value=fake), \
                mock.patch.object(server.socket, "create_connection", side_effect=AssertionError("must not connect")):
            self.assertEqual(server._fetch_link_title("http://evil.example/"), "")

    def test_redirect_to_private_is_refused(self):
        class H(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(302)
                self.send_header("Location", "http://127.0.0.1:8080/secret")
                self.end_headers()

            def log_message(self, *a):
                pass
        httpd = HTTPServer(("127.0.0.1", 0), H)
        port = httpd.server_address[1]
        threading.Thread(target=httpd.handle_request, daemon=True).start()
        # Pretend the first hop is public (it's our local test server), then check the redirect is re-vetted.
        real = server._link_public_ips
        calls = []

        def vet(host, p):
            calls.append(host)
            return ["127.0.0.1"] if host == "public.example" else real(host, p)
        with mock.patch.object(server, "_link_public_ips", vet), mock.patch.object(server, "LINK_TITLE_PORTS", {port, 8080}):
            self.assertEqual(server._fetch_link_title(f"http://public.example:{port}/"), "")
        httpd.server_close()
        self.assertEqual(calls, ["public.example", "127.0.0.1"])

    def test_title_parsing(self):
        self.assertEqual(server._parse_html_title(b"<html><title> Hello &amp;\n world </title>", "text/html"), "Hello & world")
        self.assertEqual(server._parse_html_title(b'<meta property="og:title" content="OG Title"><title>x</title>', ""), "OG Title")


class LinkListAndRemoveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.orig = server.DB
        server.DB = str(Path(self.tmp.name) / "s.db")
        server.init_db()
        server._record_direct_message_history("alice", "bob", "look https://a.example/x and www.b.org", delivered=True, msg_uid="m1")
        server._record_direct_message_history("bob", "alice", "mine: https://c.example", delivered=True, msg_uid="m2")
        server._record_direct_message_history("carol", "dave", "private https://d.example", delivered=True, msg_uid="m3")
        server._store_link_title("https://a.example/x", "Page A")

    def tearDown(self):
        server.DB = self.orig
        self.tmp.cleanup()

    def test_list_is_only_your_conversations_with_titles(self):
        items = server._links_list("alice")
        self.assertEqual({i["url"] for i in items}, {"https://a.example/x", "https://www.b.org", "https://c.example"})
        self.assertEqual([i["title"] for i in items if i["url"] == "https://a.example/x"], ["Page A"])
        self.assertEqual(server._links_list("alice", "carol"), [])
        self.assertEqual(len(server._links_list("bob", "alice")), 3)

    def test_only_sender_or_admin_removes_and_everyone_is_told(self):
        pushed = []
        with mock.patch.object(server, "_send_to_all_sessions", lambda users, p: pushed.append((set(users), p))), \
                mock.patch.object(server, "_is_admin", lambda u: u == "boss"):
            self.assertEqual(server._remove_links("bob", [{"id": "m1"}]), (0, ["m1"]))
            self.assertEqual(server._remove_links("alice", [{"id": "m1", "raw": ["www.b.org"]}]), (1, []))
            self.assertEqual(server._remove_links("boss", [{"id": "m2"}]), (1, []))
        self.assertEqual(pushed[0][1]["msg"], "look https://a.example/x and [link removed]")
        self.assertEqual(pushed[0][0], {"alice", "bob"})
        self.assertEqual(pushed[1][1]["msg"], "mine: [link removed]")
        self.assertEqual(len(server._links_list("alice")), 1)


if __name__ == "__main__":
    unittest.main()
