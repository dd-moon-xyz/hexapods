---
type: Documentation
title: Technical Overview
---

# Technical Overview

The Rust server runs the six-arm hexapod simulation using Axum, Tokio, and libjpeg-turbo. Each WebSocket connection owns an independent CUDA process. It serves fresh frames on demand without an FPS ceiling on port 9877. The Rust desktop viewer provides keyboard controls; the separate Raspberry Pi hardware client sends camera proximity and motion commands.

### CUDA

The [native worker](../../server/native/source/lenia/stream_hexapod.cu) updates six-arm gait, body density, contact injury, fluid trails, palettes, and image composition on the GPU. Each walker has its own size, palette, heading, health, feet, and fluid field. At every birth it receives a uniformly random integer interaction allowance from the inclusive `interaction_count_min`–`interaction_count_max` start parameters (defaults: 1–10). Both bounds must be positive integers and the minimum must not exceed the maximum. Each new body contact with a peer consumes one interaction; continuous contact counts once, and separation permits another interaction with that peer. Simultaneous contacts with different peers count separately. Contact injury and irreversible fading begin on the interaction that exhausts the allowance. Straight trajectories reflect only at the hidden outer limit, after the whole sprite leaves the visible circle. Escape kills walkers at the visible edge; ordinary inward mode enables replacement births outside the circle. Dead walkers stay dead until replaced.

The native executable is `server/native/build/lenia`; sources live in `server/native/source/lenia/`. Both Rust clients import `client_core/`, which owns the SDL3 renderer, libjpeg-turbo decoder, WebSocket stream, configuration loading, recording, and replay. `local_client/` owns only desktop startup and keyboard controls. Its network thread requests frames ahead through a bounded two-frame queue, and JPEG decoding writes directly into a reusable SDL streaming texture. WebSocket buffers move to display and recording without byte copies. Rendering skips alpha blending and redundant clears. The Raspberry Pi hardware client in `raspi_client/` imports `client_core` directly, adding camera proximity, I²C motion, and PWM population indication. Capture and replay also use the shared Rust library.

Startup input is `size fps dt space_speed_multiplier count interaction_count_min interaction_count_max`, followed by `count` lines of `scale x y`. There is no numeric organism type or catalog-derived ID. The worker acknowledges successful startup with `READY`.

- `n`: emits `count` float32 masses, then packed RGB image bytes.
- `s <output_size>`: changes output dimensions, acknowledges `READY`. Downsampling uses CUDA box filters before readback.
- `r <index> <scale> <x> <y> <angle>`: replaces a dead slot outside the visible circle and acknowledges `READY`.
- `m <outward:0|1> <speed_multiplier>`: controls radial escape and speed independently.
- `v <x> <y> <escape:0|1> <speed_multiplier>`: selects a screen-space trajectory, with +X right and +Y down. Components are finite numbers in [-1, 1], with a nonzero vector. Changed vectors update headings; speed-only changes preserve them. Switching back to radial mode recomputes radial headings.
- `o`, `u`, `i`, `b`: outward boosted, outward normal, inward normal, and inward boosted steering. Movement commands acknowledge `READY`.

Rust serializes commands and frame reads with the worker I/O lock; births and steering share the arena birth lock. Slots start inactive. Birth delays are 200–1000 milliseconds by default. A slot empty for five consecutive frames is queued for replacement unless escape is active. Disconnects cancel pending births and terminate the subprocess.

The positive `fps` field is recording metadata with no delivery limit; the start status includes `fps_limit: null`. The native worker receives a reference value of 60 for injury integration, which never paces rendering. Simulation advances by `dt` per requested frame.

`GET /preset` returns 50 hexapods in a 1024×1024 circular arena with recording metadata of 60 FPS. `GET /` serves the browser viewer; `/ws` accepts the start configuration, movement commands, `next`, and `stop`. Start configurations accept only `simulation: "hexapod"` and `boundary: "circle"`. Each entry in `organisms` contains `scale`, `x`, and `y`; old type IDs, velocities, and exclusion lists are rejected. The list contains 1–100 hexapods. `population_updates: true` enables live population reports before JPEG frames. Optional `birth_rate_min` and `birth_rate_max` start fields set the random birth-rate bounds in organisms per second, defaulting to `1.0` and `5.0`. Both must be positive finite numbers, with minimum no greater than maximum; equal bounds give a fixed interval. Birth delays are sampled uniformly between `1 / birth_rate_max` and `1 / birth_rate_min` seconds and apply to both initial and replacement births.

Rust flips bottom-up RGB output and encodes JPEGs. For `pixel_size: 1` and output smaller than the world, CUDA downsamples first; other resizing runs on the CPU. See [sensor mapping](../operation/motion-control.md).

Rebuild the native executable and restart the server and clients together after this protocol change. Existing JSON configurations must remove `type`, `velocity`, and `excluded_types`.

[Wiki overview](../documentation/overview.md)
