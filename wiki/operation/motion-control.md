---
type: Documentation
title: Motion control
---

# Motion control

Enable I²C with `sudo raspi-config` and reboot. The desktop user needs read/write access to `/dev/i2c-1` (membership in the `i2c` group; log out and back in after changing groups). The motion sensor at `0x6a` uses 104 Hz readings polled every 50 ms. Keep the stick still during startup so its first acceleration reading supplies the initial reference.

Hexapod motion follows the first qualifying X/Y acceleration change. The direction and speed contribution stay fixed while motion continues, regardless of subsequent changes in direction or strength. There is no fixed duration or maximum timeout.

The measured quantity is `hypot(ax - previous_ax, ay - previous_ay)` in g between fresh polled samples. It is an acceleration-change gesture proxy, not a gravity-compensated linear acceleration or velocity estimate. Tilting changes gravity's projection and can trigger it; sample spacing affects the measured change. X/Y acceleration changes of at least `MOTION_THRESHOLD` (default 0.12 g) trigger movement. Z-only changes and gyroscope-only rotation do not trigger movement.

Movement ends after 250 ms of fresh quiet readings: X/Y acceleration change below threshold and X/Y rotation below 20 degrees/second. This quiet threshold represents zero movement despite sensor noise. Brief quiet gaps keep the original direction. The detector updates its reference throughout movement; once quiet, the next gesture selects a new direction. Stale readings cannot release the latched direction. Motion strength scales speed from ×1 at threshold to ×2 at four times the threshold and stays fixed until release.

Direction is normalized once from the triggering acceleration change. Vector components and speed are rounded to 0.01, unchanged commands are suppressed, and the latest queued command replaces older pending commands before transmission.

`MOTION_SCREEN_X=y` and `MOTION_SCREEN_Y=x` map sensor +Y to screen right and sensor +X to screen down, matching the component-side axis diagram. Each setting accepts `x`, `-x`, `y`, or `-y`; the two settings must select different sensor axes. Prefix `-` to invert a mounted axis. Movement follows this mapped vector. With the defaults, a positive sensor-Y gesture sends hexapods right; a positive sensor-X gesture sends them down. Verify the mapping with the mounted stick and adjust `.env` if necessary, then run `make raspi-client-restart`.

The client sends, for example:

```json
{"action":"movement","direction":"vector","vector":{"x":0.8,"y":0.6},"escape":true,"speed_multiplier":1.5}
```

The vector is the desired travel direction in screen coordinates: +X right, +Y down. The server does not reverse it again. `escape: true` suppresses births and kills hexapods when their centers reach the visible circle boundary. Normal reflections and replacement births resume when both sensors clear. Once motion is quiet, inward movement resumes unless camera proximity is active. Non-hexapod circular simulations retain radial motion commands, controlled by the same motion detector.

Camera proximity retains radial outward escape priority and its existing proximity-based speed, confirmation, and release thresholds. Motion detection continues while the camera overrides direction. If proximity clears while motion is still active, the original latched direction resumes.

See [LSM6DS3 axes](../sensors/lsm6ds3.md) for physical directions and [sensor controls](sensor-controls.md) for how motion and proximity combine.

[Section index](index.md) · [Wiki index](../documentation/overview.md)
