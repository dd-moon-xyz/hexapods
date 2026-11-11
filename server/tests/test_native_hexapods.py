import os
import struct
import subprocess
import unittest
from contextlib import contextmanager

from PIL import Image

from lenia.server.worker import ROOT


@contextmanager
def worker(mode: str, count: int, dt: float, interactions: int = 1):
    with subprocess.Popen([str(ROOT / "build/lenia"), mode], stdin=subprocess.PIPE, stdout=subprocess.PIPE) as process:
        process.stdin.write((f"256 60 {dt} 2 {count} {interactions} {interactions}\n" + "1 128 128\n" * count).encode())
        process.stdin.flush()
        if process.stdout.readline() != b"READY\n":
            raise RuntimeError("CUDA worker failed to start")

        if mode == "--stream-hexapod":
            masses, image = frame(process, count)
            assert all(mass <= .001 for mass in masses)
            assert image.getbbox() is None
            for index in range(count):
                process.stdin.write(f"r {index} 1 128 128 0\n".encode())
                process.stdin.flush()
                assert process.stdout.readline() == b"READY\n"

        yield process


def frame(process, count: int, size: int = 256):
    process.stdin.write(b"n")
    process.stdin.flush()
    masses = struct.unpack(f"={count}f", process.stdout.read(count * 4))
    image = Image.frombytes("RGB", (size, size), process.stdout.read(size * size * 3))
    return masses, image


@unittest.skipUnless(os.environ.get("LENIA_GPU_TESTS") == "1", "Requires CUDA GPU")
class NativeHexapodTests(unittest.TestCase):
    def test_vector_escape_kills_at_edge_and_inward_does_not_revive(self):
        with worker("--stream-hexapod", 1, .2) as process:
            process.stdin.write(b'v -1 0 0 1\n')
            process.stdin.flush()
            self.assertEqual(process.stdout.readline(), b'READY\n')
            entered = False
            for _ in range(1200):
                _, image = frame(process, 1)
                bounds = image.getbbox()
                if bounds and 64 < (bounds[0] + bounds[2]) / 2 < 192:
                    entered = True
                    break

            self.assertTrue(entered)
            for command in (b'v 1 0 1 2\n', b'v 0 -1 1 2\n', b'v -0.6 0.8 0 1\n', b'v 1 0 1 2\n'):
                process.stdin.write(command)
                process.stdin.flush()
                self.assertEqual(process.stdout.readline(), b'READY\n')
                masses, _ = frame(process, 1)
                self.assertGreater(masses[0], .001)
            for _ in range(1200):
                masses, image = frame(process, 1)
            self.assertLessEqual(masses[0], .001)
            self.assertIsNone(image.getbbox())
            process.stdin.write(b'v 1 0 1 1\n')
            process.stdin.flush()
            self.assertEqual(process.stdout.readline(), b'READY\n')
            for _ in range(10):
                _, image = frame(process, 1)
                self.assertIsNone(image.getbbox())
            process.stdin.write(b'i')
            process.stdin.flush()
            self.assertEqual(process.stdout.readline(), b'READY\n')
            for _ in range(20):
                masses, _ = frame(process, 1)
                self.assertLessEqual(masses[0], .001)

    def test_resized_frames_preserve_metadata_and_command_alignment(self):
        with worker("--stream-hexapod", 1, .1) as process:
            for size in (120, 1, 256):
                process.stdin.write(f"s {size}\n".encode())
                process.stdin.flush()
                self.assertEqual(process.stdout.readline(), b"READY\n")
                for _ in range(2):
                    masses, image = frame(process, 1, size)
                    self.assertEqual(image.size, (size, size))
                    self.assertGreater(masses[0], 0)
                process.stdin.write(b"i")
                process.stdin.flush()
                self.assertEqual(process.stdout.readline(), b"READY\n")

    def test_continuous_contact_only_consumes_one_interaction(self):
        with worker("--stream-hexapod-preview", 2, .005, interactions=2) as process:
            for _ in range(200):
                masses, _ = frame(process, 2)

            self.assertTrue(all(value > .001 for value in masses))

    def test_overlapping_bodies_fade_to_death(self):
        with worker("--stream-hexapod-preview", 2, .005) as process:
            initial, _ = frame(process, 2)
            for _ in range(2000):
                masses, _ = frame(process, 2)
                if max(masses) <= .001:
                    break

            self.assertTrue(all(value > 0 for value in initial))
            self.assertTrue(all(value <= .001 for value in masses))

    def test_isolated_body_survives_and_replacement_enters_from_edge(self):
        with worker("--stream-hexapod", 1, .2) as process:
            for _ in range(100):
                masses, _ = frame(process, 1)

            self.assertGreater(masses[0], .001)
            process.stdin.write(b"r 0 1 128 128 0\n")
            process.stdin.flush()
            self.assertEqual(process.stdout.readline(), b"READY\n")
            masses, image = frame(process, 1)
            self.assertGreater(masses[0], .001)
            self.assertIsNone(image.getbbox())
            entered = False
            for _ in range(300):
                masses, image = frame(process, 1)
                entered = entered or image.getbbox() is not None

            self.assertGreater(masses[0], .001)
            self.assertTrue(entered)
