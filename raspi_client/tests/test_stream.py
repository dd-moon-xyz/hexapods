import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from websockets.asyncio.server import serve

from lenia_client.client import display_stream


class StreamTests(unittest.IsolatedAsyncioTestCase):
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
            with patch("lenia_client.client.display_frame") as draw:
                await asyncio.wait_for(
                    display_stream(f"ws://127.0.0.1:{port}", config, None, asyncio.Queue()),
                    timeout=5,
                )

        self.assertEqual(received, [config, *(["next"] * 5)])
        self.assertEqual([call.args[1] for call in draw.call_args_list], [b"first", b"second", b"third"])

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
            self.assertEqual(await websocket.recv(), "next")
            await websocket.send(json.dumps({"status": "stopped"}))

        async with serve(server, "127.0.0.1", 0) as listener:
            port = listener.sockets[0].getsockname()[1]
            with patch("lenia_client.client.display_frame"):
                await asyncio.wait_for(display_stream(f"ws://127.0.0.1:{port}", {}, None, commands), 5)
        self.assertEqual(received, [movement])


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

        with patch('lenia_client.client.connect') as connect, patch('lenia_client.client.display_frame') as draw:
            connect.return_value.__aenter__.return_value = websocket
            draw.side_effect = lambda *_: self.assertEqual(population['fraction'], .3)
            asyncio.run(display_stream('ws://test/ws', {}, None, asyncio.Queue(), population))

        self.assertTrue(json.loads(websocket.send.call_args_list[0].args[0])['population_updates'])
        draw.assert_called_once_with(None, b'frame')


if __name__ == "__main__":
    unittest.main()
