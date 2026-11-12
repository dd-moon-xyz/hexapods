---
type: Documentation
title: Client configuration
---

# Client configuration

Raspberry Pi live-client settings are loaded and validated in Python by `client/raspi/src/lenia_client/settings.py`. Edit `client/raspi/.env`; `.env.example` lists the settings. Environment variables override the file. Run `make raspi-client-restart` after changes under PM2. Both `make raspi-client-run` and `make raspi-client-up` use the same configuration. Both Python clients import `client_core`; the Pi adds camera, motion, and LED controls.

| Variable | Default | Purpose |
| --- | --- | --- |
| `LENIA_URL` | `ws://192.168.0.15:9877/ws` | WebSocket server. |
| `LENIA_CONFIG` | Unset | Optional JSON simulation start file; otherwise fetch the server preset. |
| `LENIA_WINDOWED` | `false` | Set `true` for an 800×800 window. |
| `LENIA_MOTION_DEVICE` | `/dev/i2c-1` | Motion sensor I²C device. |
| `LENIA_MOTION_THRESHOLD` | `0.12` | Positive X/Y acceleration-change threshold in g. |
| `LENIA_MOTION_SCREEN_X` | `y` | Sensor axis mapped to screen X: `x`, `-x`, `y`, or `-y`. |
| `LENIA_MOTION_SCREEN_Y` | `x` | Sensor axis mapped to screen Y; must differ from screen X's sensor axis. |
| `LENIA_PERSON_PROXIMITY` | `0.5` | Person box height fraction; greater than 0 and less than 1. |

For example, set `LENIA_PERSON_PROXIMITY=0.35` to react farther away. These settings configure the client locally; the optional JSON file configures the server simulation.

Without an explicit configuration file, both clients fetch the server preset and use its default 50 hexapod slots. An explicit `organisms` list still controls the population when supplied. Start configuration fields `scale_min` and `scale_max` set the inclusive random scale range for every birth, defaulting to 1.0 and 1.1. For example, `"scale_min": 2, "scale_max": 2` fixes all birth scales at 2; allowed bounds are finite ordered numbers from 1 through 10. Both clients pass these fields through to the server. The client preserves the preset FPS, population, simulation resolution, and timestep. It adds `output_size` matching the shorter display dimension, requesting 800×800 JPEGs on the Raspberry Pi while retaining the 1024×1024 simulation. It adds no client FPS cap.

The client keeps two frame requests in flight and replaces each request as its frame arrives. This allows the server to prepare the following frame during delivery and avoids waiting for a new round trip between simulation steps. The request count stays bounded; every received frame is displayed.

The desktop viewer accepts `--url ws://127.0.0.1:9877/ws`, `--config config.json`, and `--record capture.mp4` using `cd client/local && uv run --locked local-client`. Without `--config`, it fetches `/preset`. Build with `make local-client-setup`; run with `make local-client-run`, `make local-client-record`, or `make local-client-up`. See [Python client setup](../../client/local/README.md). The [Rust server](../../server/README.md) listens on port 9877 and has no delivery FPS cap. Its positive `fps` value is recording metadata. Set the Pi’s `LENIA_URL` to the Rust server address.

[Section index](index.md) · [Wiki index](../documentation/overview.md)
