---
type: Documentation
title: CUDA Preview Recording
---

# CUDA Preview Recording

The preview recorder uses the same CUDA hexapod gait, density, fluid, and color kernels as the server. The preview shows one walker traveling from top-left to bottom-right against black, with a fixed camera and palette. It leaves the frame without wrapping or arena clipping.

From the repository root, `make gif` records a 1024×1024 GIF, and `make video` records a 1080×1920 portrait MP4. FFmpeg is required for MP4 encoding. Output is generated under `server/resources/hexapod/`; no resource files are needed to build or start the server.

Run from `server/` for custom recording settings:

```bash
uv run python -m lenia.scripts.record_hexapod_cuda --duration 30 --fps 25 --speed 2
uv run python -m lenia.scripts.record_hexapod_cuda --output resources/hexapod/propulsion.mp4 --speed 5 --story
```

Duration is at most 30 seconds, FPS is 5–60, and speed divided by FPS must not exceed 0.2. `--story` places the square render on a black portrait canvas without stretching or cropping it. Build `server/build/lenia` before recording and run on a CUDA GPU host.

[Wiki overview](../documentation/overview.md)
