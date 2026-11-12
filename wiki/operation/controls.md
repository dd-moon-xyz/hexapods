---
type: Documentation
title: Controls
---

# Controls

The browser viewer at `http://<server-LAN-IP>:9877/` loads the hexapod preset. Edit its JSON configuration and use Start / restart, Pause / Resume, and Stop to control playback. There is no organism selector.

In the browser, hold Space or C for boosted outward escape, or V for boosted inward movement. Releasing the last held key returns to ordinary inward movement. Losing focus releases the control.

The `client/local/` Python/Pygame viewer uses the movement controls below; Esc exits. Start it with `make local-client-run`. Focus loss restores ordinary inward movement.

The Raspberry Pi viewer uses [camera proximity and motion sensors](sensor-controls.md) instead of keyboard controls. `make raspi-client-run` launches the Raspberry Pi viewer in the terminal; `make raspi-client-up` starts it in the background through PM2. Ctrl+C exits foreground live or replay playback. Use `make raspi-client-stop` or `make replay-stop` to stop PM2-managed processes.

[Wiki overview](../documentation/overview.md)
