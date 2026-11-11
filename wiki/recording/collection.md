---
type: Documentation
title: Frame collection
---

# Frame collection

Run `make collect` to collect a fresh recording without opening a display, then `make replay` to play it. Every collection deletes previous JPEG frames and the manifest in the selected directory before contacting the server.

For custom collection settings:

```bash
uv run lenia-collect --seconds 30 --output-size 800 --directory recordings/new
```

The collector also accepts `--url` and `--config`.

See [replay](replay.md) to play saved frames.

[Section index](index.md) · [Wiki index](../documentation/overview.md)
