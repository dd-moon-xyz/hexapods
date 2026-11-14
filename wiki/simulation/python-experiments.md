---
type: Documentation
title: CUDA Preview Recording
---

# CUDA Preview Recording

Run `make fallback-record` to regenerate the bundled offline animation through the standard CUDA renderer and JPEG encoder at native 1024×1024 resolution. It reads `SERVER_URL` or `SERVER_ADDRESS` and `HEXAPODS_TOKEN` from `client/local/.env` and writes JPEG frames and a manifest to `client/core/src/client_core/assets/fallback.zip`. A gray ASCII `tqdm` display reports capture progress. Both live clients play this archive when disconnected. The ZIP is ignored by Git; its release URL and SHA-256 checksum are tracked in `fallback.json`. Run `make fallback-publish` after recording to upload it as a GitHub Release asset and update that metadata. Publishing uses `GH_TOKEN`, `GITHUB_TOKEN`, or an authenticated GitHub CLI. Client setup downloads and verifies the pinned archive through `make fallback-download`.

The GPU server must be running with preview support. Fallback capture uses a 1024×1024 internal grid for the large walker instead of the live simulation’s 128×128 grid, computing finer body and fluid detail directly in CUDA. Fluid distances are adjusted to retain their physical scale. The final frames remain 1024×1024; the improvement comes from higher internal detail rather than image enlargement. Capture follows one large red/orange hexapod crossing diagonally, with `dt: 0.1` and 120 FPS metadata, preserving the previous 60 FPS playback speed with twice as many motion samples. It ends after the walker has crossed the center and the entire image is black; a 7200-frame limit rejects incomplete crossings. Ctrl+C interrupts capture without replacing the bundled archive. FFmpeg is not required.

Changes to preview size or color require rebuilding the CUDA worker on the GPU server and rerunning `make fallback-record`.

[Wiki overview](../documentation/overview.md)
