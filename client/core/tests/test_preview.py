import asyncio
import io
import json
import tempfile
import unittest
from pathlib import Path

import pygame
from websockets.asyncio.server import serve

from client_core.preview import capture


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
            self.assertEqual(config["size"], 1024)
            self.assertEqual(config["fps"], 120)
            self.assertEqual(config["dt"], 0.1)
            self.assertNotIn("output_size", config)
            self.assertEqual(len(config["organisms"]), 1)
            await websocket.send(json.dumps({"status": "started", "fps": 120}))
            for image in images:
                self.assertEqual(await websocket.recv(), "next")
                await websocket.send(image)

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            async with serve(server, "127.0.0.1", 0) as listener:
                port = listener.sockets[0].getsockname()[1]
                manifest = await asyncio.wait_for(capture(f"ws://127.0.0.1:{port}", directory, "preview-test-token"), 5)

            self.assertEqual(manifest["fps"], 120)
            self.assertEqual(tuple((directory / name).read_bytes() for name in manifest["frames"]), images[1:])
