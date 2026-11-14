# Hexapods Raspberry Pi Client

Python hardware entry point using the same [client_core](../core/README.md) renderer, WebSocket pipeline, recording, capture, and replay as the local client. Pi-specific code in `src/hexapods_client/` supplies camera proximity, I²C motion, PWM population indication, and validated `.env` settings.

Use a 64-bit Raspberry Pi OS desktop. Install uv and the system camera packages:

```bash
sudo apt update
sudo apt install python3-picamera2 imx500-all
make raspi-client-setup
cp client/raspi/.env.example client/raspi/.env
# Set SERVER_ADDRESS to the Rust server's LAN address, port 9877.
make raspi-client-run
```

Setup installs managed Python 3.14 with locked dependencies. The camera helper runs `/usr/bin/python3` to access Raspberry Pi OS's Picamera2/libcamera packages and the installed IMX500 model. The previous Python camera path is restored; native `rpicam-vid` metadata parsing is removed. Rust, CUDA, and SDL3 are not Pi-client requirements. Pygame wheels provide SDL2; source builds may need SDL2 development libraries.

The client uses fullscreen Wayland by default, or an 800×800 window with `WINDOWED=true`. It fits frames with nearest-pixel sampling and letterboxing. Camera proximity overrides motion; the LED follows living population. Sensors update every 50 ms. Camera model loading allows 180 seconds for the first inference, then five seconds between samples. Camera, motion, LED, and stream resources are closed on exit.

Use `make collect` for a fresh capture and `make replay` to loop JPEG frames. Replay captures when no manifest exists. From `client/raspi/`:

```bash
uv run --locked hexapods-collect --seconds 30 --output-size 800 --directory recordings/new
uv run --locked hexapods-replay --directory recordings/new --windowed
```

`make raspi-client-test` checks settings and hardware logic with synthetic inputs. `make local-client-test` checks the shared viewer and protocol. Actual camera, I²C, and PWM operation still need validation on the Pi.

PM2 commands and process names are `hexapods-client` and `hexapods-replay`. Delete existing process entries before recreating them with `make raspi-client-up` or `make replay-start`, then save the PM2 process list. Run `make raspi-client-setup` first to install the renamed commands. See the [wiki](../../wiki/documentation/overview.md) for permissions, wiring, and desktop startup.
