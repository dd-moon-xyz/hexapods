---
type: Documentation
title: Technical Overview
---

# Technical Overview

The Rust server runs the six-arm hexapod simulation using Axum, Tokio, and libjpeg-turbo. Each WebSocket connection owns an independent CUDA process. It serves fresh frames on demand without an FPS ceiling on port 9877. The Python desktop viewer provides keyboard controls; the separate Raspberry Pi hardware client sends camera proximity and motion commands.

### CUDA

The [native worker](../../server/native/source/hexapods/stream_hexapod.cu) updates six-arm gait, body density, contact injury, fluid trails, palettes, and image composition on the GPU. Each walker has its own size, palette, heading, health, feet, and fluid field. At every birth it receives a uniformly random integer interaction allowance from the inclusive `interaction_count_min`–`interaction_count_max` start parameters (defaults: 1–10). Both bounds must be positive integers and the minimum must not exceed the maximum. Each new body contact with a peer consumes one interaction; continuous contact counts once, and separation permits another interaction with that peer. Simultaneous contacts with different peers count separately. Contact injury and irreversible fading begin on the interaction that exhausts the allowance. Straight trajectories reflect only at the hidden outer limit, after the whole sprite leaves the visible circle. Escape kills walkers at the visible edge; ordinary inward mode enables replacement births outside the circle. Dead walkers stay dead until replaced.

The native executable is `server/native/build/hexapods`; sources live in `server/native/source/hexapods/`. Both Python clients import `client/core/`, which owns the SDL2/Pygame renderer, JPEG decoding, WebSocket stream, configuration loading, recording, capture, and replay. The stream keeps two requests in flight; decoded frames update a reusable nearest-pixel texture. `client/local/` supplies the desktop entry point. `client/raspi/` adds Picamera2 camera proximity, I²C motion, PWM population indication, and `.env` settings. Its camera helper uses system Python for libcamera compatibility.

Startup input is `size fps dt space_speed_multiplier count interaction_count_min interaction_count_max`, followed by `count` lines of `scale x y`. There is no numeric organism type or catalog-derived ID. The worker acknowledges successful startup with `READY`.

- `n`: emits `count` float32 masses, then packed RGB image bytes.
- `s <output_size>`: changes output dimensions, acknowledges `READY`. Downsampling uses CUDA box filters before readback.
- `r <index> <scale> <x> <y> <angle>`: replaces a dead slot outside the visible circle and acknowledges `READY`.
- `m <outward:0|1> <speed_multiplier>`: controls radial escape and speed independently.
- `v <x> <y> <escape:0|1> <speed_multiplier>`: selects a screen-space trajectory, with +X right and +Y down. Components are finite numbers in [-1, 1], with a nonzero vector. Changed vectors update headings; speed-only changes preserve them. Switching back to radial mode recomputes radial headings.
- `o`, `u`, `i`, `b`: outward boosted, outward normal, inward normal, and inward boosted steering. Movement commands acknowledge `READY`.

Rust serializes commands and frame reads with the worker I/O lock; births and steering share the arena birth lock. Slots start inactive. Birth delays are 200–1000 milliseconds by default. Every initial and replacement birth samples a uniform floating-point scale from the inclusive `scale_min`–`scale_max` start parameters (defaults: 1.0–1.1). Bounds must be finite ordered numbers from 1 through 10; equal bounds give a fixed scale. This multiplier applies to the native randomized base size, subject to its world-size limit. A slot empty for five consecutive frames is queued for replacement unless escape is active. Disconnects cancel pending births and terminate the subprocess.

The positive `fps` field is recording metadata with no delivery limit; the start status includes `fps_limit: null`. The native worker receives a reference value of 60 for injury integration, which never paces rendering. Simulation advances by `dt` per requested frame. The optional `preview: true` start field requires exactly one organism and selects `--stream-hexapod-preview`: one large living walker enters from outside the top-left corner, travels diagonally across the full square canvas, and leaves beyond the bottom-right corner. Preview skips circular masking, boundary reflection, and replacement births. The [preview recorder](python-experiments.md) captures one complete crossing and loops it locally.

`GET /preset` returns 50 hexapods in a 1024×1024 circular arena with recording metadata of 60 FPS. `GET /` serves the browser viewer; `/ws` accepts the start configuration, movement commands, `next`, and `stop`. Start configurations accept only `simulation: "hexapod"` and `boundary: "circle"`. Each entry in `organisms` contains `scale`, `x`, and `y`; old type IDs, velocities, and exclusion lists are rejected. The list contains 1–100 hexapods. `population_updates: true` enables live population reports before JPEG frames. Optional `birth_rate_min` and `birth_rate_max` start fields set the random birth-rate bounds in organisms per second, defaulting to `1.0` and `5.0`. Both must be positive finite numbers, with minimum no greater than maximum; equal bounds give a fixed interval. Birth delays are sampled uniformly between `1 / birth_rate_max` and `1 / birth_rate_min` seconds and apply to both initial and replacement births.

Rust flips bottom-up RGB output and encodes JPEGs on blocking threads. Each session permits up to two requested frames in progress, allowing CUDA computation to overlap JPEG encoding of the previous frame. Responses remain in request order, and no simulation frames are computed without a client request. For `pixel_size: 1` and output smaller than the world, CUDA downsamples first; other resizing runs on the CPU. See [sensor mapping](../operation/motion-control.md).

Rebuild the native executable and restart the server and clients together after this protocol change. Existing JSON configurations must remove `type`, `velocity`, and `excluded_types`.

[Wiki overview](../documentation/overview.md)
