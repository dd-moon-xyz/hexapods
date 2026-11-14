import argparse
import asyncio
import io
import json
import shutil
import tempfile
from pathlib import Path
from uuid import uuid4

import pygame
from websockets.asyncio.client import connect
from websockets.exceptions import WebSocketException

from client_core.rendering import Viewer
from client_core.replay import replay


async def capture(url: str, directory: Path) -> dict:
    generation = uuid4().hex
    frames = 0
    started = False
    crossed = False
    fps = 60
    config = {
        "action": "start", "preview": True, "size": 1024, "output_size": 800,
        "fps": fps, "dt": 0.1, "organisms": [{"scale": 1, "x": 0, "y": 0}],
    }

    async with connect(url, max_size=4 * 1024 * 1024, compression=None) as websocket:
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


async def record(url: str, directory: Path) -> dict:
    if shutil.which("ffmpeg") is None:
        raise ValueError("Install FFmpeg before recording the preview")

    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=directory.parent, prefix=".preview-") as temporary:
        staging = Path(temporary)
        manifest = await capture(url, staging)
        pattern = manifest["frames"][0].rsplit("-", 1)[0] + "-%06d.jpg"
        process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-framerate", str(manifest["fps"]), "-i", str(staging / pattern),
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(staging / "animation.mp4"),
        )

        try:
            code = await process.wait()
        finally:
            if process.returncode is None:
                process.kill()
                await process.wait()

        if code != 0:
            raise ValueError(f"Video recording failed (FFmpeg exit {code})")

        for name in (*manifest["frames"], "animation.mp4"):
            (staging / name).replace(directory / name)
        (staging / "manifest.json").write_text(json.dumps(manifest))
        (staging / "manifest.json").replace(directory / "manifest.json")
    print(f"Saved one crossing to {directory / 'animation.mp4'}", flush=True)
    return manifest


def main(default_url: str) -> None:
    parser = argparse.ArgumentParser(description="Record and loop one large diagonal hexapod crossing")
    parser.add_argument("--url", default=default_url)
    parser.add_argument("--directory", type=Path, default=Path("recordings/single-hexapod"))
    parser.add_argument("--record-only", action="store_true", help="Create a fresh recording without a display")
    parser.add_argument("--windowed", action="store_true")
    args = parser.parse_args()
    screen = None
    try:
        manifest_path = args.directory / "manifest.json"
        if manifest_path.exists() and not args.record_only:
            manifest = json.loads(manifest_path.read_text())
        else:
            print(f"Recording one diagonal crossing from {args.url}…", flush=True)
            manifest = asyncio.run(record(args.url, args.directory))
        if not args.record_only:
            pygame.display.init()
            screen = Viewer(fullscreen=not args.windowed, fit_display=True)
            pygame.mouse.set_visible(False)
            print("Looping the crossing locally. Press Escape to exit.", flush=True)
            replay(screen, args.directory, manifest)
    except (OSError, ValueError, KeyError, WebSocketException, pygame.error) as error:
        parser.exit(1, f"Error: {error}\n")
    except KeyboardInterrupt:
        pass
    finally:
        if screen is not None:
            screen.close()

        pygame.display.quit()
