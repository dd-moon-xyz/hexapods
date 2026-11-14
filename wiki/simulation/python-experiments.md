---
type: Documentation
title: CUDA Preview Recording
---

# CUDA Preview Recording

Run `make single-hexapod` on the Raspberry Pi to record one large hexapod walking diagonally from the upper-left edge of the round display to the lower-right edge, then play that crossing in a continuous loop. The preview uses the standard animation's red/orange palette with bright highlights and is 25% larger than the previous red preview (1.875 times the original preview size). It uses a doubled animation step (`dt: 0.2`) at 60 FPS. It uses `SERVER_URL` or `SERVER_ADDRESS` and `HEXAPODS_TOKEN` from `client/raspi/.env` to capture authenticated frames over the internet. A gray ASCII `tqdm` display reports received frames, elapsed time, and capture rate; the crossing length is determined automatically. The preview uses the live simulation's circular mask, leaving pixels outside the round display black. The hexapod fully exits that circle before the recording loops back to its entrance. Escape or Ctrl+C exits playback.

Install FFmpeg on the Pi and run `make raspi-client-setup` to install the command. The GPU server must already be running an updated build with preview support; this command does not start or restart it. Stop other viewers before fullscreen playback. The first run saves JPEG frames, a manifest, and `animation.mp4` in `client/raspi/recordings/single-hexapod/`; later runs replay the saved frames without contacting the server. From `client/raspi/`, use `uv run --locked hexapods-preview --record-only` to create a fresh capture without opening a display, or `uv run --locked hexapods-preview --windowed` for a window. `--url` and `--directory` override the server and recording location. Interrupted captures leave the previous recording available. Capture ends after the walker has crossed the center and the entire image is black; a 7200-frame limit rejects incomplete crossings.

Changes to preview size or color require rebuilding the CUDA worker on the GPU server. Existing recordings retain their previous appearance and speed; after updating the server, run `uv run --locked hexapods-preview --record-only` from `client/raspi/` to replace the recording, then `make single-hexapod` from the repository root to loop it. Use `make local-client-record` to record the ordinary live simulation to `client/local/animation.mp4`. See [Python recording options](../../client/local/README.md).

[Wiki overview](../documentation/overview.md)
