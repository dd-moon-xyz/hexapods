import argparse
import asyncio
import json
import math
import tempfile
import time
from pathlib import Path

import pygame
from tqdm import tqdm
from websockets.asyncio.client import connect
from websockets.exceptions import WebSocketException

from .client import display_frame, load_preset


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
    target = math.ceil(seconds * float(config.get("fps", 60)))
    with tqdm(total=target, desc="Capturing", unit="frame", ascii=True,
              colour="#808080", dynamic_ncols=True) as progress:
        return await _capture(url, config, directory, seconds, progress)


async def _capture(url: str, config: dict, directory: Path, seconds: float, progress: tqdm) -> dict:
    frames = []
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
                    target = math.ceil(seconds * fps)
                    progress.total = target
                    progress.refresh()
                    await websocket.send("next")
                    await websocket.send("next")
                continue
            name = f"{len(frames):06d}.jpg"
            (directory / name).write_bytes(message)
            frames.append(name)
            progress.update(1)
            if len(frames) >= target:
                break
            await websocket.send("next")
    manifest = {"fps": fps, "frames": frames}
    (directory / "manifest.json").write_text(json.dumps(manifest))
    return manifest


def replay(screen: pygame.Surface, directory: Path, manifest: dict) -> None:
    frames = manifest["frames"]
    fps = float(manifest.get("fps", 60))
    if not frames or not 0 < fps < float("inf"):
        raise ValueError("Recording has no frames or invalid FPS")
    # Keep compressed frames in memory; never read files during playback.
    images = [(directory / (frame["file"] if isinstance(frame, dict) else frame)).read_bytes() for frame in frames]
    deadline = time.monotonic()
    index = 0
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
        display_frame(screen, images[index])
        index = (index + 1) % len(images)
        deadline += 1 / fps
        now = time.monotonic()
        if deadline < now:
            deadline = now
        time.sleep(max(0, deadline - now))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="ws://192.168.0.15:9876/ws")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--directory", type=Path, default=Path("recordings/default"))
    parser.add_argument("--seconds", type=float, default=30)
    parser.add_argument("--windowed", action="store_true")
    parser.add_argument("--record-only", action="store_true", help="Capture without opening a display")
    args = parser.parse_args()
    try:
        if not 0 < args.seconds < float("inf"):
            raise ValueError("--seconds must be positive and finite")
        manifest_path = args.directory / "manifest.json"
        if not args.record_only:
            pygame.display.init()
            screen = pygame.display.set_mode((800, 800) if args.windowed else (0, 0), 0 if args.windowed else pygame.FULLSCREEN)
            pygame.display.set_caption("Hexapod replay")
            pygame.mouse.set_visible(False)
        if manifest_path.exists() and not args.record_only:
            manifest = json.loads(manifest_path.read_text())
        else:
            config = load_preset(args.url) if args.config is None else json.loads(args.config.read_text())
            config = {**config, "output_size": 800 if args.record_only else min(screen.get_size())}
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
        pygame.display.quit()


if __name__ == "__main__":
    main()
