import asyncio
import io
import unittest
from unittest.mock import MagicMock, patch

import pygame
from websockets.exceptions import InvalidHandshake

from client_core.client import reconnect
from client_core.fallback import display_fallback, load_animation


class FallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_bundled_animation_is_complete_and_decodable(self):
        fps, frames = load_animation()
        self.assertEqual(fps, 60)
        self.assertGreater(len(frames), 1)
        for frame in frames:
            self.assertEqual(pygame.image.load(io.BytesIO(frame), "frame.jpg").get_size(), (800, 800))

    async def test_fallback_draws_offline_and_yields_to_live_frames(self):
        connected = asyncio.Event()
        viewer = MagicMock()
        drawn = asyncio.Event()
        viewer.draw.side_effect = lambda frame: drawn.set()
        task = asyncio.create_task(display_fallback(viewer, connected))
        try:
            await asyncio.wait_for(drawn.wait(), 2)
            connected.set()
            count = viewer.draw.call_count
            await asyncio.sleep(.05)
            self.assertEqual(viewer.draw.call_count, count)
            drawn.clear()
            connected.clear()
            await asyncio.wait_for(drawn.wait(), 2)
            self.assertGreater(viewer.draw.call_count, count)
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def test_retries_preset_failure_rejection_timeout_and_clean_disconnect(self):
        connected = asyncio.Event()
        restored = asyncio.Event()
        attempts = 0
        pause = asyncio.sleep

        async def retry_delay(seconds):
            self.assertEqual(seconds, 3)
            await pause(0)

        async def stream(url, config, commands, viewer, record, population, token, live):
            nonlocal attempts
            self.assertFalse(live.is_set())
            self.assertEqual(config, {"action": "start"})
            self.assertEqual(token, "test-token")
            attempts += 1
            if attempts == 1:
                raise InvalidHandshake("HTTP 429")
            if attempts == 2:
                raise TimeoutError("no frames")
            if attempts == 3:
                live.set()
                return

            live.set()
            restored.set()
            await asyncio.Future()

        with (
            patch("client_core.client.load_preset", side_effect=[OSError("offline"), *({"action": "start"} for _ in range(4))]) as preset,
            patch("client_core.client.display_stream", side_effect=stream),
            patch("client_core.client.asyncio.sleep", side_effect=retry_delay),
        ):
            task = asyncio.create_task(reconnect(
                "ws://unused/ws", None, asyncio.Queue(), MagicMock(), connected, token="test-token",
            ))

            try:
                await asyncio.wait_for(restored.wait(), 2)
                self.assertTrue(connected.is_set())
                self.assertEqual(preset.call_count, 5)
                self.assertEqual(attempts, 4)
            finally:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

        self.assertFalse(connected.is_set())
