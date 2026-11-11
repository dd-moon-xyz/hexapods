# Hexapods Local Client

Windowed desktop viewer for testing the hexapod server with keyboard controls and optional MP4 recording. It has its own Python 3.14 environment and depends only on pygame-ce and websockets. It fetches the simulation preset from the server.

From the repository root, with the server running:

```bash
make local-client-setup
make local-client-run
```

The default server is `ws://127.0.0.1:9876/ws`. To select another server or supply a JSON start configuration, run from `local_client/`:

```bash
uv run local-client --url ws://<server-LAN-IP>:9876/ws
uv run local-client --config config.json --record capture.mp4
```

Hold Space or C for outward escape, or V for boosted inward movement. Release the keys to resume ordinary inward movement. Esc closes the viewer.

Use `make local-client-record` to record `local_client/animation.mp4`; FFmpeg must be installed. For background mode, install PM2, run `make local-client-setup`, then `make local-client-up`. Stop it with `make local-client-stop`. PM2 runs `local-client` from this directory and saves its process list. A graphical desktop session is required in either mode; PM2 restarts the viewer after it exits.

Run tests from this directory with `uv run python -m unittest discover -s tests -v`. See [client configuration](../wiki/operation/configuration.md) and [controls](../wiki/operation/controls.md) in the shared wiki.
