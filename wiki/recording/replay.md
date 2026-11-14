---
type: Documentation
title: Replay
---

# Replay

`make replay` collects 30 seconds of JPEG frames at the server preset FPS on its first run, then plays them fullscreen in a continuous loop. Later runs use the saved recording without contacting the server. Playback uses a fixed frame rate and ignores capture delays. Frames are preloaded into memory and stored in `recordings/default/`, which Git ignores. Up to four worker threads load compressed JPEGs and decode upcoming frames in order, with a bounded queue; drawing remains on the main thread. Preloading shows a gray ASCII `tqdm` bar with the exact frame total, percentage, elapsed time, and estimated remaining time; the same loading bar appears before single-hexapod playback. After drawing the first frame, playback prints the frame count, FPS, and duration of each loop. Ctrl+C exits foreground playback; movement keys are ignored and Esc exits.

Stop the live client with `make raspi-client-stop` before replay so both processes do not use the display at once. Use `make replay-start`, `make replay-stop`, `make replay-restart`, and `make replay-logs` to manage replay through PM2. PM2 saves the process list for startup restoration and restarts replay after an exit, including closing its window; use `make replay-stop` to keep it stopped.

See [frame collection](collection.md) to capture a fresh recording or customize collection settings. `make single-hexapod` records and loops a separate top-left to bottom-right crossing, restarting at the upper corner after the hexapod fully disappears. Both live clients include this red/orange crossing as an offline fallback: the shared package bundles 153 JPEG frames at 800×800 and 60 FPS (2.55 seconds) in a roughly 1.52 MB archive. It plays during startup connection attempts and whenever server communication fails, including preset errors, rejected connections, disconnects, and streams that deliver no frames for 15 seconds. Connection attempts repeat after a three-second delay while the animation continues, and the first new live frame automatically replaces it. No connection or FFmpeg installation is needed to play the bundled fallback. See [CUDA preview recording](../simulation/python-experiments.md).

Use `uv run --locked hexapods-replay --windowed` for a window, or `--directory recordings/new` to select another recording directory (capturing if no recording exists). Replay also accepts `--url`, `--config`, and `--seconds` (default 30).

[Section index](index.md) · [Wiki index](../documentation/overview.md)
