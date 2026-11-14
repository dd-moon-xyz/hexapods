import asyncio
import io
import json
from importlib.resources import files
from itertools import cycle
from zipfile import ZipFile

import pygame

from client_core.rendering import Viewer


def load_animation() -> tuple[float, tuple[bytes, ...]]:
    with files("client_core").joinpath("assets/single-hexapod.zip").open("rb") as source, ZipFile(source) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        return float(manifest["fps"]), tuple(archive.read(name) for name in manifest["frames"])


async def display_fallback(viewer: Viewer, connected: asyncio.Event) -> None:
    fps, frames = await asyncio.to_thread(load_animation)
    loop = asyncio.get_running_loop()
    deadline = loop.time()
    for frame in cycle(frames):
        if not connected.is_set():
            image = await asyncio.to_thread(pygame.image.load, io.BytesIO(frame), "frame.jpg")
            if not connected.is_set():
                viewer.draw(image)

        deadline = max(deadline + 1 / fps, loop.time())
        await asyncio.sleep(max(0, deadline - loop.time()))
