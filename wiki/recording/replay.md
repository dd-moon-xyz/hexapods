---
type: Documentation
title: Replay
---

# Replay

`make replay` collects 30 seconds of JPEG frames at the server preset FPS on its first run, then plays them fullscreen in a continuous loop. Later runs use the saved recording without contacting the server. Playback uses a fixed frame rate and ignores capture delays. Frames are preloaded into memory and stored in `recordings/default/`, which Git ignores. Ctrl+C exits foreground playback; keyboard events are ignored.

Stop the live client with `make raspi-client-stop` before replay so both processes do not use the display at once. Use `make replay-start`, `make replay-stop`, `make replay-restart`, and `make replay-logs` to manage replay through PM2. PM2 saves the process list for startup restoration and restarts replay after an exit, including closing its window; use `make replay-stop` to keep it stopped.

See [frame collection](collection.md) to capture a fresh recording or customize collection settings.

Use `uv run lenia-replay --windowed` for a window, or `--directory recordings/new` to select another recording directory (capturing if no recording exists). Replay also accepts `--url`, `--config`, and `--seconds` (default 30).

[Section index](index.md) · [Wiki index](../documentation/overview.md)
