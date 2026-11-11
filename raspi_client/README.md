# Hexapods Raspberry Pi Client

Fullscreen Raspberry Pi viewer for the hexapod WebSocket server. The GPU server runs the simulation; the Pi displays JPEG frames and sends camera-based person proximity and motion controls.

From the repository root:

```bash
make raspi-client-setup
make raspi-client-run
```

See the [wiki](../wiki/documentation/overview.md) for installation, configuration, sensor wiring, recording, replay, and troubleshooting.

Configure the live client in `.env`; [.env.example](.env.example) lists all settings. Environment variables override the file. Set `LENIA_PERSON_PROXIMITY` lower to react to people farther away (default `0.5`).

Use `make raspi-client-up` for background mode through PM2 and `make raspi-client-stop` to stop it. Both modes use `raspi_client/.env`. PM2 process names and Python entry points remain `lenia-client` and `lenia-replay`. The desktop testing viewer lives separately in [local_client/](../local_client/README.md).
