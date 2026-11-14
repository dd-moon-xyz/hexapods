# Hexapods

Interactive GPU hexapod simulations streamed over WebSocket. The Rust server uses Axum, Tokio, and libjpeg-turbo; the Python desktop and Raspberry Pi clients share a Pygame/SDL2 viewer. The simulation core remains C++20/CUDA.

- [server/](server/README.md): uncapped HTTP/WebSocket server and native CUDA core.
- [client/core/](client/core/README.md): shared rendering, streaming, configuration, and offline fallback.
- [client/local/](client/local/README.md): desktop entry point and keyboard controls.
- [client/raspi/](client/raspi/README.md): separate Raspberry Pi hardware viewer, sensors, and offline fallback.
- [wiki/](wiki/documentation/overview.md): setup, operation, wiring, and protocol documentation.

Install the [server prerequisites](server/README.md) and [Python client prerequisites](client/local/README.md), then run from the repository root:

```bash
make rust-setup
make server-setup
make local-client-setup
make server-run
```

`make rust-setup` installs or updates stable Rust, Cargo, rustfmt, and Clippy through rustup. It also runs `sudo apt update` and `sudo apt install -y cmake`. It requires an apt-based system, sudo access, `curl`, and internet access. CUDA is installed separately; see the [environment guide](wiki/setup/python.md). Server setup builds an optimized binary. Install uv for the Python clients; their setup commands create managed Python 3.14 environments and install locked dependencies. SDL3 is no longer required.

In a second terminal:

```bash
make local-client-run
```

Both use port **9877** by default. The browser viewer is at `http://127.0.0.1:9877/`. For a remote server, run `cd client/local && uv run --locked local-client --url ws://<server-LAN-IP>:9877/ws`. The server delivers fresh simulation frames on demand without an FPS cap; the `fps` start field is recording metadata.

Hold Space or C for boosted outward escape, or V for boosted inward movement. Release keys to restore inward movement; Esc exits.

Use `make server-test` and `make local-client-test` for tests. PM2 background mode uses `make server-up` and `make local-client-up`; stop them with the corresponding `-stop` commands. The client needs an active graphical desktop.

The Raspberry Pi sensor client uses the shared `client_core` Python package, with Picamera2 camera, I²C motion, and LED controls. Run `make raspi-client-setup`, configure `SERVER_ADDRESS=<server-LAN-IP>:9877` in `client/raspi/.env`, then use `make raspi-client-run`. See [Pi setup](wiki/setup/index.md), [configuration](wiki/operation/configuration.md), and [sensor wiring](wiki/wiring/index.md).
