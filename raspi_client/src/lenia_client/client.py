import asyncio
import io
import json
import sys
from urllib.parse import urlsplit, urlunsplit
from urllib.request import urlopen

import pygame
from websockets.asyncio.client import connect
from websockets.exceptions import WebSocketException

from lenia_client.sensors import monitor_sensors
from lenia_client.settings import Settings


def load_preset(url: str) -> dict:
    address = urlsplit(url)
    scheme = {"ws": "http", "wss": "https"}[address.scheme]
    path = address.path.rsplit("/", 1)[0] + "/preset"
    with urlopen(urlunsplit((scheme, address.netloc, path, "", "")), timeout=30) as response:
        return json.load(response)


def display_frame(screen: pygame.Surface, message: bytes) -> None:
    frame = pygame.image.load(io.BytesIO(message), "frame.jpg")
    scale = min(screen.get_width() / frame.get_width(), screen.get_height() / frame.get_height())
    size = tuple(max(1, round(dimension * scale)) for dimension in frame.get_size())
    if frame.get_size() != size:
        frame = pygame.transform.scale(frame, size)

    screen.fill("black")
    screen.blit(frame, frame.get_rect(center=screen.get_rect().center))
    pygame.display.flip()


async def display_stream(url: str, config: dict, screen: pygame.Surface, commands: asyncio.Queue, population=None) -> None:
    if population is not None:
        config = {**config, "population_updates": True}

    async with connect(url, max_size=4 * 1024 * 1024, max_queue=1, compression=None) as websocket:
        await websocket.send(json.dumps(config))
        async for message in websocket:
            if isinstance(message, str):
                status = json.loads(message)
                if "error" in status:
                    raise ValueError(status["error"])

                if status.get("status") == "started":
                    print(f"Streaming {status['size']}×{status['size']} at server preset {status['fps']} FPS", flush=True)
                    # Keep two requests in flight so the server can prepare the
                    # next frame while the current one is being delivered.
                    await websocket.send("next")
                    await websocket.send("next")

                if status.get("status") == "population" and population is not None:
                    population['fraction'] = status['alive'] / status['total']

                if status.get("status") == "stopped":
                    return

                continue

            if not commands.empty():
                command = commands.get_nowait()
                while not commands.empty():
                    command = commands.get_nowait()
                await websocket.send(json.dumps(command) if isinstance(command, dict) else command)

            await websocket.send("next")
            display_frame(screen, message)


async def run(settings: Settings, config: dict) -> None:
    pygame.display.init()
    try:
        screen = pygame.display.set_mode((800, 800) if settings.windowed else (0, 0), 0 if settings.windowed else pygame.FULLSCREEN)
        config = {**config, "output_size": min(screen.get_size())}
        pygame.display.set_caption("Hexapod client")
        pygame.mouse.set_visible(False)
        print(f"Display: {pygame.display.get_driver()} {screen.get_width()}×{screen.get_height()}", flush=True)
        commands = asyncio.Queue()
        population = {'fraction': 1.0}
        stream = asyncio.create_task(display_stream(settings.url, config, screen, commands, population))
        proximity = asyncio.create_task(monitor_sensors(commands, settings.motion_device,
                                                      settings.person_proximity, settings.motion_threshold,
                                                      settings.motion_screen_x, settings.motion_screen_y,
                                                      population))

        try:
            while not stream.done():
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        return

                if proximity.done():
                    await proximity

                await asyncio.sleep(0.01)

            await stream
        finally:
            tasks = (stream, proximity)
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    finally:
        pygame.display.quit()


def main() -> None:
    try:
        if len(sys.argv) > 1:
            raise ValueError('Client options are configured in .env; see .env.example')
        settings = Settings()
        config = load_preset(settings.url) if settings.config is None else json.loads(settings.config.read_text())
        asyncio.run(run(settings, config))
    except (OSError, ValueError, WebSocketException, pygame.error) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
