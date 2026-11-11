---
type: Documentation
title: Linux Build and Run
---

# Linux Build and Run

## Compile on Linux

The native worker needs an NVIDIA GPU for execution, a compatible NVIDIA driver, a CUDA Toolkit, CMake 3.24 or newer, and a CUDA-compatible C++20 compiler. It uses CUDA runtime kernels without OpenGL, cuFFT, fonts, or external organism data.

For a host build, install the toolchain appropriate to your distribution and run from `server/`:

```bash
cmake --fresh -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --target lenia --parallel 2
ctest --test-dir build -R '^compilation$' --output-on-failure --no-tests=error
```

## Run

Run all Make commands from the repository root. The server runs in Docker; the host needs Docker Compose, NVIDIA Container Toolkit, and a compatible NVIDIA driver and GPU:

```bash
make server-build
make server-up
```

Open `http://<server-LAN-IP>:9876/` in a browser or configure the Pi with `ws://<server-LAN-IP>:9876/ws`. Clients need access to port 9876. The API is for a trusted local network and has no authentication. Each connection gets an independent simulation and controls.

Use `make server-stop` to stop the container. After changes, run `make server-build` and `make server-up` to rebuild and recreate it. Both foreground and background server commands use the fixed container name `server-lenia`. Use `make server-run` for foreground server logs, `make local-client-run` for the desktop viewer, and `make local-client-record` to record that viewer. Run `make local-client-setup` first to create its independent environment. `make local-client-up` uses PM2 for background mode. See [Pi setup](index.md) for display and hardware requirements.

The image installs locked Python dependencies into system Python. Host Python and a host CUDA Toolkit are not needed for the Docker server. The [Dockerfile](../../server/Dockerfile) and [Compose configuration](../../server/docker-compose.yml) define core, app, and development targets. `make core-build` builds the toolchain; `make devcontainer-build` builds the development environment for VS Code’s Reopen in Container. The devcontainer installs the package in editable mode into system Python under `/workspace`.

## Build details

CMake compiles only the hexapod entry point and CUDA renderer into `build/lenia`. The CUDA architecture is set to `61` for the GTX 1060; change `CMAKE_CUDA_ARCHITECTURES` in [CMakeLists.txt](../../server/CMakeLists.txt) for another GPU target. The compiler selection probe checks installed host compilers for CUDA C++20 compatibility. Compilation itself does not require a GPU.

The Docker image copies the CUDA 12.9.2 toolkit into Ubuntu 26.04 and uses GCC 14. Its math-header patch matches glibc exception declarations. The server runs headlessly without X11 or Wayland. The [CI compilation workflow](../../.github/workflows/compilation.yml) builds the native target on push.

From `server/`, run `uv run python -m unittest discover -s tests -v` for Python and synthetic-worker integration tests. The resize tests compare the shared CUDA box-filter arithmetic against Pillow using a C++ compiler. Run `LENIA_GPU_TESTS=1 uv run python -m unittest discover -s tests -p test_native_hexapods.py -v` on a CUDA host to test escape death, population injury, replacement entry, and resized-frame alignment.

## Startup troubleshooting

Check the NVIDIA driver, GPU access in Docker, and architecture compatibility when the worker fails to acknowledge startup. A protocol change requires rebuilding the native binary and restarting the server and clients together. Update saved configurations to remove numeric `type`, `velocity`, and `excluded_types` fields; only hexapod simulation and circular boundaries are accepted. See [the protocol](../simulation/architecture.md) and [client troubleshooting](../operation/troubleshooting.md).

[Wiki overview](../documentation/overview.md)
