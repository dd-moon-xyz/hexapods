---
type: Documentation
title: Troubleshooting
---

# Troubleshooting

Use `make raspi-client-logs` or `PATH="$HOME/.local/bin:$PATH" pm2 describe lenia-client` to inspect failures. For Wayland errors, check that `/run/user/1000/wayland-0` exists and belongs to the desktop user. For connection errors, check the server address and server logs. After changing Python dependencies, rerun `make raspi-client-setup` and `make raspi-client-restart`.

[Section index](index.md) · [Wiki index](../documentation/overview.md)
