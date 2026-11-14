---
type: Documentation
title: CUDA Preview Recording
---

# CUDA Preview Recording

Run `make single-hexapod` on the Raspberry Pi to record one large hexapod walking from the top-left corner to the bottom-right corner, then play that crossing in a continuous loop. It uses `SERVER_ADDRESS` from `client/raspi/.env` to capture frames over the internet. The hexapod fully exits before the recording loops back to its entrance. The preview fills a square black canvas without the live simulation's circular mask. Escape or Ctrl+C exits playback.

Install FFmpeg on the Pi and run `make raspi-client-setup` to install the command. The GPU server must already be running an updated build with preview support; this command does not start or restart it. Stop other viewers before fullscreen playback. The first run saves JPEG frames, a manifest, and `animation.mp4` in `client/raspi/recordings/single-hexapod/`; later runs replay the saved frames without contacting the server. From `client/raspi/`, use `uv run --locked hexapods-preview --record-only` to create a fresh capture without opening a display, or `uv run --locked hexapods-preview --windowed` for a window. `--url` and `--directory` override the server and recording location. Interrupted captures leave the previous recording available. Capture ends after the walker has crossed the center and the entire image is black; a 7200-frame limit rejects incomplete crossings.

Use `make local-client-record` to record the ordinary live simulation to `client/local/animation.mp4`. See [Python recording options](../../client/local/README.md).

[Wiki overview](../documentation/overview.md)
