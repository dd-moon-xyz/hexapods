---
type: Documentation
title: Rust client environment
---

# Rust client environment

From the repository root (`/home/bastian/projects/hexapods`):

```bash
make raspi-client-setup
```

This builds the locked Rust release binary in `raspi_client/target/release/raspi-client`. The Pi imports the shared `client_core` Rust library for rendering, WebSocket streaming, capture, and replay. Python and uv are no longer required.

Install Rust 1.85+, SDL3 development headers, a C compiler, CMake, and `pkg-config`. Install `imx500-all` for native camera inference and the existing firmware/model. Use a 64-bit Raspberry Pi OS desktop. The Pi client does not require CUDA.

Desktop testing uses the [same Rust + SDL3 viewer](../../local_client/README.md). Use `make local-client-test` for shared protocol/capture tests and `make raspi-client-test` for Pi sensor logic. Real camera, I²C, and PWM operation must also be verified on the Pi.

[Section index](index.md) · [Wiki index](../documentation/overview.md)
