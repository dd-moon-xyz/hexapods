import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from websockets.asyncio.server import serve

from client_core.replay import record


class CaptureTests(unittest.IsolatedAsyncioTestCase):
    async def test_capture_preserves_previous_manifest_when_server_stops(self):
        async def server(websocket):
            await websocket.recv()
            await websocket.send(json.dumps({'status': 'started', 'fps': 10}))
            await websocket.recv()
            await websocket.recv()
            await websocket.send(b'new')
            await websocket.recv()
            await websocket.send(json.dumps({'status': 'stopped'}))

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / 'recording'
            directory.mkdir()
            manifest = {'fps': 10, 'frames': ['old.jpg']}
            (directory / 'manifest.json').write_text(json.dumps(manifest))
            (directory / 'old.jpg').write_bytes(b'old')
            async with serve(server, '127.0.0.1', 0) as listener:
                port = listener.sockets[0].getsockname()[1]
                with self.assertRaisesRegex(ValueError, 'stopped'):
                    await asyncio.wait_for(record(f'ws://127.0.0.1:{port}', {}, directory, 1), 5)

            self.assertEqual(json.loads((directory / 'manifest.json').read_text()), manifest)
            self.assertEqual((directory / 'old.jpg').read_bytes(), b'old')

    async def test_capture_publishes_complete_frames(self):
        async def server(websocket):
            await websocket.recv()
            await websocket.send(json.dumps({'status': 'started', 'fps': 2}))
            await websocket.recv()
            await websocket.recv()
            await websocket.send(b'first')
            await websocket.recv()
            await websocket.send(b'second')

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            async with serve(server, '127.0.0.1', 0) as listener:
                port = listener.sockets[0].getsockname()[1]
                manifest = await asyncio.wait_for(record(f'ws://127.0.0.1:{port}', {}, directory, 1), 5)

            self.assertEqual(tuple((directory / name).read_bytes() for name in manifest['frames']), (b'first', b'second'))
            self.assertEqual(json.loads((directory / 'manifest.json').read_text()), {'fps': 2, 'frames': list(manifest['frames'])})
