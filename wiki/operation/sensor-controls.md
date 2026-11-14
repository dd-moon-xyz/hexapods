---
type: Documentation
title: Sensor controls
---

# Sensor controls

During live hexapod streaming, the AI Camera acts as a person proximity sensor and the accelerometer/gyroscope remains active. The physical LTR559 proximity sensor is disabled in the client: it is not opened, calibrated, or polled. The [indicator LED](../wiring/indicator-led.md) tracks the living hexapod population, from off at zero to 25% brightness at the configured count. Replay does not open these inputs.

The camera uses pretrained SSD MobileNetV2 FPN Lite on the IMX500. Only person detections with confidence at least 0.60 count. The tallest person box determines proximity, including when multiple people are present. Escape starts after three detections with box height at least 50% of the image; it clears after three detections below 40%. This estimates closeness, not metres. See [AI Camera setup and tuning](../sensors/imx500.md#person-proximity-control).

Tune the trigger with `PERSON_PROXIMITY=0.35` in `.env`: lower values react farther away; higher values require a larger person in the image. Valid values are greater than 0 and less than 1; the default is `0.5`. Run `make raspi-client-restart` to apply changes under PM2.

Camera proximity selects radial `outward` escape. Camera speed increases from ×1 at the proximity threshold to ×2 when the person box fills the image height. Its existing confirmation and release thresholds are unchanged. Camera proximity has priority over motion, and motion cannot alter its escape speed. With both inputs clear, movement is `inward` at ×1. The camera runs separately so loading or waiting for camera frames does not block motion polling. Camera failure or stale inference stops the client with an error so PM2 can retry; the LTR559 is not used as a fallback.

A qualifying X/Y acceleration gesture selects a fixed mapped direction for hexapod movement. Direction and speed contribution stay fixed until 250 ms of fresh quiet readings release movement. The next gesture selects a new direction. Camera detection continues throughout; its radial escape overrides motion while detection continues independently.

Camera-only escape sends `{"action":"movement","direction":"outward","speed_multiplier":1.0}` with speed adjusted to proximity strength. Motion perturbations send the mapped screen vector with `direction: "vector"` and `escape: true`, suppressing births and killing hexapods when their centers reach the visible circle boundary. Normal reflections and replacement births resume when both inputs clear. Speeds and vector components are rounded to 0.01 and sent only when changed. The server must support the structured movement API and native `m` and `v` commands. The client preserves the server preset and simulation settings.

See [motion control](motion-control.md) for motion thresholds and polling.

[Section index](index.md) · [Wiki index](../documentation/overview.md)
