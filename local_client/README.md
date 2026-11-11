# Hexapods Rust Client

Desktop viewer written in Rust with SDL3 and libjpeg-turbo. It imports [client_core](../client_core/README.md), also used by the Raspberry Pi client, for rendering, decoding, streaming, capture, and replay. Only desktop startup and keyboard controls live here. It fetches the server preset, displays full-resolution JPEG frames, sends keyboard controls, and optionally records MP4 video.

Install Rust 1.85 or later with Cargo, a C compiler, CMake, `pkg-config`, NASM on x86, and the SDL3 development package. On Debian/Ubuntu with SDL3 packages available:

```bash
sudo apt install build-essential cmake pkg-config nasm libsdl3-dev
```

With the server running, build and launch from the repository root:

```bash
make local-client-setup
make local-client-run
```

The Make setup command builds an optimized release binary using `Cargo.lock`. It builds the SIMD JPEG decoder from bundled sources; SDL3 is linked from the system. Rebuild after source changes. A graphical desktop and the SDL3 runtime are required on the viewing machine; Python, Go, and CUDA are not required there. Linux supports SDL's X11 or Wayland backends.

The default server is `ws://127.0.0.1:9877/ws`. From `local_client/`, select another server, use an explicit JSON start configuration, or record video:

```bash
./target/release/local-client --url ws://<server-LAN-IP>:9877/ws
./target/release/local-client --config config.json --record capture.mp4
```

Without `--config`, the client fetches `/preset` from the selected server. Secure `wss://` connections and HTTPS presets use certificate verification. `--help` lists the CLI options.

Hold Space or C for boosted outward escape, or V for boosted inward movement. The most recently pressed held key takes priority. Releasing all keys or losing window focus restores ordinary inward movement. Esc, the close button, or Ctrl+C exits.

The network thread requests the next frame before handing the current JPEG to the display thread. A bounded two-frame queue overlaps server work with display work. A reusable libjpeg-turbo decoder writes directly into a reusable SDL streaming texture, avoiding an intermediate RGBA allocation and copy. The original WebSocket JPEG buffer moves through display and recording without copying its bytes. Repeated control messages use static buffers. Opaque frames cover the entire window, so rendering disables alpha blending and avoids a redundant screen clear. Frames retain their source resolution, and high-DPI window sizing accounts for pixel density.

Use `make local-client-record` to record `local_client/animation.mp4`; FFmpeg must be installed. Recording preserves displayed frame intervals in a 1080×1920 H.264 MP4 with black padding, with frame timing preserved. Shutdown finalizes the last displayed frame and closes the encoder.

For background mode, install PM2, run `make local-client-setup`, then `make local-client-up`. Stop it with `make local-client-stop`. PM2 runs the release binary under the distinct name `local-client` and saves its process list. It requires an active graphical session and restarts the viewer after it exits.

Run `make local-client-test` for configuration, CLI, control priority, recording timing, and WebSocket integration checks. These tests use local mock servers and do not require CUDA or a desktop. `cargo fmt --check` and `cargo clippy --release --locked --all-targets -- -D warnings` check formatting and code quality.

An optional `cargo build --release --locked --features bundled-sdl` build compiles SDL3 from source as well. It requires the platform-specific development dependencies listed in [SDL's Linux build guide](https://wiki.libsdl.org/SDL3/README-linux#build-dependencies).

See [client configuration](../wiki/operation/configuration.md) and [controls](../wiki/operation/controls.md) in the shared wiki.
