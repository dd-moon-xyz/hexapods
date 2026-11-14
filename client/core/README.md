# Hexapods Client Core

Shared Python package used by both clients through editable uv path dependencies. `src/client_core/client.py` owns preset loading, WebSocket streaming, and keyboard controls. `rendering.py` owns the DPI-aware SDL2/Pygame renderer, reusable textures, nearest-pixel sampling, and fullscreen letterboxing. `preview.py` captures the fallback crossing; `fallback.py` displays the downloaded animation while disconnected. Client setup downloads the GitHub Release asset pinned in `src/client_core/assets/fallback.json` and verifies its SHA-256 checksum. The ZIP is ignored by Git. Use `make fallback-record` to regenerate it and `make fallback-publish` to upload it and update the metadata (requires GitHub write authentication).

`client/local/` supplies the desktop entry point. `client/raspi/` supplies camera, motion, PWM, and settings; it passes a sensor-monitor callback into the same viewer loop. Population messages update the Pi LED state. No shared code depends on Pi hardware.

Run `make local-client-test` for shared tests, and `make raspi-client-test` for hardware logic with synthetic inputs. Both clients require uv and managed Python 3.14; setup targets create their environments using locked dependencies. The Pi camera helper separately uses system Python and Picamera2.
