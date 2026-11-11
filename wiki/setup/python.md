---
type: Documentation
title: Rust client environment
---

# Rust client environment

From the repository root, install the Rust toolchain first:

```bash
make rust-setup
```

This requires an apt-based system providing `libsdl3-dev`, sudo access, `curl`, HTTPS access, and a C compiler/linker. It first runs `sudo apt update` and `sudo apt install -y cmake libsdl3-dev`. It downloads the [official rustup installer](https://rust-lang.org/tools/install/) when rustup is missing, installs or updates stable Rust with Cargo, rustfmt, and Clippy, and selects stable as your user's default toolchain. The Rust toolchain itself is installed as your user; sudo is used for the system packages. Rust tools live in `${CARGO_HOME:-$HOME/.cargo}/bin`; the Makefile includes that directory in PATH automatically. For direct `cargo` commands in the current terminal, run:

```bash
. "${CARGO_HOME:-$HOME/.cargo}/env"
rustc --version
cargo --version
```

There is no virtual environment to activate. Cargo reads `Cargo.toml`, downloads dependencies into its user cache, and uses `Cargo.lock` for reproducible dependency versions. Release builds go into each crate's `target/release/` directory. Run `make rust-setup` again to update the stable toolchain.

Install the system libraries described in [Linux setup](linux.md) and the [Pi client prerequisites](../../raspi_client/README.md), including system-wide CMake (`sudo apt install cmake` on Debian, Ubuntu, or Raspberry Pi OS). Verify it is available with `cmake --version`; `make rust-setup` installs CMake and SDL3 development packages automatically. Then build the Pi client:

```bash
make raspi-client-setup
```

This builds the locked Rust release binary in `raspi_client/target/release/raspi-client`. The Pi imports the shared `client_core` Rust library for rendering, WebSocket streaming, capture, and replay. Python and uv are no longer required.

Install Rust 1.85+, SDL3 development headers, a C compiler, CMake, and `pkg-config`. Install SDL3 with `sudo apt install libsdl3-dev` on releases providing that package, and verify it with `pkg-config --modversion sdl3`. See [Linux setup](linux.md) for the source-build alternative when the package is unavailable. Install `imx500-all` for native camera inference and the existing firmware/model. Use a 64-bit Raspberry Pi OS desktop. The Pi client does not require CUDA.

Desktop testing uses the [same Rust + SDL3 viewer](../../local_client/README.md). Use `make local-client-test` for shared protocol/capture tests and `make raspi-client-test` for Pi sensor logic. Real camera, I²C, and PWM operation must also be verified on the Pi.

[Section index](index.md) · [Wiki index](../documentation/overview.md)
