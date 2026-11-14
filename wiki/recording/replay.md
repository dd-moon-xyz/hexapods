---
type: Documentation
title: Replay
---

# Replay

`make replay` collects 30 seconds of JPEG frames at the server preset FPS on its first run, then plays them fullscreen in a continuous loop. Later runs use the saved recording without contacting the server. Playback uses a fixed frame rate and ignores capture delays. Frames are preloaded into memory and stored in `recordings/default/`, which Git ignores. Ctrl+C exits foreground playback; movement keys are ignored and Esc exits.

Stop the live client with `make raspi-client-stop` before replay so both processes do not use the display at once. Use `make replay-start`, `make replay-stop`, `make replay-restart`, and `make replay-logs` to manage replay through PM2. PM2 saves the process list for startup restoration and restarts replay after an exit, including closing its window; use `make replay-stop` to keep it stopped.

See [frame collection](collection.md) to capture a fresh recording or customize collection settings. `make single-hexapod` records and loops a separate top-left to bottom-right crossing, restarting at the upper corner after the hexapod fully disappears. See [CUDA preview recording](../simulation/python-experiments.md).

Use `uv run --locked hexapods-replay --windowed` for a window, or `--directory recordings/new` to select another recording directory (capturing if no recording exists). Replay also accepts `--url`, `--config`, and `--seconds` (default 30).

[Section index](index.md) · [Wiki index](../documentation/overview.md)
