import asyncio
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pygame
from websockets.asyncio.server import serve

from client_core.preview import capture, record


def jpeg(point=None):
    surface = pygame.Surface((32, 32))
    surface.fill((0, 0, 0))
    if point is not None:
        pygame.draw.rect(surface, (255, 255, 255), (*point, 4, 4))

    stream = io.BytesIO()
    pygame.image.save(surface, stream, "frame.jpg")
    return stream.getvalue()


class PreviewTests(unittest.IsolatedAsyncioTestCase):
    async def test_capture_waits_for_center_crossing_and_full_exit(self):
        images = (jpeg(), jpeg((0, 0)), jpeg(), jpeg((14, 14)), jpeg((28, 28)), jpeg())
        async def server(websocket):
            self.assertEqual(websocket.request.headers["Authorization"], "Bearer preview-test-token")
            config = json.loads(await websocket.recv())
            self.assertTrue(config["preview"])
            self.assertEqual(len(config["organisms"]), 1)
            await websocket.send(json.dumps({"status": "started", "fps": 60}))
            for image in images:
                self.assertEqual(await websocket.recv(), "next")
                await websocket.send(image)

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            async with serve(server, "127.0.0.1", 0) as listener:
                port = listener.sockets[0].getsockname()[1]
                manifest = await asyncio.wait_for(capture(f"ws://127.0.0.1:{port}", directory, "preview-test-token"), 5)

            self.assertEqual(tuple((directory / name).read_bytes() for name in manifest["frames"]), images[1:])

    async def test_server_error_preserves_previous_recording(self):
        async def server(websocket):
            await websocket.recv()
            await websocket.send(json.dumps({"error": "preview unavailable"}))

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "saved"
            directory.mkdir()
            (directory / "manifest.json").write_text('{"frames":["old.jpg"]}')
            (directory / "animation.mp4").write_bytes(b"previous video")
            async with serve(server, "127.0.0.1", 0) as listener:
                port = listener.sockets[0].getsockname()[1]
                with patch("client_core.preview.shutil.which", return_value="ffmpeg"):
                    with self.assertRaisesRegex(ValueError, "preview unavailable"):
                        await record(f"ws://127.0.0.1:{port}", directory)

            self.assertEqual((directory / "animation.mp4").read_bytes(), b"previous video")
            self.assertEqual(json.loads((directory / "manifest.json").read_text()), {"frames": ["old.jpg"]})

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "Requires FFmpeg")
    async def test_record_encodes_complete_cycle_to_mp4(self):
        images = (jpeg(), jpeg((0, 0)), jpeg((14, 14)), jpeg((28, 28)), jpeg())

        async def server(websocket):
            await websocket.recv()
            await websocket.send(json.dumps({"status": "started", "fps": 60}))
            for image in images:
                await websocket.recv()
                await websocket.send(image)

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "saved"
            async with serve(server, "127.0.0.1", 0) as listener:
                port = listener.sockets[0].getsockname()[1]
                manifest = await record(f"ws://127.0.0.1:{port}", directory)

            process = await asyncio.create_subprocess_exec(
                "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                "stream=nb_frames,width,height,r_frame_rate", "-of", "json", str(directory / "animation.mp4"),
                stdout=asyncio.subprocess.PIPE,
            )

            output, _ = await process.communicate()
            stream = json.loads(output)["streams"][0]
            self.assertEqual(process.returncode, 0)
            self.assertEqual(stream["nb_frames"], str(len(images) - 1))
            self.assertEqual((stream["width"], stream["height"], stream["r_frame_rate"]), (32, 32, "60/1"))
            self.assertEqual(json.loads((directory / "manifest.json").read_text())["frames"], list(manifest["frames"]))
