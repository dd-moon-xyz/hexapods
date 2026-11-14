---
type: Documentation
title: Linux Build and Run
---

# Linux Build and Run

## Compile on Linux

Install Rust 1.85+, a C/C++ compiler, CMake 3.24+, `pkg-config`, NASM on x86, and a CUDA Toolkit with a compatible C++20 host compiler. Runtime needs an NVIDIA GPU and compatible driver.

CMake must be installed on the system and available on PATH before building the server. On Debian, Ubuntu, or Raspberry Pi OS:

```bash
sudo apt update
sudo apt install cmake
cmake --version
```

For the native server, verify that the installed CMake version is at least 3.24. `make rust-setup` installs CMake using `sudo apt update` and `sudo apt install -y cmake`.

Run `make rust-setup` to install or update stable Rust, Cargo, rustfmt, and Clippy through rustup. See the [environment guide](python.md) for server Rust PATH setup and client Python environment behavior. This command requires sudo access and an apt-based system. CUDA and the other build prerequisites are installed separately.

```bash
make server-setup
```

Both viewers use Python/Pygame and share `client/core/`. Install uv, then set up the required client:

```bash
make local-client-setup
make raspi-client-setup
```

These commands install locked dependencies into separate managed Python 3.14 environments. Pygame binary wheels include SDL2; SDL3 development libraries are no longer needed. Source builds may require SDL2 development packages. The Pi camera separately needs `sudo apt install python3-picamera2 imx500-all`. See [client prerequisites](../../client/local/README.md) and [server prerequisites](../../server/README.md).

## Run

From the repository root, run `make server-run`, then `make local-client-run` in another terminal. Both default to port 9877. The browser viewer is at `http://<server-LAN-IP>:9877/`. Configure the Pi with `SERVER_ADDRESS=<server-LAN-IP>:9877`. Each authenticated connection owns an independent simulation, with one active connection per token. Configure token hashes and client credentials as described in [server setup](../../server/README.md). Internet connections require a TLS reverse proxy and `wss://`; use `--allow-unauthenticated` only for trusted local development.

The [Python local client](../../client/local/README.md) and [Pi client](../../client/raspi/README.md) use the same shared viewer. The Rust client implementations have been removed; the Rust server remains.

`make server-up` and `make local-client-up` use PM2. Stop them with the corresponding `-stop` commands. The server is headless; the desktop viewer requires a graphical session. Server frames have no FPS pacing.

## Build details

The [native CMake project](../../server/native/CMakeLists.txt) compiles `server/native/build/lenia`. Its CUDA architecture is 61 for GTX 1060; adjust `CMAKE_CUDA_ARCHITECTURES` for another target. Compilation does not require a GPU. The [CI workflow](../../.github/workflows/compilation.yml) builds the native target on push.

Run `make server-test` and `make local-client-test` for synthetic protocol and integration tests without CUDA. Both `make local-client-test` and `make raspi-client-test` run Python tests in parallel with `pytest-xdist` (`pytest -n auto`). Run `ctest --test-dir server/native/build --output-on-failure` for native checks. Real simulation testing requires GPU access.

## Startup troubleshooting

Check NVIDIA driver access and architecture compatibility if the worker fails to acknowledge startup. Rebuild the native worker after protocol changes. The Rust server and Python viewers use port 9877; start the server before the client. See [the protocol](../simulation/architecture.md) and [client troubleshooting](../operation/troubleshooting.md).

[Wiki overview](../documentation/overview.md)
