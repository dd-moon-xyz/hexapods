import asyncio
import logging
import math
import random

from lenia.server.frames import encode_frame
from lenia.server.models import Organism, Start

__all__ = ["CircularArena"]


class CircularArena:
    def __init__(self, config: Start, worker):
        self.config = config
        self.worker = worker
        self.organisms = list(config.organisms)
        self.dead_frames = [0] * len(config.organisms)
        self.pending = {}
        self.deadline = None
        self.outward = False
        self.birth_lock = asyncio.Lock()
        self.birth_rate_lock = asyncio.Lock()

    async def frame(self) -> bytes:
        loop = asyncio.get_running_loop()
        started = loop.time()
        for index, task in tuple(self.pending.items()):
            if task.done():
                await task
                del self.pending[index]

        raw = await self.worker.frame()
        for index, mass in enumerate(self.worker.masses):
            if index in self.pending:
                continue

            self.dead_frames[index] = (
                self.dead_frames[index] + 1 if mass <= 0.001 else 0
            )

            if self.dead_frames[index] >= 5 and not self.outward:
                self.pending[index] = asyncio.create_task(self.replace(index))

        frame = await asyncio.to_thread(
            encode_frame, raw, self.worker.frame_size, self.config.pixel_size,
            self.config.output_size,
        )
        interval = 1 / self.config.fps
        if self.deadline is None or started - self.deadline > interval:
            self.deadline = started

        self.deadline += interval
        await asyncio.sleep(max(0, self.deadline - loop.time()))
        return frame

    async def replace(self, index: int) -> None:
        async with self.birth_rate_lock:
            await asyncio.sleep(random.uniform(1 / self.config.birth_rate_max, 1 / self.config.birth_rate_min))
            # Keep steering responsive while a birth waits for its turn.
            async with self.birth_lock:
                if not self.outward:
                    await self._replace(index)

    async def _replace(self, index: int) -> None:
        logger = logging.getLogger("uvicorn.error")
        logger.info(
            "Hexapod died: slot=%s", index
        )
        organism = Organism(scale=1)
        self.organisms[index] = organism
        angle = random.uniform(0, 2 * math.pi)
        await self.worker.replace_organism(index, organism, angle)
        self.dead_frames[index] = 0
        logger.info(
            "Hexapod born outside visible circle: slot=%s scale=%s",
            index,
            organism.scale,
        )

    async def movement(self, outward: bool, speed_multiplier: float) -> None:
        async with self.birth_lock:
            await self.worker.movement(outward, speed_multiplier)
            self.outward = outward

    async def steer_vector(self, x: float, y: float, escape: bool, speed_multiplier: float) -> None:
        async with self.birth_lock:
            await self.worker.steer_vector(x, y, escape, speed_multiplier)
            # The existing birth gate represents escape, including vector escape.
            self.outward = escape

    async def redirect(self, outward: bool, boosted: bool = False) -> None:
        async with self.birth_lock:
            await self.worker.redirect(outward, boosted)
            self.outward = outward

    async def close(self) -> None:
        for task in self.pending.values():
            task.cancel()

        await asyncio.gather(*self.pending.values(), return_exceptions=True)
