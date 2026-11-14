# Hexapods Rust Server

HTTP/WebSocket server written in Rust with Axum, Tokio, and libjpeg-turbo. The C++/CUDA simulation core lives in `native/`. Configuration validation, connection handling, organism replacement, image processing, and JPEG encoding run in Rust.

The Rust server has **no frame-rate pacing or FPS ceiling**. Each `next` request advances the simulation and returns a fresh JPEG as soon as CUDA, encoding, and the connection allow. It does not repeat a prepared image or sleep between frames.

Install Rust 1.85+, a C/C++ compiler, CMake, `pkg-config`, and NASM on x86 for the bundled SIMD JPEG library. The CUDA worker also needs the [native server toolchain](../wiki/setup/linux.md) and an NVIDIA GPU with a compatible driver at runtime. SDL, Python, and a graphical desktop are not required by this server.

From the repository root:

```bash
make server-setup
make server-run
```

Setup builds the existing CUDA executable and the locked Rust release binary. The default address is `0.0.0.0:9877`. Authentication is required by default. Set `HEXAPODS_TOKEN_HASHES` to comma-separated `client:sha256hex` entries (one independent token per client). For trusted local development only, pass `--allow-unauthenticated`. Each token permits one active simulation connection.

Edit `server/.env` directly using [`.env.example`](.env.example): set `HEXAPODS_TOKEN_HASHES` to comma-separated `local:sha256hex,raspi:sha256hex` entries, `SERVER_BIND` to the listen address, and optionally `HEXAPODS_BROWSER_ORIGIN` for browser login. Store only token hashes on the server. Add or replace an entry to add or rotate a token; remove an entry to revoke it. Restart the server to apply changes (`make server-restart` for PM2). Process environment variables take precedence over `.env`.

For internet access, bind the server to `127.0.0.1:9877` behind a TLS reverse proxy with WebSocket upgrade support. Connect clients using `wss://your-host/ws`; keep port 9877 private. TLS termination and certificates must be configured on the deployment host. Set `HEXAPODS_BROWSER_ORIGIN=https://your-host` to enable browser login from that exact origin. The viewer exchanges its API token for a Secure, HttpOnly, SameSite=Strict cookie valid for one hour; cookies require HTTPS. Invalid credentials are rejected before WebSocket upgrade or worker creation. Browser login sessions are held in memory and cleared on restart. An already connected WebSocket lasts until it closes or the server restarts.

Connect the Python local client:

```bash
make local-client-setup
make local-client-run
```

Edit `client/local/.env` or `client/raspi/.env` directly: set `SERVER_URL` and the original `HEXAPODS_TOKEN` for that client. See the [local example](../client/local/.env.example) and [Raspberry Pi example](../client/raspi/.env.example). Use `wss://your-host/ws` for internet access, or `ws://server-LAN-IP:9877/ws` for a trusted LAN. Existing run, record, collect, replay, and PM2 targets load their respective `.env` files automatically. Restart background clients with `make local-client-restart` or `make raspi-client-restart` after changes.

`GET /` serves the existing browser viewer. `GET /preset` returns 50 organisms in a 1024×1024 circular world. `/ws` accepts the existing start configuration, `next`, `stop`, radial controls, and vector movement JSON. Optional population messages precede JPEG frames. World/output sizes, pixelation, birth-rate bounds, scale bounds (`scale_min`/`scale_max`, default random float 1.0–1.1), and interaction-count bounds follow the existing API. Unknown fields and invalid values are rejected.

The legacy `fps` start field is retained as a positive recording-rate hint, defaulting to 60. It neither throttles delivery nor imposes an upper bound on delivered FPS; the start response includes `fps_limit: null`. A client can record at that rate independently of actual delivery throughput. The native worker's separate reference value of 60 is used only by its injury integration and never sleeps or limits rendering. The simulation still advances by its configured `dt` per requested frame, so uncapped playback can advance simulation time faster as delivery speeds up.

Every connection owns a separate native process, frame buffers, JPEG compressor, and birth tasks. Initial slots remain inactive until their serialized birth delays expire. Dead slots queue replacements after five empty frames; outward escape suppresses births, and inward movement restores them. Frame generation has no pacing sleep; only organism births use the configured birth delays. Disconnects, errors, and shutdown cancel pending births and terminate native workers.

The server flips bottom-up CUDA RGB rows, applies optional box-filter pixelation/resizing, and encodes quality-80 JPEGs with 4:2:0 subsampling. Smaller unpixelated outputs use the CUDA worker's existing GPU resizing command. Accepted TCP connections enable `TCP_NODELAY` to avoid delayed delivery of population metadata followed by JPEG frames.

Use `make server-test` for validation, image orientation/resizing, native command framing, birth gating, and HTTP/WebSocket integration tests. Tests use a synthetic native-protocol fixture and do not need CUDA. `cargo fmt --check` and `cargo clippy --release --locked --all-targets -- -D warnings` check formatting and code quality. Real performance comparisons must use the actual CUDA worker, identical scenes, and the same output resolution; synthetic image streaming measures client capacity only.

A real-CUDA comparison on a GTX 1060 6 GB used a local measuring WebSocket relay, three alternating runs per client, 150 warmup frames, and six measured seconds per run at 1024×1024 with 50 live organisms. The benchmark set birth rates to 1000 and interaction allowances to 1,000,000 to keep the population constant, with quality-80 JPEGs and no frame pacing. Python averaged **91.46 FPS** (91.06–91.75), and Rust averaged **91.99 FPS** (90.63–93.23). They were effectively tied in this workload. A separate 256×256 one-organism probe delivered about 692 FPS with `fps: 1`, verifying that the legacy recording hint does not throttle delivery. These are hardware- and scene-specific stream-throughput measurements, not general language performance claims.

For background mode, install PM2, run `make server-setup`, then `make server-up`. Stop it with `make server-stop`. Its distinct PM2 process name is `server`. Ctrl+C stops foreground mode and cleans up active simulations.
