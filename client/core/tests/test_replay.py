import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pygame

from client_core.replay import replay


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
                patch("client_core.replay.pygame.image.load", side_effect=lambda stream, _: stream.getvalue()),
                patch("client_core.replay.time.monotonic", return_value=0),
                patch("client_core.replay.time.sleep") as sleep,
                patch("pygame.event.get", side_effect=[[], [], [], [pygame.event.Event(pygame.QUIT)]]),
            ):
                viewer = MagicMock()
                replay(viewer, directory, manifest)
            self.assertEqual([call.args[0] for call in viewer.draw.call_args_list], [b"a", b"b", b"a"])
            self.assertAlmostEqual(sleep.call_args_list[0].args[0], 1 / 60)


if __name__ == "__main__":
    unittest.main()
