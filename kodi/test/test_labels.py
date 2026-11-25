# ./labels.py without kodi (no xbmc in it): what a release or a download
# row says. run: python3 kodi/test/test_labels.py
import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = importlib.util.spec_from_file_location(
    "labels", os.path.join(HERE, "..", "moviepipe", "labels.py")
)
labels = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(labels)


class Dynamic(unittest.TestCase):
    def test_dolby_vision_and_hdr10(self):
        shown, rank = labels.dynamic("Film.2020.2160p.DV.HDR10.mkv", "Bluray-2160p")
        self.assertEqual(rank, 2)
        self.assertIn("DV", shown)
        self.assertIn("HDR10", shown)

    def test_hdr10_plus(self):
        _, rank = labels.dynamic("Film.2020.HDR10+.mkv", "Bluray-2160p")
        self.assertEqual(rank, 2)

    def test_sdr_up_to_1080p(self):
        shown, rank = labels.dynamic("Film.2019.1080p.BluRay", "Bluray-1080p")
        self.assertEqual(rank, 0)
        self.assertIn("SDR", shown)

    def test_2160p_without_a_tag_is_a_question(self):
        shown, rank = labels.dynamic("Film.2019.2160p.WEB-DL", "WEB-DL-2160p")
        self.assertEqual(rank, 1)
        self.assertIn("HDR?", shown)


class Quality(unittest.TestCase):
    def test_names_read_as_on_the_trackers(self):
        self.assertIn("BDRip 1080p", labels.quality("Bluray-1080p"))
        self.assertIn("WEB-DL 1080p", labels.quality("WEBDL-1080p"))
        self.assertEqual(labels.quality("HDTV-720p"), "HDTV 720p")


class Reason(unittest.TestCase):
    def test_short_reasons_once_each(self):
        self.assertEqual(
            labels.reason(
                [
                    "Not enough seeders",
                    "Not enough seeders",
                    "movie is not wanted in profile",
                ]
            ),
            "few seeders, quality not in profile",
        )

    def test_unknown_text_is_kept_short(self):
        self.assertEqual(
            labels.reason(["something else entirely, and long"]),
            "something else entirely, and long",
        )


class Age(unittest.TestCase):
    def test_units(self):
        self.assertEqual(labels.age(None), "")
        self.assertEqual(labels.age(0), "today")
        self.assertEqual(labels.age(3), "3 d")
        self.assertEqual(labels.age(60), "2 mo")
        self.assertEqual(labels.age(730), "2 y")


class Duration(unittest.TestCase):
    def test_units(self):
        self.assertEqual(labels.duration(None), "∞")
        self.assertEqual(labels.duration(0), "0 s")
        self.assertEqual(labels.duration(90), "1 min")
        self.assertEqual(labels.duration(3660), "1 h 01 min")
        self.assertEqual(labels.duration(90000), "1 d 1 h")


class Timeleft(unittest.TestCase):
    def test_servarrs_format(self):
        self.assertEqual(labels.timeleft("02:03:04"), 7384)
        self.assertEqual(labels.timeleft("1.02:03:04"), 93784)
        self.assertIsNone(labels.timeleft(""))
        self.assertIsNone(labels.timeleft(None))


class Speed(unittest.TestCase):
    def test_units(self):
        self.assertEqual(labels.speed(2048), "2 KB/s")
        self.assertEqual(labels.speed(1024**2), "1.0 MB/s")


if __name__ == "__main__":
    unittest.main()
