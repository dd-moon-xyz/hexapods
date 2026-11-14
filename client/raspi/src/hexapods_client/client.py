import asyncio
import json
import sys
from functools import partial

import pygame
from websockets.exceptions import WebSocketException

from client_core.client import run
from client_core.preview import main as preview_main
from hexapods_client.sensors import monitor_sensors
from hexapods_client.settings import Settings


def main() -> None:
    try:
        if len(sys.argv) > 1:
            raise ValueError("Client options are configured in .env; see .env.example")

        settings = Settings()
        config = None if settings.config is None else json.loads(settings.config.read_text())
        monitor = partial(
            monitor_sensors, device=settings.motion_device,
            person_proximity=settings.person_proximity, motion_threshold=settings.motion_threshold,
            screen_x=settings.motion_screen_x, screen_y=settings.motion_screen_y,
        )

        async def sensors(commands, population):
            await monitor(commands, population=population)

        asyncio.run(run(
            settings.url, config, sensor_monitor=sensors,
            windowed=settings.windowed, fit_display=True, token=settings.hexapods_token,
        ))

    except (OSError, ValueError, WebSocketException, pygame.error) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    except KeyboardInterrupt:
        pass


def preview() -> None:
    settings = Settings()
    preview_main(settings.url, settings.hexapods_token)


if __name__ == "__main__":
    main()
