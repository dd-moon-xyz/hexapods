# Hexapods Raspberry Pi Client

Rust Raspberry Pi viewer using the same SDL3 renderer, libjpeg-turbo decoder, WebSocket stream, and recording/replay code from [client_core](../client_core/README.md), imported as a Cargo path dependency. The Pi adds native camera, I²C motion, and hardware PWM controls. No Python runtime is used.

Build on a 64-bit Raspberry Pi OS desktop with Rust 1.85+, SDL3 development headers, a C compiler, CMake, and pkg-config. Install `imx500-all` for firmware, models, native `rpicam-vid`, and IMX500 post-processing. NASM is needed only for x86 builds. The Pi does not need CUDA.

From the repository root:

```bash
make raspi-client-setup
cp raspi_client/.env.example raspi_client/.env
# Set LENIA_URL to the server's LAN address.
make raspi-client-run
```

The live client loads `raspi_client/.env`; environment variables override it. Existing `LENIA_*` settings and sensor thresholds are preserved. It uses fullscreen SDL3 on Wayland by default, or an 800×800 window with `LENIA_WINDOWED=true`. It requests the display's square output size and letterboxes frames. Camera proximity overrides motion steering; the LED tracks living population. Esc, closing the window, or Ctrl+C exits. Motion and camera updates run every 50 ms, independently of frame generation.

Camera inference runs in the native `rpicam-vid` process. It loads the same SSD MobileNetV2 model using the installed IMX500 post-processing configuration; Rust reads its raw SSD tensor metadata and applies the existing confidence, height, confirmation, and hysteresis rules. It does not save camera images. Model loading allows 180 seconds before the first inference, then five seconds between inference samples. The camera process, motion sensor, and LED are cleaned up on exit.

Use `make raspi-client-test` for settings, person detection, motion latching, steering priority, and PWM tests. Run `make local-client-test` for the shared rendering pipeline's protocol, capture, replay validation, and recording tests. These synthetic tests do not verify real Pi hardware; check camera detection, motion axes, and PWM on the Pi after installation.

`make collect` captures a fresh recording, and `make replay` loops the stored JPEGs without a server. Replay captures 30 seconds at the server recording FPS when no manifest exists. Capture publishes a complete generation and its manifest only after success; interrupted captures preserve the previous manifest. Examples from `raspi_client/`:

```bash
./target/release/raspi-client collect --seconds 30 --output-size 800 --directory recordings/new
./target/release/raspi-client replay --directory recordings/new --windowed
```

Use `make raspi-client-up`, `make raspi-client-restart`, and `make raspi-client-stop` for PM2. Process names remain `lenia-client` and `lenia-replay`; both now launch the Rust binary. On migration, stop/delete the old PM2 entries, rebuild with `make raspi-client-setup`, then run `make raspi-client-up` or `make replay-start` to recreate them. See the [wiki](../wiki/documentation/overview.md) for hardware permissions, wiring, configuration, and boot startup.
