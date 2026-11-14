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

The [ecosystem configuration](../../client/raspi/ecosystem.config.js) launches `uv run --locked hexapods-client` for live mode, with `client/raspi/` as the working directory. Run `make raspi-client-setup` first. SDL2 selects Wayland through `SDL_VIDEODRIVER`; `WAYLAND_DISPLAY` defaults to `wayland-0`, and `XDG_RUNTIME_DIR` derives from the current UID.

PM2 restarts the client after an exit, with a three-second delay. This allows recovery from server restarts or waiting for the desktop to become available. `make raspi-client-up`, `make raspi-client-stop`, and `make raspi-client-restart` save the PM2 process list. They target only `hexapods-client`, leaving other PM2 applications alone. The restart target stops the client first to cancel a pending automatic retry and clear its PID, then restarts it with the current configuration. This avoids PM2's `Process with pid … already exists` failure when the client is waiting to restart. Use `make raspi-client-stop` to keep it stopped; closing the window causes PM2 to restart it.

For the desktop viewer, run `make local-client-setup` and `make local-client-up`; stop it with `make local-client-stop`. `make local-client-restart` stops `local-client` first to clear pending retries, then restarts it with the current configuration and saves the PM2 process list. Its [PM2 configuration](../../client/local/ecosystem.config.js) runs `.venv/bin/local-client` in the graphical session. For the server, run `make server-setup` and `make server-up`; stop it with `make server-stop`. Its [PM2 configuration](../../server/ecosystem.config.js) runs the headless Rust server on port 9877 with CUDA GPU access.

For terminal mode, use `make server-run`, `make local-client-run`, or `make raspi-client-run`.

After updating the client, run `make raspi-client-setup` and `make raspi-client-restart` to refresh the installed commands and restart live mode.

[Section index](index.md) · [Wiki index](../documentation/overview.md)
