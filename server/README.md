# Hexapods Server

Headless CUDA simulation of six-arm hexapods, streamed as JPEG frames over WebSocket. Each viewer gets an independent circular arena with GPU gait animation, fluid trails, contact injury, and replacement births. Camera proximity and motion commands steer the creatures.

From the repository root:

```bash
make server-build
make server-up
```

The host needs an NVIDIA GPU, a compatible driver, Docker Compose, and NVIDIA Container Toolkit. Open `http://<server-LAN-IP>:9876/` for the browser viewer. Use `make server-stop` to stop the server. See [Linux setup](../wiki/setup/linux.md) and [the wiki](../wiki/documentation/overview.md).

The default preset contains 50 hexapods at 60 FPS in a 1024×1024 arena. The server supports only hexapod simulation and circular boundaries. No catalog, organism types, fonts, OpenGL, or cuFFT are required. Existing Python package and executable names remain `lenia`.

Rebuild and restart the server and clients together after native protocol changes. Saved JSON configurations must omit `type`, `velocity`, and `excluded_types`; each entry in `organisms` contains only `scale`, `x`, and `y`. See [architecture and protocol](../wiki/simulation/architecture.md).

## Credits

This project originated as a fork of [DeepQuantum/Lenia](https://github.com/DeepQuantum/Lenia), based on work by Bert Wang-Chak Chan. The current runtime uses the custom CUDA hexapod renderer. See [project credits](../wiki/documentation/credits.md).
