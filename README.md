# Hexapods

Interactive GPU hexapod simulations streamed over WebSocket. The Rust server uses Axum, Tokio, and libjpeg-turbo; the Rust desktop client uses SDL3. The simulation core remains C++20/CUDA.

- [server/](server/README.md): uncapped HTTP/WebSocket server and native CUDA core.
- [client_core/](client_core/README.md): shared rendering, streaming, configuration, recording, and replay.
- [local_client/](local_client/README.md): desktop entry point and keyboard controls.
- [raspi_client/](raspi_client/README.md): separate Raspberry Pi hardware viewer, sensors, recording, and replay.
- [wiki/](wiki/documentation/overview.md): setup, operation, wiring, and protocol documentation.

Install the [server prerequisites](server/README.md) and [SDL3 client prerequisites](local_client/README.md), then run from the repository root:

```bash
make rust-setup
make server-setup
make local-client-setup
make server-run
```

`make rust-setup` installs or updates stable Rust, Cargo, rustfmt, and Clippy through rustup. It requires `curl` and internet access. System libraries such as SDL3 and CUDA are installed separately; see the [Rust environment guide](wiki/setup/python.md). The existing `*-setup` commands build optimized binaries using locked dependencies.

In a second terminal:

```bash
make local-client-run
```

Both use port **9877** by default. The browser viewer is at `http://127.0.0.1:9877/`. For a remote server, run `./local_client/target/release/local-client --url ws://<server-LAN-IP>:9877/ws`. The server delivers fresh simulation frames on demand without an FPS cap; the `fps` start field is recording metadata.

Hold Space or C for boosted outward escape, or V for boosted inward movement. Release keys to restore inward movement; Esc exits. `make local-client-record` records an MP4 using FFmpeg.

Use `make server-test` and `make local-client-test` for tests. PM2 background mode uses `make server-up` and `make local-client-up`; stop them with the corresponding `-stop` commands. The client needs an active graphical desktop.

The Raspberry Pi sensor client uses the shared `client_core` Rust library, with native camera, motion, and LED controls. Run `make raspi-client-setup`, configure `LENIA_URL=ws://<server-LAN-IP>:9877/ws` in `raspi_client/.env`, then use `make raspi-client-run`. See [Pi setup](wiki/setup/index.md), [configuration](wiki/operation/configuration.md), and [sensor wiring](wiki/wiring/index.md).
