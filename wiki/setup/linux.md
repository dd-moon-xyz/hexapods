---
type: Documentation
title: Linux Build and Run
---

# Linux Build and Run

## Compile on Linux

Install Rust 1.85+, a C/C++ compiler, CMake 3.24+, `pkg-config`, NASM on x86, and a CUDA Toolkit with a compatible C++20 host compiler. Runtime needs an NVIDIA GPU and compatible driver.

CMake must be installed on the system and available on PATH before building the server or either client. On Debian, Ubuntu, or Raspberry Pi OS:

```bash
sudo apt update
sudo apt install cmake
cmake --version
```

For the native server, verify that the installed CMake version is at least 3.24. `make rust-setup` installs CMake and SDL3 development packages using `sudo apt update` and `sudo apt install -y cmake libsdl3-dev`.

Run `make rust-setup` to install or update stable Rust, Cargo, rustfmt, and Clippy through rustup. See the [Rust environment guide](python.md) for PATH setup and dependency/build behavior. This command requires sudo access and an apt-based system providing `libsdl3-dev`. CUDA and the other build prerequisites are installed separately.

```bash
make server-setup
```

Both the desktop and Raspberry Pi viewers require SDL3 installed on the system, including its development package. On Debian/Ubuntu/Raspberry Pi OS releases that provide SDL3 packages:

```bash
sudo apt install libsdl3-dev
pkg-config --modversion sdl3
```

SDL2 does not satisfy this dependency. If your release does not provide `libsdl3-dev`, use the source-build option in the [client prerequisites](../../local_client/README.md). `make rust-setup` installs this package automatically on supported apt-based systems. After installing it, run `make local-client-setup` or `make raspi-client-setup`. The server does not require SDL3. See also [server prerequisites](../../server/README.md).

## Run

From the repository root, run `make server-run`, then `make local-client-run` in another terminal. Both default to port 9877. The browser viewer is at `http://<server-LAN-IP>:9877/`. Configure the Pi with `LENIA_URL=ws://<server-LAN-IP>:9877/ws`. Each connection owns an independent simulation; the API is for a trusted local network.

`make server-up` and `make local-client-up` use PM2. Stop them with the corresponding `-stop` commands. The server is headless; the desktop viewer requires a graphical session. Server frames have no FPS pacing.

## Build details

The [native CMake project](../../server/native/CMakeLists.txt) compiles `server/native/build/lenia`. Its CUDA architecture is 61 for GTX 1060; adjust `CMAKE_CUDA_ARCHITECTURES` for another target. Compilation does not require a GPU. The [CI workflow](../../.github/workflows/compilation.yml) builds the native target on push.

Run `make server-test` and `make local-client-test` for synthetic protocol and integration tests without CUDA. Run `ctest --test-dir server/native/build --output-on-failure` for native checks. Real simulation testing requires GPU access.

## Startup troubleshooting

Check NVIDIA driver access and architecture compatibility if the worker fails to acknowledge startup. Rebuild the native worker after protocol changes. Both Rust binaries use port 9877; start the server before the client. See [the protocol](../simulation/architecture.md) and [client troubleshooting](../operation/troubleshooting.md).

[Wiki overview](../documentation/overview.md)
