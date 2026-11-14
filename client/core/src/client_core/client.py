import argparse
import asyncio
import io
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

import pygame
from websockets.asyncio.client import connect
from websockets.exceptions import WebSocketException

from client_core.rendering import Viewer
from client_core.auth import headers
from client_core.fallback import display_fallback

FRAME_TIMEOUT = 15


def load_preset(url: str, token: str | None = None) -> dict:
    address = urlsplit(url)
    scheme = {"ws": "http", "wss": "https"}[address.scheme]
    path = address.path.rsplit("/", 1)[0] + "/preset"
    with urlopen(Request(urlunsplit((scheme, address.netloc, path, "", "")), headers=headers(token)), timeout=30) as response:
        return json.load(response)


async def display_stream(
    url: str, config: dict, commands: asyncio.Queue, viewer: Viewer, population: dict | None = None, token: str | None = None,
    connected: asyncio.Event | None = None,
) -> None:
    async with (
        connect(url, additional_headers=headers(token), max_size=4 * 1024 * 1024, compression=None) as websocket,
        asyncio.timeout(FRAME_TIMEOUT) as activity,
    ):
        if population is not None:
            config = {**config, "population_updates": True}

        await websocket.send(json.dumps(config))
        async for message in websocket:
            if isinstance(message, str):
                status = json.loads(message)
                if "error" in status:
                    raise ValueError(status["error"])

                if status.get("status") == "started":
                    viewer.resize((status["size"], status["size"]))
                    await websocket.send("next")
                    await websocket.send("next")

                if status.get("status") == "population" and population is not None:
                    population["fraction"] = status["alive"] / max(1, status["total"])

                if status.get("status") == "stopped":
                    return

                continue

            while not commands.empty():
                command = commands.get_nowait()
                await websocket.send(json.dumps(command) if isinstance(command, dict) else command)

            await websocket.send("next")
            frame = pygame.image.load(io.BytesIO(message), "frame.jpg")
            viewer.draw(frame)
            activity.reschedule(asyncio.get_running_loop().time() + FRAME_TIMEOUT)
            if connected is not None:
                connected.set()


async def reconnect(
    url: str, config: dict | None, commands: asyncio.Queue, viewer: Viewer,
    connected: asyncio.Event, population: dict | None = None,
    token: str | None = None, fit_display: bool = False,
) -> None:
    while True:
        try:
            preset = await asyncio.to_thread(load_preset, url, token) if config is None else config
            if fit_display:
                preset = {**preset, "output_size": min(1024, *viewer.output_size)}

            await display_stream(url, preset, commands, viewer, population, token, connected)
            print("Server stream ended; playing offline animation. Retrying in 3 seconds.", file=sys.stderr, flush=True)
        except (OSError, ValueError, KeyError, TypeError, WebSocketException, pygame.error) as error:
            print(f"Server unavailable: {error}. Playing offline animation; retrying in 3 seconds.", file=sys.stderr, flush=True)
        finally:
            connected.clear()

        await asyncio.sleep(3)


async def run(
    url: str, config: dict | None,
    sensor_monitor=None, windowed: bool = True, fit_display: bool = False, token: str | None = None,
) -> None:
    pygame.display.init()
    viewer = Viewer(fullscreen=not windowed, fit_display=fit_display) if fit_display else Viewer()
    if fit_display:
        pygame.mouse.set_visible(False)

    commands = asyncio.Queue()
    held = {}
    steering_keys = {} if sensor_monitor is not None else {
        pygame.K_SPACE: "outward",
        pygame.K_c: "outward",
        pygame.K_v: "inward_fast",
    }
    population = {"fraction": 1.0}
    sensors = None
    if sensor_monitor is not None:
        sensors = asyncio.create_task(sensor_monitor(commands, population))

    connected = asyncio.Event()
    stream = asyncio.create_task(reconnect(
        url, config, commands, viewer, connected,
        population if sensors is not None else None, token, fit_display,
    ))

    fallback = asyncio.create_task(display_fallback(viewer, connected))
    try:
        while not stream.done():
            if fallback.done():
                await fallback

            if sensors is not None and sensors.done():
                await sensors

            events = pygame.event.get()
            if any(
                event.type == pygame.QUIT
                or (
                    event.type == pygame.KEYDOWN
                    and event.key == pygame.K_ESCAPE
                )
                for event in events
            ):
                return

            for event in events:
                if (
                    event.type in {pygame.KEYDOWN, pygame.KEYUP}
                    and event.key in steering_keys
                ):
                    if (
                        event.type == pygame.KEYDOWN
                        and event.key not in held
                    ):
                        held[event.key] = steering_keys[event.key]
                        commands.put_nowait(held[event.key])

                    if event.type == pygame.KEYUP and event.key in held:
                        del held[event.key]
                        commands.put_nowait(
                            next(reversed(held.values()), "inward")
                        )

                if sensor_monitor is None and event.type == pygame.WINDOWFOCUSLOST:
                    held.clear()
                    commands.put_nowait("inward")

            await asyncio.sleep(0.01)

        await stream
    finally:
        tasks = (stream, fallback) if sensors is None else (stream, fallback, sensors)
        for task in tasks:
            task.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)

        viewer.close()
        pygame.display.quit()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Display a Hexapod WebSocket animation in pygame"
    )
    parser.add_argument(
        "--url", default=os.getenv("SERVER_URL") or "ws://" + os.getenv("SERVER_ADDRESS", "127.0.0.1:9877") + "/ws", help="Server WebSocket URL"
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="JSON file containing the server start configuration",
    )
    args = parser.parse_args()
    try:
        config = None if args.config is None else json.loads(args.config.read_text())

        asyncio.run(run(args.url, config))
    except (OSError, ValueError, WebSocketException, pygame.error) as error:
        parser.exit(1, f"Error: {error}\n")
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
