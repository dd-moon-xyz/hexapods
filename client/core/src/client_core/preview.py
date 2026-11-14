import asyncio
import io
import json
from pathlib import Path
from uuid import uuid4

import pygame
from tqdm import tqdm
from websockets.asyncio.client import connect

from client_core.auth import headers


async def capture(url: str, directory: Path, token: str | None = None) -> dict:
    with tqdm(desc="Capturing", unit="frame", ascii=True,
              colour="#808080", dynamic_ncols=True) as progress:
        return await _capture(url, directory, token, progress)


async def _capture(url: str, directory: Path, token: str | None, progress: tqdm) -> dict:
    generation = uuid4().hex
    frames = 0
    started = False
    crossed = False
    fps = 120
    config = {
        "action": "start", "preview": True, "size": 1024,
        "fps": fps, "dt": 0.1, "organisms": [{"scale": 1, "x": 0, "y": 0}],
    }

    async with connect(url, additional_headers=headers(token), max_size=4 * 1024 * 1024, compression=None) as websocket:
        await websocket.send(json.dumps(config))
        for _ in range(7200):
            message = await asyncio.wait_for(websocket.recv(), timeout=30)
            if isinstance(message, str):
                status = json.loads(message)
                if "error" in status:
                    raise ValueError(status["error"])
                if status.get("status") != "started" or started:
                    raise ValueError("Preview server did not start the crossing")

                started = True
                await websocket.send("next")
                continue
            if not started:
                raise ValueError("Preview frame received before stream started")

            progress.update(1)
            image = pygame.image.load(io.BytesIO(message), "frame.jpg")
            visible = any(pygame.image.tobytes(image, "RGB"))
            width, height = image.get_size()
            center = image.subsurface((width // 4, height // 4, width // 2, height // 2))
            crossed = crossed or any(pygame.image.tobytes(center, "RGB"))
            if frames or visible:
                (directory / f"{generation}-{frames:06d}.jpg").write_bytes(message)
                frames += 1
                if crossed and not visible:
                    return {
                        "fps": fps,
                        "frames": tuple(f"{generation}-{index:06d}.jpg" for index in range(frames)),
                    }

            await websocket.send("next")
    raise ValueError("Preview did not finish a crossing within 7200 frames")
