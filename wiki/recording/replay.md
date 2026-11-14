---
type: Documentation
title: Replay
---

# Replay

Standalone replay has been removed. Offline fallback remains part of the live clients.

Both live clients include this red/orange crossing as an offline fallback: the clients use JPEG frames at 1024×1024 and 120 FPS in `client/core/src/client_core/assets/fallback.zip`. The frames use the standard live stream’s CUDA renderer and JPEG encoder without reducing the output resolution. The fallback walker is computed on a 1024×1024 internal CUDA grid for finer detail at its large display size. The local window starts at the standard 1024×1024 size, and offline playback preserves the current window size when switching from live frames. Run `make fallback-record` with the GPU server running to regenerate the bundled archive using the local client’s connection settings. It plays during startup connection attempts and whenever server communication fails, including preset errors, rejected connections, disconnects, and streams that deliver no frames for 15 seconds. Connection attempts repeat after a three-second delay while the animation continues, and the first new live frame automatically replaces it. The archive is a GitHub Release asset, excluded from Git. Both client setup targets run `make fallback-download` to fetch the version pinned in `client/core/src/client_core/assets/fallback.json`, verify its SHA-256 checksum, and keep it locally. After setup, playback needs no connection or FFmpeg installation. After regenerating the archive, run `make fallback-publish` with GitHub write authentication to publish it and update the pinned metadata. See [CUDA preview recording](../simulation/python-experiments.md).
