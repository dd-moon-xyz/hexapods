---
type: Documentation
title: Controls
---

# Controls

The browser viewer at `http://<server-LAN-IP>:9877/` loads the hexapod preset. Edit its JSON configuration and use Start / restart, Pause / Resume, and Stop to control playback. There is no organism selector.

In the browser, hold Space or C for boosted outward escape, or V for boosted inward movement. Releasing the last held key returns to ordinary inward movement. Losing focus releases the control.

The `client/local/` Python/Pygame viewer uses the movement controls below; Esc exits. Start it with `make local-client-run`. Focus loss restores ordinary inward movement. Both the local and Raspberry Pi live clients display the bundled fallback animation while disconnected and retry the server automatically; live playback resumes when frames return. Esc remains available during offline playback. See [offline fallback](../recording/replay.md).

The Raspberry Pi viewer uses [camera proximity and motion sensors](sensor-controls.md) instead of keyboard controls. `make raspi-client-run` launches the Raspberry Pi viewer in the terminal; `make raspi-client-up` starts it in the background through PM2. Ctrl+C exits the foreground client. Use `make raspi-client-stop` to stop the PM2-managed client.

[Wiki overview](../documentation/overview.md)
