import asyncio
import struct
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from lenia.server.arena import CircularArena
from lenia.server.models import Organism, Start

__all__ = ["ROOT", "SimulationWorker", "simulation_worker"]

ROOT = Path(__file__).resolve().parents[3]


class SimulationWorker:
    def __init__(self, process: asyncio.subprocess.Process, config: Start):
        self.process = process
        self.config = config
        self.frame_size = config.size
        self.masses = ()
        self.lock = asyncio.Lock()

    def organism_line(self, item: Organism) -> str:
        return f"{item.scale} {item.x} {item.y}"

    async def ready(self) -> None:
        await self.process.stdin.drain()
        async with asyncio.timeout(30):
            ready = await self.process.stdout.readline()

        if ready != b"READY\n":
            raise RuntimeError(
                "Simulation failed to start; check server logs and CUDA setup"
            )

    async def start(self) -> None:
        header = f"{self.config.size} {self.config.fps} {self.config.dt} {self.config.space_speed_multiplier} {len(self.config.organisms)} {self.config.interaction_count_min} {self.config.interaction_count_max}\n"
        organisms = "".join(
            f"{self.organism_line(item)}\n" for item in self.config.organisms
        )

        self.process.stdin.write((header + organisms).encode())
        await self.ready()
        if (
            self.config.pixel_size == 1
            and self.config.output_size is not None
            and self.config.output_size < self.config.size
        ):
            self.process.stdin.write(f"s {self.config.output_size}\n".encode())
            try:
                await self.ready()
            except RuntimeError as error:
                raise RuntimeError("GPU output resizing failed; rebuild the native lenia executable") from error
            self.frame_size = self.config.output_size

    async def frame(self) -> bytes:
        async with self.lock:
            self.process.stdin.write(b"n")
            await self.process.stdin.drain()
            async with asyncio.timeout(30):
                count = len(self.config.organisms)
                metadata = await self.process.stdout.readexactly(4 * count)
                self.masses = struct.unpack(f"={count}f", metadata)

                raw = await self.process.stdout.readexactly(
                    self.frame_size * self.frame_size * 3
                )

        return raw

    async def replace_organism(
        self, index: int, organism: Organism, angle: float
    ) -> None:
        async with self.lock:
            command = f"r {index} {self.organism_line(organism)} {angle}\n"
            self.process.stdin.write(command.encode())
            await self.ready()

    async def movement(self, outward: bool, speed_multiplier: float) -> None:
        async with self.lock:
            self.process.stdin.write(f"m {int(outward)} {speed_multiplier}\n".encode())
            try:
                await self.ready()
            except RuntimeError as error:
                raise RuntimeError("Movement command failed; rebuild the native lenia executable") from error

    async def steer_vector(self, x: float, y: float, escape: bool, speed_multiplier: float) -> None:
        async with self.lock:
            self.process.stdin.write(f"v {x} {y} {int(escape)} {speed_multiplier}\n".encode())
            try:
                await self.ready()
            except RuntimeError as error:
                raise RuntimeError("Vector movement failed; rebuild the native lenia executable") from error

    async def redirect(self, outward: bool, boosted: bool = False) -> None:
        async with self.lock:
            self.process.stdin.write(
                (b"o" if boosted else b"u") if outward else (b"b" if boosted else b"i")
            )
            await self.ready()

    async def close(self) -> None:
        if self.process.returncode is None:
            with suppress(ProcessLookupError):
                self.process.kill()

        await self.process.wait()


@asynccontextmanager
async def simulation_worker(
    config: Start,
) -> AsyncIterator[CircularArena]:
    process = await asyncio.create_subprocess_exec(
        str(ROOT / "build/lenia"),
        "--stream-hexapod",
        cwd=ROOT / "build",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
    )

    worker = SimulationWorker(process, config)
    arena = CircularArena(config, worker)
    try:
        await worker.start()
        yield arena
    finally:
        await arena.close()
        await worker.close()
