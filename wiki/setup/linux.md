---
type: Documentation
title: Linux Build and Run
---

# Linux Build and Run

## Compile on Linux

Install Rust 1.85+, a C/C++ compiler, CMake 3.24+, `pkg-config`, NASM on x86, and a CUDA Toolkit with a compatible C++20 host compiler. Runtime needs an NVIDIA GPU and compatible driver.

```bash
make server-setup
```

For the desktop viewer, install SDL3 development headers and run `make local-client-setup`. See [server prerequisites](../../server/README.md) and [client prerequisites](../../local_client/README.md).

## Run

From the repository root, run `make server-run`, then `make local-client-run` in another terminal. Both default to port 9877. The browser viewer is at `http://<server-LAN-IP>:9877/`. Configure the Pi with `LENIA_URL=ws://<server-LAN-IP>:9877/ws`. Each connection owns an independent simulation; the API is for a trusted local network.

`make server-up` and `make local-client-up` use PM2. Stop them with the corresponding `-stop` commands. The server is headless; the desktop viewer requires a graphical session. Server frames have no FPS pacing.

## Build details

The [native CMake project](../../server/native/CMakeLists.txt) compiles `server/native/build/lenia`. Its CUDA architecture is 61 for GTX 1060; adjust `CMAKE_CUDA_ARCHITECTURES` for another target. Compilation does not require a GPU. The [CI workflow](../../.github/workflows/compilation.yml) builds the native target on push.

Run `make server-test` and `make local-client-test` for synthetic protocol and integration tests without CUDA. Run `ctest --test-dir server/native/build --output-on-failure` for native checks. Real simulation testing requires GPU access.

## Startup troubleshooting

Check NVIDIA driver access and architecture compatibility if the worker fails to acknowledge startup. Rebuild the native worker after protocol changes. Both Rust binaries use port 9877; start the server before the client. See [the protocol](../simulation/architecture.md) and [client troubleshooting](../operation/troubleshooting.md).

[Wiki overview](../documentation/overview.md)
