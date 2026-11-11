---
type: Documentation
title: Run with PM2
---

# Run with PM2

```bash
make raspi-client-up
make raspi-client-logs
make raspi-client-restart
make raspi-client-stop
```

The [ecosystem configuration](../../raspi_client/ecosystem.config.js) launches `target/release/raspi-client` for live mode and the same binary with `replay` for playback, with `raspi_client/` as the working directory. Run `make raspi-client-setup` first. SDL3 selects Wayland through `SDL_VIDEO_DRIVER`; `WAYLAND_DISPLAY` defaults to `wayland-0`, and `XDG_RUNTIME_DIR` derives from the current UID. Existing display/socket variables take precedence.

PM2 restarts the client after an exit, with a three-second delay. This allows recovery from server restarts or waiting for the desktop to become available. `make raspi-client-up`, `make raspi-client-stop`, and `make raspi-client-restart` save the PM2 process list. They target only `lenia-client`, leaving other PM2 applications alone. Use `make raspi-client-stop` to keep it stopped; closing the window causes PM2 to restart it.

For the desktop viewer, run `make local-client-setup` and `make local-client-up`; stop it with `make local-client-stop`. Its [PM2 configuration](../../local_client/ecosystem.config.js) runs the release binary in the graphical session. For the server, run `make server-setup` and `make server-up`; stop it with `make server-stop`. Its [PM2 configuration](../../server/ecosystem.config.js) runs the headless Rust server on port 9877 with CUDA GPU access.

For terminal mode, use `make server-run`, `make local-client-run`, or `make raspi-client-run`.

When migrating from the Python client, stop/delete the existing `lenia-client` and `lenia-replay` PM2 entries, rebuild with `make raspi-client-setup`, then recreate them with `make raspi-client-up` and `make replay-start`. Save the updated PM2 list.

[Section index](index.md) · [Wiki index](../documentation/overview.md)
