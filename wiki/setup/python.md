---
type: Documentation
title: Python environment
---

# Python environment

From the repository root (`/home/bastian/projects/hexapods`):

```bash
make raspi-client-setup
```

This uses the installed `uv` in `~/.local/bin` to download a uv-managed Python 3.14 and sync the client and its dependencies into `raspi_client/.venv`. The project requires uv-managed Python and does not inherit system Python packages or require the OS's `python3-venv` package.

The display dependency is `pygame-ce`, which supplies the `pygame` module and prebuilt Python 3.14 ARM64 wheels.

For local desktop testing, run `make local-client-setup`. It creates `local_client/.venv` with pygame-ce and websockets, independently of the server and Raspberry Pi environments. Run local tests from `local_client/` and hardware-client tests from `raspi_client/` using `uv run python -m unittest discover -s tests -v`.

[Section index](index.md) · [Wiki index](../documentation/overview.md)
