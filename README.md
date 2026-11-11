# Hexapods

Interactive GPU hexapod simulations streamed to a desktop or Raspberry Pi viewer. The server runs the simulation in CUDA and sends JPEG frames over WebSocket; the local client provides windowed keyboard testing, while the Raspberry Pi client uses camera proximity and motion sensors.

- [server/](server/README.md): C++20/CUDA hexapod simulation, Python WebSocket API, and Docker services.
- [local_client/](local_client/README.md): desktop testing, keyboard controls, and optional MP4 recording.
- [raspi_client/](raspi_client/README.md): Raspberry Pi viewer, sensor controls, frame recording, and replay.
- [wiki/](wiki/documentation/overview.md): shared setup, operation, wiring, simulation, and protocol documentation.

Run all `make` commands from the repository root. The server and both clients keep separate Python dependencies and environments.

On the server host, install Docker Compose and NVIDIA Container Toolkit with a compatible NVIDIA driver and GPU, then build and start the server:

```bash
make server-build
make server-up
```

The API and browser viewer are available at `http://<server-LAN-IP>:9876/`. The client device must be able to reach port 9876. Use `make server-stop` to stop the container; after server changes, run `make server-build` and `make server-up` again. See [server setup](wiki/setup/linux.md) for build requirements and Docker details.

For local desktop testing, install uv and start the independent local viewer:

```bash
make local-client-setup
make local-client-run
```

It connects to `ws://127.0.0.1:9876/ws` and fetches the server preset. Use `make local-client-record` to record an MP4 with FFmpeg, or see [local configuration](local_client/README.md) to connect to another server.

On the Raspberry Pi, install uv and complete the [display and hardware setup](wiki/setup/index.md), then configure and launch the client:

```bash
make raspi-client-setup
cp raspi_client/.env.example raspi_client/.env
# Set LENIA_URL=ws://<server-LAN-IP>:9876/ws in raspi_client/.env.
make raspi-client-run
```

The live client reads `raspi_client/.env`; environment variables override the file. Set `LENIA_WINDOWED=true` for an 800×800 window. See [configuration](wiki/operation/configuration.md), [sensor wiring](wiki/wiring/index.md), and [troubleshooting](wiki/operation/troubleshooting.md) for the remaining settings and hardware requirements.

Choose terminal or background mode from the repository root:

| Component | Terminal | Background | Stop background process |
| --- | --- | --- | --- |
| Server | `make server-run` | `make server-up` | `make server-stop` |
| Local client | `make local-client-run` | `make local-client-up` | `make local-client-stop` |
| Raspberry Pi client | `make raspi-client-run` | `make raspi-client-up` | `make raspi-client-stop` |

Client background mode uses PM2 and still needs an active desktop session. Terminal mode logs to the terminal and exits with Ctrl+C. The existing `make desktop-client`, `make client`, and related commands remain aliases.

For unattended operation, install [Node.js and PM2](wiki/setup/node-and-pm2.md), then use `make raspi-client-up`, `make raspi-client-stop`, `make raspi-client-restart`, and `make raspi-client-logs`. See [boot startup](wiki/operation/boot-startup.md) to restore the viewer after reboot.

Use `make collect` to capture a fresh recording and `make replay` to loop saved frames. Collection replaces the frames in the selected recording directory. Replay captures 30 seconds on its first run if no recording exists. Stop the live viewer before using replay; see [recording and replay](wiki/recording/index.md) for options and PM2 commands.

The server retains its original `lenia` Python package and executable names; it runs only the CUDA hexapod simulation. See [credits](wiki/documentation/credits.md) for project provenance.
