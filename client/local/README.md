# Hexapods Local Client

Python/Pygame desktop viewer using [client_core](../core/README.md), shared with the Raspberry Pi client. The Rust server remains unchanged.

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run from the repository root:

```bash
make local-client-setup
make local-client-run
```

Setup downloads managed Python 3.14 and installs locked dependencies into `client/local/.venv`. Pygame wheels include SDL2; SDL3 and Rust are not client requirements. A graphical desktop is required. For a remote server or preset:

```bash
cd client/local
uv run --locked local-client --url ws://SERVER:9877/ws --config preset.json
```

Without `--config`, the viewer fetches the server preset. Hold Space/C for outward movement, V for boosted inward movement, and release to restore inward movement. Most recently held keys take priority. Focus loss restores inward movement; Escape exits.

The high-DPI window preserves frame pixels with nearest-pixel texture sampling. Streaming keeps two frame requests in flight and has no FPS cap. `make local-client-record` records an MP4 (install FFmpeg); `make local-client-test` runs shared tests. Use `make local-client-up` and `make local-client-stop` for PM2; recreate an old Rust PM2 process after migration.
