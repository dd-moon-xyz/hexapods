---
type: Documentation
title: Foreground and controls
---

# Foreground and controls

Stop the managed viewer before launching another one:

```bash
make raspi-client-stop
make raspi-client-run
```

Set `LENIA_WINDOWED=true` in `.env` for an 800×800 window. Ctrl+C exits a foreground client. Keyboard events are ignored by both the live client and replay.

See [sensor controls](sensor-controls.md) for circle-mode proximity and motion behaviour.

`make raspi-client-run` selects Wayland and defaults to `XDG_RUNTIME_DIR=/run/user/<your UID>` and `WAYLAND_DISPLAY=wayland-0`, matching PM2. Override those variables when the desktop uses a different socket. Startup logs show the SDL driver and display size. When launching with `uv run` directly from SSH, supply these variables too; otherwise SDL may select an invisible offscreen display.

[Section index](index.md) · [Wiki index](../documentation/overview.md)
