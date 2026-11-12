# Hexapods Client Core

Shared Python package used by both clients through editable uv path dependencies. `src/client_core/client.py` owns preset loading, WebSocket streaming, keyboard controls, and MP4 recording. `rendering.py` owns the DPI-aware SDL2/Pygame renderer, reusable textures, nearest-pixel sampling, and fullscreen letterboxing. `replay.py` and `collect.py` own JPEG capture and looping playback.

`client/local/` supplies the desktop entry point. `client/raspi/` supplies camera, motion, PWM, and settings; it passes a sensor-monitor callback into the same viewer loop. Population messages update the Pi LED state. No shared code depends on Pi hardware.

Run `make local-client-test` for shared tests, and `make raspi-client-test` for hardware logic with synthetic inputs. Both clients require uv and managed Python 3.14; setup targets create their environments using locked dependencies. The Pi camera helper separately uses system Python and Picamera2.
