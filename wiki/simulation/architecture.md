---
type: Documentation
title: Technical Overview
---

# Technical Overview

The server runs only the six-arm hexapod simulation. FastAPI starts an independent CUDA subprocess for each WebSocket connection. The independent local viewer displays JPEG frames with keyboard controls. The Raspberry Pi displays JPEG frames and sends camera proximity and motion commands. No organism catalog, font, OpenGL context, or FFT library is used.

### CUDA

The [native worker](../../server/source/lenia/stream_hexapod.cu) updates six-arm gait, body density, contact injury, fluid trails, palettes, and image composition on the GPU. Each walker has its own size, palette, heading, health, feet, and fluid field. At every birth it receives a uniformly random integer interaction allowance from the inclusive `interaction_count_min`–`interaction_count_max` start parameters (defaults: 1–10). Both bounds must be positive integers and the minimum must not exceed the maximum. Each new body contact with a peer consumes one interaction; continuous contact counts once, and separation permits another interaction with that peer. Simultaneous contacts with different peers count separately. Contact injury and irreversible fading begin on the interaction that exhausts the allowance. Straight trajectories reflect only at the hidden outer limit, after the whole sprite leaves the visible circle. Escape kills walkers at the visible edge; ordinary inward mode enables replacement births outside the circle. Dead walkers stay dead until replaced.

The native executable is `server/build/lenia`; Server Python modules retain the `lenia` package name. Desktop viewer code lives in `local_client/src/local_client/`; Raspberry Pi code lives in `raspi_client/src/lenia_client/`. Each client has its own dependencies and connects over HTTP/WebSocket without importing server code. These are existing entry-point names, and the executable accepts only `--stream-hexapod` and `--stream-hexapod-preview`.

Startup input is `size fps dt space_speed_multiplier count`, followed by `count` lines of `scale x y`. There is no numeric organism type or catalog-derived ID. The worker acknowledges successful startup with `READY`.

- `n`: emits `count` float32 masses, then packed RGB image bytes.
- `s <output_size>`: changes output dimensions, acknowledges `READY`. Downsampling uses CUDA box filters before readback.
- `r <index> <scale> <x> <y> <angle>`: replaces a dead slot outside the visible circle and acknowledges `READY`.
- `m <outward:0|1> <speed_multiplier>`: controls radial escape and speed independently.
- `v <x> <y> <escape:0|1> <speed_multiplier>`: selects a screen-space trajectory, with +X right and +Y down. Components are finite numbers in [-1, 1], with a nonzero vector. Changed vectors update headings; speed-only changes preserve them. Switching back to radial mode recomputes radial headings.
- `o`, `u`, `i`, `b`: outward boosted, outward normal, inward normal, and inward boosted steering. Movement commands acknowledge `READY`.

Python serializes commands and frame reads with the worker I/O lock; births and steering share the arena birth lock. The arena starts with inactive slots and introduces organisms one at a time. Initial and replacement births share random intervals of 200–1000 milliseconds by default (1–5 births per second). A slot with mass at or below 0.001 for five consecutive frames is queued for replacement unless escape is active. Disconnects cancel pending births and terminate the subprocess.

`GET /preset` returns 50 hexapods in a 1024×1024 circular arena at 60 FPS. `GET /` serves the browser viewer; `/ws` accepts the start configuration, movement commands, `next`, and `stop`. Start configurations accept only `simulation: "hexapod"` and `boundary: "circle"`. Each entry in `organisms` contains `scale`, `x`, and `y`; old type IDs, velocities, and exclusion lists are rejected. The list contains 1–100 hexapods. `population_updates: true` enables live population reports before JPEG frames. Optional `birth_rate_min` and `birth_rate_max` start fields set the random birth-rate bounds in organisms per second, defaulting to `1.0` and `5.0`. Both must be positive finite numbers, with minimum no greater than maximum; equal bounds give a fixed interval. Birth delays are sampled uniformly between `1 / birth_rate_max` and `1 / birth_rate_min` seconds and apply to both initial and replacement births.

Python flips bottom-up RGB output and encodes JPEGs. For `pixel_size: 1` and output smaller than the world, CUDA downsamples first; pixelated or enlarged output is resized on the CPU. A 1024×1024 world sent as 480×480 transfers 691,200 raw RGB bytes per frame. See [sensor mapping](../operation/motion-control.md).

Rebuild the native executable and restart the server and clients together after this protocol change. Existing JSON configurations must remove `type`, `velocity`, and `excluded_types`.

[Wiki overview](../documentation/overview.md)
