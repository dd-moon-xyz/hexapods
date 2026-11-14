import argparse
import asyncio
import io
import json
import os
import math
import tempfile
import time
from pathlib import Path
from uuid import uuid4

import pygame
from tqdm import tqdm
from websockets.asyncio.client import connect
from websockets.exceptions import WebSocketException

from .client import load_preset
from .rendering import Viewer


async def record(url: str, config: dict, directory: Path, seconds: float) -> dict:
    # Publish only complete captures, preserving the old one on interruption.
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=directory.parent, prefix=".capture-") as temporary:
        staging = Path(temporary)
        manifest = await _record(url, config, staging, seconds)
        for name in manifest["frames"]:
            (staging / name).replace(directory / name)
        (staging / "manifest.json").replace(directory / "manifest.json")
    print(f"Saved {len(manifest['frames'])} frames ({seconds:g} seconds) to {directory}", flush=True)
    return manifest


async def _record(url: str, config: dict, directory: Path, seconds: float) -> dict:
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("Capture duration must be positive and finite")

    target = math.ceil(seconds * float(config.get("fps", 60)))
    with tqdm(total=target, desc="Capturing", unit="frame", ascii=True,
              colour="#808080", dynamic_ncols=True) as progress:
        return await _capture(url, config, directory, seconds, progress)


async def _capture(url: str, config: dict, directory: Path, seconds: float, progress: tqdm) -> dict:
    generation = uuid4().hex
    frames = ()
    received = 0
    fps = float(config.get("fps", 60))
    target = math.ceil(seconds * fps)
    async with connect(url, max_size=4 * 1024 * 1024, max_queue=1, compression=None) as websocket:
        await websocket.send(json.dumps(config))
        while True:
            message = await asyncio.wait_for(websocket.recv(), timeout=30)
            if isinstance(message, str):
                status = json.loads(message)
                if "error" in status:
                    raise ValueError(status["error"])
                if status.get("status") == "stopped":
                    raise ValueError("Server stopped before recording completed")
                if status.get("status") == "started":
                    fps = float(status["fps"])
                    if not math.isfinite(fps) or fps <= 0:
                        raise ValueError("Invalid recording FPS")

                    target = math.ceil(seconds * fps)
                    frames = tuple(f"{generation}-{index:06d}.jpg" for index in range(target))
                    progress.total = target
                    progress.refresh()
                    await websocket.send("next")
                    await websocket.send("next")
                continue
            if not frames:
                raise ValueError("Frame received before stream started")

            (directory / frames[received]).write_bytes(message)
            received += 1
            progress.update(1)
            if received >= target:
                break
            await websocket.send("next")
    manifest = {"fps": fps, "frames": frames}
    (directory / "manifest.json").write_text(json.dumps(manifest))
    return manifest


def replay(screen: Viewer, directory: Path, manifest: dict) -> None:
    frames = manifest["frames"]
    fps = float(manifest.get("fps", 60))
    names = tuple(frame["file"] if isinstance(frame, dict) else frame for frame in frames)
    if any(not isinstance(name, str) or Path(name).name != name or not name.endswith(".jpg") for name in names):
        raise ValueError("Invalid recording frame path")

    if not frames or not 0 < fps < float("inf"):
        raise ValueError("Recording has no frames or invalid FPS")
    # Keep compressed frames in memory; never read files during playback.
    images = tuple((directory / name).read_bytes() for name in names)
    deadline = time.monotonic()
    index = 0
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                return
        screen.draw(pygame.image.load(io.BytesIO(images[index]), "frame.jpg"))
        index = (index + 1) % len(images)
        deadline += 1 / fps
        now = time.monotonic()
        if deadline < now:
            deadline = now
        time.sleep(max(0, deadline - now))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="ws://" + os.getenv("SERVER_ADDRESS", "192.168.0.15:9877") + "/ws")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--directory", type=Path, default=Path("recordings/default"))
    parser.add_argument("--seconds", type=float, default=30)
    parser.add_argument("--windowed", action="store_true")
    parser.add_argument("--record-only", action="store_true", help="Capture without opening a display")
    args = parser.parse_args()
    screen = None
    try:
        if not 0 < args.seconds < float("inf"):
            raise ValueError("--seconds must be positive and finite")
        manifest_path = args.directory / "manifest.json"
        if not args.record_only:
            pygame.display.init()
            screen = Viewer(fullscreen=not args.windowed, fit_display=True)
            pygame.mouse.set_visible(False)
        if manifest_path.exists() and not args.record_only:
            manifest = json.loads(manifest_path.read_text())
        else:
            config = load_preset(args.url) if args.config is None else json.loads(args.config.read_text())
            config = {**config, "output_size": 800 if args.record_only else min(1024, *screen.output_size)}
            print(f"Recording {args.seconds:g} seconds from {args.url}…", flush=True)
            manifest = asyncio.run(record(args.url, config, args.directory, args.seconds))
        if not args.record_only:
            print("Replaying local frames in a loop. Press Escape to exit.", flush=True)
            replay(screen, args.directory, manifest)
    except (OSError, ValueError, KeyError, WebSocketException, pygame.error) as error:
        parser.exit(1, f"Error: {error}\n")
    except KeyboardInterrupt:
        pass
    finally:
        if screen is not None:
            screen.close()

        pygame.display.quit()


if __name__ == "__main__":
    main()
