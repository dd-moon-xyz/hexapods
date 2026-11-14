---
type: Documentation
title: Python client environment
---

# Python client environment

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and create a client environment from the repository root:

```bash
make local-client-setup
```

For the Raspberry Pi, use `make raspi-client-setup`. Both commands download the pinned fallback Release asset and verify its checksum, then run `uv sync --locked`, download managed Python 3.14 when needed, and install dependencies into each client's `.venv`. No manual activation is required: Make run targets use `uv run --locked`. The shared `client/core/` package is installed as an editable path dependency, so both clients use the same rendering, streaming, and fallback code.

For direct commands:

```bash
cd client/local
uv run --locked local-client --help
```

The clients use Pygame's SDL2 renderer; SDL3, CMake, and Rust are not client requirements when compatible binary wheels are available. Source builds may require SDL2 development packages. See [Linux setup](linux.md) for the Rust/CUDA server prerequisites. The server still uses `make rust-setup` and `make server-setup`; `make rust-setup` installs system CMake through apt and manages stable Rust, Cargo, rustfmt, and Clippy through rustup. Rust tools live in `${CARGO_HOME:-$HOME/.cargo}/bin`; Make adds that directory to PATH. For direct Cargo commands, load `. "${CARGO_HOME:-$HOME/.cargo}/env"` in the shell. Cargo reads `server/Cargo.toml` and the locked dependencies, caches downloads, and writes the release binary under `server/target/release/`. Run `make rust-setup` again to update the toolchain.

Install the [Pi hardware prerequisites](../../client/raspi/README.md), then set up the Pi environment:

```bash
make raspi-client-setup
```

The Pi camera helper runs `/usr/bin/python3`, separately from the managed client interpreter, to use the system's Picamera2 and libcamera bindings. On Raspberry Pi OS, install `sudo apt install python3-picamera2 imx500-all`. The helper loads the existing IMX500 SSD model and sends height metadata to the client. I²C motion and hardware PWM controls remain Python code.

Use a 64-bit Raspberry Pi OS graphical desktop. The Pi does not require CUDA or Rust. Configure `.env` as described in [client configuration](../operation/configuration.md); run `make raspi-client-run` for live mode.

Desktop testing uses the [same Python viewer](../../client/local/README.md). Use `make local-client-test` for shared tests and `make raspi-client-test` for Pi sensor logic. Real camera, I²C, and PWM operation must also be verified on the Pi.

[Section index](index.md) · [Wiki index](../documentation/overview.md)
