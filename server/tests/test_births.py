import asyncio
import math
import unittest
from unittest.mock import AsyncMock, patch

from lenia.server.arena import CircularArena
from lenia.server.models import Start


class FakeWorker:
    def __init__(self, config, mass=0.0):
        self.config = config
        self.frame_size = config.size
        self.masses = (mass,)
        self.replacements = ()

    async def redirect(self, outward, boosted=False):
        pass

    async def frame(self):
        return bytes(self.config.size ** 2 * 3)

    async def replace_organism(self, index, organism, angle):
        await asyncio.sleep(0)
        self.replacements = (*self.replacements, (index, organism, angle))
        self.masses = (100.0,)


class BirthTests(unittest.IsolatedAsyncioTestCase):
    def config(self):
        return Start.model_validate({"action": "start", "boundary": "circle", "fps": 60, "birth_rate_min": 5, "birth_rate_max": 10, "organisms": [{}]})

    async def test_concurrent_births_are_spaced_by_random_bounded_delays(self):
        config = Start.model_validate({"action": "start", "organisms": [{}], "birth_rate_min": 2, "birth_rate_max": 4})
        arena = CircularArena(config, FakeWorker(config))
        times = {}

        async def record(index):
            times[index] = asyncio.get_running_loop().time()

        arena._replace = AsyncMock(side_effect=record)
        try:
            with patch("lenia.server.arena.random.uniform", side_effect=(0.25, 0.5, 0.25)) as delay:
                await asyncio.gather(*(arena.replace(index) for index in range(3)))

            self.assertEqual(delay.call_args_list, [((0.25, 0.5),)] * 3)
            self.assertGreaterEqual(times[1] - times[0], 0.5)
            self.assertGreaterEqual(times[2] - times[1], 0.25)
        finally:
            await arena.close()

    async def test_dead_organism_sends_random_boundary_birth_to_native_worker(self):
        config = self.config()
        worker = FakeWorker(config)
        arena = CircularArena(config, worker)
        try:
            for _ in range(20):
                await arena.frame()

            self.assertEqual(len(worker.replacements), 1)
            index, organism, angle = worker.replacements[0]
            self.assertEqual(index, 0)
            self.assertEqual(organism.scale, 1)
            self.assertGreaterEqual(angle, 0)
            self.assertLessEqual(angle, 2 * math.pi)
        finally:
            await arena.close()

    async def test_dead_hexapod_is_replaced_with_hexapod(self):
        config = Start.model_validate({"action": "start", "simulation": "hexapod", "boundary": "circle", "fps": 60, "birth_rate_min": 5, "birth_rate_max": 10, "organisms": [{}]})
        worker = FakeWorker(config)
        arena = CircularArena(config, worker)
        try:
            for _ in range(20):
                await arena.frame()

            self.assertEqual(len(worker.replacements), 1)
            self.assertEqual(worker.replacements[0][1].scale, 1)
        finally:
            await arena.close()

    async def test_hidden_but_living_organism_is_not_replaced(self):
        config = self.config()
        worker = FakeWorker(config, mass=100.0)
        arena = CircularArena(config, worker)
        try:
            for _ in range(20):
                await arena.frame()

            self.assertFalse(worker.replacements)
        finally:
            await arena.close()

    async def test_pending_replacement_is_cancelled_on_close(self):
        config = self.config()
        worker = FakeWorker(config)
        entered = asyncio.Event()

        async def replace(index, organism, angle):
            entered.set()
            await asyncio.Event().wait()

        worker.replace_organism = replace
        arena = CircularArena(config, worker)
        for _ in range(5):
            await arena.frame()

        await asyncio.wait_for(entered.wait(), 1)
        await arena.close()
        self.assertTrue(all(task.cancelled() for task in arena.pending.values()))

    async def test_outward_pauses_births_until_either_inward_command(self):
        for boosted in (False, True):
            with self.subTest(boosted=boosted):
                worker = FakeWorker(self.config())
                arena = CircularArena(self.config(), worker)
                try:
                    await arena.redirect(True, boosted)
                    for _ in range(7):
                        await arena.frame()

                    self.assertFalse(worker.replacements)
                    self.assertFalse(arena.pending)
                    await arena.redirect(False, boosted)
                    for _ in range(15):
                        await arena.frame()

                    self.assertEqual(len(worker.replacements), 1)
                finally:
                    await arena.close()

    async def test_queued_replacement_checks_current_direction(self):
        config = self.config()
        worker = FakeWorker(config)
        arena = CircularArena(config, worker)
        try:
            # A birth task created during the last inward frame may still be queued.
            await arena.birth_lock.acquire()
            redirect = asyncio.create_task(arena.redirect(True, True))
            await asyncio.sleep(0)
            birth = asyncio.create_task(arena.replace(0))
            arena.birth_lock.release()
            await redirect
            await birth
            self.assertFalse(worker.replacements)
        finally:
            await arena.close()

