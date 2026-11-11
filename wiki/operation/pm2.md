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

The [ecosystem configuration](../../raspi_client/ecosystem.config.js) launches `~/.local/bin/uv run --no-sync lenia-client` with `raspi_client/` as its working directory. Run `make raspi-client-setup` first to sync the environment. It selects the Wayland driver, defaults `WAYLAND_DISPLAY` to `wayland-0`, and derives `XDG_RUNTIME_DIR` from the current user's UID. Existing values of those two variables take precedence. Output is unbuffered for PM2 logs.

PM2 restarts the client after an exit, with a three-second delay. This allows recovery from server restarts or waiting for the desktop to become available. `make raspi-client-start`, `make raspi-client-stop`, and `make raspi-client-restart` save the PM2 process list. They target only `lenia-client`, leaving other PM2 applications alone. Use `make raspi-client-stop` to keep it stopped; closing the window causes PM2 to restart it.

For the local testing viewer, use `make local-client-setup`, then `make local-client-up`. Its separate [ecosystem configuration](../../local_client/ecosystem.config.js) runs `uv run --no-sync local-client` from `local_client/` under the PM2 process name `local-client`; stop it with `make local-client-stop`. It inherits the desktop environment instead of forcing the Raspberry Pi Wayland settings. Neither background mode starts a graphical desktop.

For terminal mode, use `make local-client-run` or `make raspi-client-run`; neither starts PM2.

When upgrading from the old `client/` directory, delete any existing `lenia-client` or `lenia-replay` PM2 entry that still has the old working directory, then start it again using the new Make commands. Sync the environment in `raspi_client/` first.

[Section index](index.md) · [Wiki index](../documentation/overview.md)
