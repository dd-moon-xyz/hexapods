---
type: Documentation
title: Frame collection
---

# Frame collection

Run `make collect` to collect a fresh recording without opening a display, then `make replay` to play it. Each capture stages a new JPEG generation and switches the manifest only after success. Interrupted captures preserve the previous recording; successful captures remove older staged generations.

For custom collection settings:

```bash
./target/release/raspi-client collect --seconds 30 --output-size 800 --directory recordings/new
```

The collector also accepts `--url` and `--config`.

See [replay](replay.md) to play saved frames.

[Section index](index.md) · [Wiki index](../documentation/overview.md)
