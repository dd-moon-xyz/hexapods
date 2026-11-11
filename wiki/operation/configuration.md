---
type: Documentation
title: Client configuration
---

# Client configuration

Raspberry Pi live-client settings are loaded and validated in Rust by `raspi_client/src/settings.rs`. Edit `raspi_client/.env`; `.env.example` lists the settings. Environment variables override the file. Run `make raspi-client-restart` after changes under PM2. Both `make raspi-client-run` and `make raspi-client-up` use the same configuration. The Pi imports the desktop Rust viewer library and adds camera, motion, and LED controls.

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

The client preserves the preset FPS, population, simulation resolution, and timestep. It adds `output_size` matching the shorter display dimension, requesting 800×800 JPEGs on the Raspberry Pi while retaining the 1024×1024 simulation. It adds no client FPS cap.

The client keeps two frame requests in flight and replaces each request as its frame arrives. This allows the server to prepare the following frame during delivery and avoids waiting for a new round trip between simulation steps. The request count stays bounded; every received frame is displayed.

The desktop viewer accepts `--url ws://127.0.0.1:9877/ws`, `--config config.json`, and `--record capture.mp4` using `./local_client/target/release/local-client`. Without `--config`, it fetches `/preset`. Build with `make local-client-setup`; run with `make local-client-run`, `make local-client-record`, or `make local-client-up`. See [Rust client setup](../../local_client/README.md). The [Rust server](../../server/README.md) listens on port 9877 and has no delivery FPS cap. Its positive `fps` value is recording metadata. Set the Pi’s `LENIA_URL` to the Rust server address.

[Section index](index.md) · [Wiki index](../documentation/overview.md)
