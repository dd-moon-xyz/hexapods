import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pygame

from lenia_client.replay import replay


class ReplayTests(unittest.TestCase):
    def test_capture_pauses_are_ignored_and_frames_loop(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "a.jpg").write_bytes(b"a")
            (directory / "b.jpg").write_bytes(b"b")
            manifest = {"duration": 30, "frames": [
                {"file": "a.jpg", "time": 0},
                {"file": "b.jpg", "time": 20},
            ]}
            with (
                patch("lenia_client.replay.display_frame") as draw,
                patch("lenia_client.replay.time.monotonic", return_value=0),
                patch("lenia_client.replay.time.sleep") as sleep,
                patch("pygame.event.get", side_effect=[[], [], [], [pygame.event.Event(pygame.QUIT)]]),
            ):
                replay(None, directory, manifest)
            self.assertEqual([call.args[1] for call in draw.call_args_list], [b"a", b"b", b"a"])
            self.assertAlmostEqual(sleep.call_args_list[0].args[0], 1 / 60)


if __name__ == "__main__":
    unittest.main()
