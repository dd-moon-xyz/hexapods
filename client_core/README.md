# Hexapods Client Core

Shared Rust library used directly by `local_client` and `raspi_client`. It contains the SDL3 viewer and JPEG decoder in `src/lib.rs`, WebSocket streaming in `src/stream.rs`, preset loading in `src/config.rs`, MP4 recording in `src/recording.rs`, and frame collection/replay in `src/archive.rs`.

Both clients depend on this crate through Cargo path dependencies. The desktop client owns its CLI and keyboard controls; the Pi client owns hardware settings, camera, motion, and PWM. They supply input through the `Inputs` interface. The core contains no Pi sensor code or desktop CLI.

Build and run through the existing client Make targets. `make local-client-test` runs desktop and shared-core tests; `make raspi-client-test` runs the Pi-specific tests. To test the core alone:

```bash
cargo test --manifest-path client_core/Cargo.toml --release --locked
```

The native requirements match the [desktop viewer](../local_client/README.md): SDL3 development libraries, a C compiler, CMake, pkg-config, and NASM for x86 builds. The `bundled-sdl` feature builds SDL3 from source and is forwarded by the desktop crate.
