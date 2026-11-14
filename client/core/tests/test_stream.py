import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from websockets.asyncio.server import serve

from client_core.client import display_stream


class StreamTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_frames_time_out_before_and_after_live_playback(self):
        for images in ((), (b"frame",)):
            async def messages():
                yield json.dumps({"status": "started", "size": 480, "fps": 60})
                for image in images:
                    yield image
                await asyncio.Future()

            websocket = MagicMock()
            websocket.send = AsyncMock()
            websocket.__aiter__.side_effect = messages
            connected = asyncio.Event()
            with (
                self.subTest(images=images),
                patch("client_core.client.connect") as connect,
                patch("client_core.client.FRAME_TIMEOUT", .01),
                patch("client_core.client.pygame.image.load"),
            ):
                connect.return_value.__aenter__.return_value = websocket
                with self.assertRaises(TimeoutError):
                    await display_stream("ws://unused/ws", {}, asyncio.Queue(), MagicMock(), connected=connected)

            self.assertEqual(connected.is_set(), bool(images))

    async def test_two_requests_are_primed_and_replenished(self):
        received = []
        config = {"action": "start", "output_size": 480}

        async def server(websocket):
            received.append(json.loads(await websocket.recv()))
            await websocket.send(json.dumps({"status": "started", "size": 480, "fps": 60}))
            # Both requests must arrive before the server delivers any frame.
            for _ in range(2):
                received.append(await websocket.recv())
            for frame in (b"first", b"second", b"third"):
                await websocket.send(frame)
                received.append(await websocket.recv())
            await websocket.send(json.dumps({"status": "stopped"}))

        async with serve(server, "127.0.0.1", 0) as listener:
            port = listener.sockets[0].getsockname()[1]
            viewer = MagicMock()
            with patch("client_core.client.pygame.image.load", side_effect=lambda stream, _: stream.getvalue()):
                await asyncio.wait_for(
                    display_stream(f"ws://127.0.0.1:{port}", config, asyncio.Queue(), viewer),
                    timeout=5,
                )

        self.assertEqual(received, [config, *(["next"] * 5)])
        self.assertEqual([call.args[0] for call in viewer.draw.call_args_list], [b"first", b"second", b"third"])

    async def test_structured_movement_is_sent_as_websocket_json(self):
        movement = {"action": "movement", "direction": "vector", "vector": {"x": -.6, "y": .8},
                    "escape": True, "speed_multiplier": 1.5}
        commands = asyncio.Queue()
        commands.put_nowait({"action": "movement", "direction": "outward", "speed_multiplier": 1.0})
        commands.put_nowait(movement)
        received = []

        async def server(websocket):
            await websocket.recv()
            await websocket.send(json.dumps({"status": "started", "size": 480, "fps": 60}))
            await websocket.recv()
            await websocket.recv()
            await websocket.send(b"frame")
            received.append(json.loads(await websocket.recv()))
            received.append(json.loads(await websocket.recv()))
            self.assertEqual(await websocket.recv(), "next")
            await websocket.send(json.dumps({"status": "stopped"}))

        async with serve(server, "127.0.0.1", 0) as listener:
            port = listener.sockets[0].getsockname()[1]
            with patch("client_core.client.pygame.image.load", return_value=None):
                await asyncio.wait_for(display_stream(f"ws://127.0.0.1:{port}", {}, commands, MagicMock()), 5)
        self.assertEqual(received[-1], movement)


class PopulationStreamTests(unittest.TestCase):
    def test_population_reports_reach_shared_sensor_state(self):
        population = {'fraction': 1.0}
        websocket = MagicMock()
        websocket.send = AsyncMock()
        websocket.__aiter__.return_value = (
            json.dumps({'status': 'started', 'size': 480, 'fps': 60}),
            json.dumps({'status': 'population', 'alive': 3, 'total': 10}),
            b'frame',
            json.dumps({'status': 'stopped'}),
        )

        with patch('client_core.client.connect') as connect, patch('client_core.client.pygame.image.load'):
            viewer = MagicMock()
            connect.return_value.__aenter__.return_value = websocket
            viewer.draw.side_effect = lambda *_: self.assertEqual(population['fraction'], .3)
            asyncio.run(display_stream('ws://test/ws', {}, asyncio.Queue(), viewer, population=population))

        self.assertTrue(json.loads(websocket.send.call_args_list[0].args[0])['population_updates'])
        viewer.draw.assert_called_once()


if __name__ == "__main__":
    unittest.main()
