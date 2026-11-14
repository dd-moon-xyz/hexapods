---
type: Documentation
title: Client configuration
---

# Client configuration

Raspberry Pi live-client settings are loaded and validated in Python by `client/raspi/src/lenia_client/settings.py`. Set `SERVER_ADDRESS` in `client/raspi/.env`; `.env.example` also shows optional internet connection and authentication variables. All other settings have defaults in the Pydantic settings object and can be omitted from `.env`. Environment variables override the file. Run `make raspi-client-restart` after changes under PM2. Both `make raspi-client-run` and `make raspi-client-up` use the same configuration. Both Python clients import `client_core`; the Pi adds camera, motion, and LED controls.

| Variable | Default | Purpose |
| --- | --- | --- |
| `SERVER_ADDRESS` | `192.168.0.15:9877` | Server host and port (`host:port`); clients build `ws://host:port/ws`. |
| `SERVER_URL` | Unset | Full Pi WebSocket URL, such as `wss://hexapods.example.com/ws`; overrides `SERVER_ADDRESS`. |
| `HEXAPODS_TOKEN` | Empty | Per-client API token for authenticated HTTP and WebSocket requests. |
| `CONFIG` | Unset | Optional JSON simulation start file; otherwise fetch the server preset. |
| `WINDOWED` | `false` | Set `true` for an 800×800 window. |
| `MOTION_DEVICE` | `/dev/i2c-1` | Motion sensor I²C device. |
| `MOTION_THRESHOLD` | `0.12` | Positive X/Y acceleration-change threshold in g. |
| `MOTION_SCREEN_X` | `y` | Sensor axis mapped to screen X: `x`, `-x`, `y`, or `-y`. |
| `MOTION_SCREEN_Y` | `x` | Sensor axis mapped to screen Y; must differ from screen X's sensor axis. |
| `PERSON_PROXIMITY` | `0.5` | Person box height fraction; greater than 0 and less than 1. |

For example, set `PERSON_PROXIMITY=0.35` to react farther away. These settings configure the client locally; the optional JSON file configures the server simulation.

Without an explicit configuration file, both clients fetch the server preset and use its default 50 hexapod slots. An explicit `organisms` list still controls the population when supplied. Start configuration fields `scale_min` and `scale_max` set the inclusive random scale range for every birth, defaulting to 1.0 and 1.1. For example, `"scale_min": 2, "scale_max": 2` fixes all birth scales at 2; allowed bounds are finite ordered numbers from 1 through 10. Both clients pass these fields through to the server. The client preserves the preset FPS, population, simulation resolution, and timestep. It adds `output_size` matching the shorter display dimension, requesting 800×800 JPEGs on the Raspberry Pi while retaining the 1024×1024 simulation. It adds no client FPS cap.

The client keeps two frame requests in flight and replaces each request as its frame arrives. This allows the server to prepare the following frame during delivery and avoids waiting for a new round trip between simulation steps. The request count stays bounded; every received frame is displayed.

Edit `server/.env` directly using [the server example](../../server/.env.example): set `HEXAPODS_TOKEN_HASHES=local:sha256hex,raspi:sha256hex`, `SERVER_BIND`, and optionally `HEXAPODS_BROWSER_ORIGIN`. Set `SERVER_URL` and the original `HEXAPODS_TOKEN` in each client’s `.env`; see the [local example](../../client/local/.env.example) and [Raspberry Pi example](../../client/raspi/.env.example). Add, replace, or remove server hash entries to manage tokens. Python clients send `HEXAPODS_TOKEN` as a Bearer credential for preset retrieval and WebSocket upgrade. Use HTTPS/WSS through a TLS reverse proxy for internet access; see [server authentication and deployment](../../server/README.md). Only trusted local development should use the server’s explicit `--allow-unauthenticated` option. Browser login requires `HEXAPODS_BROWSER_ORIGIN` matching the HTTPS viewer origin. Each token permits one active simulation; token changes require a server restart (`make server-restart` for PM2, or stop and rerun `make server-run` for foreground mode).

The desktop viewer, collection, and replay recording commands read the server host and port (`host:port`) from the `SERVER_ADDRESS` environment variable; an explicit `--url` takes precedence. For example, run `SERVER_ADDRESS=SERVER:9877 make local-client-run`. The desktop default remains `ws://127.0.0.1:9877/ws`; collection and replay recording default to `ws://192.168.0.15:9877/ws`. All Makefile run, recording, collection, replay, and PM2 targets load their role’s `.env`; process environment variables take precedence. `SERVER_URL` sets a full WebSocket URL and takes precedence over `SERVER_ADDRESS`. The desktop viewer accepts `--url ws://127.0.0.1:9877/ws`, `--config config.json`, and `--record capture.mp4` using `cd client/local && uv run --locked local-client`. Without `--config`, it fetches `/preset`. Build with `make local-client-setup`; run with `make local-client-run`, `make local-client-record`, or `make local-client-up`. See [Python client setup](../../client/local/README.md). The [Rust server](../../server/README.md) listens on port 9877 and has no delivery FPS cap. Its positive `fps` value is recording metadata. Set the Pi’s `SERVER_ADDRESS` to the Rust server address.

[Section index](index.md) · [Wiki index](../documentation/overview.md)
