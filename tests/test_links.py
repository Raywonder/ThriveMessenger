import unittest

try:
    import main
except Exception:
    main = None


@unittest.skipIf(main is None, "main.py needs wxPython (or a stub) to import")
class FindLinksTests(unittest.TestCase):
    def test_same_rules_as_the_server(self):
        text = "see https://example.com/a?b=1, www.test.org and blind.software. Not server.py or a@mail.com. https://example.com/a?b=1"
        self.assertEqual([l["url"] for l in main.find_links(text)],
                         ["https://example.com/a?b=1", "https://www.test.org", "https://blind.software"])

    def test_plain_file_names_and_versions_are_not_links(self):
        self.assertEqual(main.find_links("main.py and notes.txt, v1.2.3"), [])

    def test_trailing_punctuation_is_not_part_of_the_link(self):
        self.assertEqual(main.find_links("Go to https://im.tappedin.fm/downloads!")[0]["raw"], "https://im.tappedin.fm/downloads")


if __name__ == "__main__":
    unittest.main()
