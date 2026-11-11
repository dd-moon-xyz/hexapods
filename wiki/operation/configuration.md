---
type: Documentation
title: Client configuration
---

# Client configuration

Raspberry Pi live-client settings are validated by `pydantic-settings` in `raspi_client/src/lenia_client/settings.py`. Edit `raspi_client/.env`; `raspi_client/.env.example` lists every supported setting. On a fresh checkout, copy `.env.example` to `.env`. Environment variables override the file, including in Docker. Run `make raspi-client-restart` after changing settings for PM2. The Raspberry Pi client accepts configuration through the environment file. Both `make raspi-client-run` (terminal) and `make raspi-client-up` (PM2 background mode) use that same configuration.

| Variable | Default | Purpose |
| --- | --- | --- |
| `LENIA_URL` | `ws://192.168.0.15:9876/ws` | WebSocket server. |
| `LENIA_CONFIG` | Unset | Optional JSON simulation start file; otherwise fetch the server preset. |
| `LENIA_WINDOWED` | `false` | Set `true` for an 800×800 window. |
| `LENIA_MOTION_DEVICE` | `/dev/i2c-1` | Motion sensor I²C device. |
| `LENIA_MOTION_THRESHOLD` | `0.12` | Positive X/Y acceleration-change threshold in g. |
| `LENIA_MOTION_SCREEN_X` | `y` | Sensor axis mapped to screen X: `x`, `-x`, `y`, or `-y`. |
| `LENIA_MOTION_SCREEN_Y` | `x` | Sensor axis mapped to screen Y; must differ from screen X's sensor axis. |
| `LENIA_PERSON_PROXIMITY` | `0.5` | Person box height fraction; greater than 0 and less than 1. |

For example, set `LENIA_PERSON_PROXIMITY=0.35` to react farther away. These settings configure the client locally; the optional JSON file configures the server simulation.

The client preserves the preset FPS, population, simulation resolution, and timestep. It adds `output_size` matching the shorter display dimension, requesting 800×800 JPEGs on the Raspberry Pi while retaining the 1024×1024 simulation. It adds no client FPS cap.

The client keeps two frame requests in flight and replaces each request as its frame arrives. This allows the server to prepare the following frame during delivery and avoids waiting for a new round trip between simulation steps. The request count stays bounded; every received frame is displayed.

The independent local viewer is configured with CLI options from `local_client/`: `uv run local-client --url ws://127.0.0.1:9876/ws`, `--config config.json`, and `--record capture.mp4`. Without `--config`, it fetches `/preset` from the selected server. It uses keyboard controls and a windowed display. `make local-client-run` runs in the terminal; `make local-client-up` starts the default local viewer through PM2. It uses no Pi environment or hardware settings.

[Section index](index.md) · [Wiki index](../documentation/overview.md)
