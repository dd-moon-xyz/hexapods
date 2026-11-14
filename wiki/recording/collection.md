---
type: Documentation
title: Frame collection
---

# Frame collection

Run `make collect` to collect a fresh recording without opening a display, then `make replay` to play it. Each capture stages a new JPEG generation and switches the manifest only after success. Interrupted captures preserve the previous recording; successful captures publish uniquely named frame generations.

For custom collection settings:

```bash
uv run --locked hexapods-collect --seconds 30 --output-size 800 --directory recordings/new
```

The collector also accepts `--url` and `--config`. For one large hexapod crossing diagonally instead of the live population, use `make single-hexapod`; see [CUDA preview recording](../simulation/python-experiments.md) for capture-only and MP4 output options.

See [replay](replay.md) to play saved frames.

[Section index](index.md) · [Wiki index](../documentation/overview.md)
