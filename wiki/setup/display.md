---
type: Documentation
title: Display
---

# Display

The Raspberry Pi uses an 800×800 HDMI display and a Wayland desktop. The client uses the shared Python/Pygame viewer. The desktop must run as `bastian` for the fullscreen client. Enable desktop autologin with `sudo raspi-config` if the display should work after reboot without manual login.

Use the standard `vc4-kms-v3d` driver in `/boot/firmware/config.txt` with no DPI display overlay. HDMI should be the only enabled desktop output so fullscreen playback consistently opens there after reboot. The connected display is currently `HDMI-A-2` at 800×800.

Both Python clients use the shared [client core](../../client/core/README.md), with a high-DPI SDL2 window and nearest-pixel texture sampling. The local client sizes the window to frame pixels; the Pi fits and letterboxes to its display. JPEG encoding remains in the Rust server.

[Section index](index.md) · [Wiki index](../documentation/overview.md)
