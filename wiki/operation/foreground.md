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

The local and Raspberry Pi `-run`, `-up`, and `-restart` Make targets first run `make fallback-download`. It downloads a missing or outdated animation and checks its SHA-256 checksum; an already verified archive is reused without network access.

Set `WINDOWED=true` in `.env` for an 800×800 window. Ctrl+C exits a foreground client. Movement keys are ignored by the Pi live client; Esc exits.

See [sensor controls](sensor-controls.md) for circle-mode proximity and motion behaviour.

`make raspi-client-run` selects Wayland and defaults to `XDG_RUNTIME_DIR=/run/user/<your UID>` and `WAYLAND_DISPLAY=wayland-0`, matching PM2. Override those variables when the desktop uses a different socket. When launching the Python client directly from SSH, supply these variables too; otherwise SDL may select an invisible offscreen display.

[Section index](index.md) · [Wiki index](../documentation/overview.md)
