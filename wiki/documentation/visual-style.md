---
type: Documentation
title: Visual style
---

# Visual style

Dark mode. ASCII cyberpunk. Extreme minimalism.

This is the shared style for wiki diagrams and future visual documentation. The Markdown viewer controls page colours; SVG diagrams carry their own dark background so they look consistent in any viewer.

## Palette

| Role | Colour |
|---|---|
| Background | `#090d12` |
| Primary text | `#e6edf3` |
| Secondary text / ground wire | `#93a4b5` |
| Borders | `#344150` |
| Unused pins | `#18212b`, outline `#526171` |
| Power / active LED connection | `#ff5370` |
| SDA | `#50fa9b` |
| SCL | `#e6edf3`, outline `#8495a7` |
| Resistor / caution text | `#f3c969` |

Colours communicate signals. Keep the same signal colours across diagrams and label each connection so colour is never the only guide.

## Diagram rules

- Author editable SVG directly. Use a `960 × 850` viewBox for GPIO wiring diagrams.
- Use `DejaVu Sans Mono`, `Liberation Mono`, then `monospace`.
- Use ASCII labels: `[ TITLE ]`, `->`, `/`, `+`, `-`, and `470 ohm`.
- Use flat fills, square corners, straight wire routes, and generous empty space. No gradients, shadows, glow, textures, or decorative graphics.
- Keep text short. Show components, connections, pin numbers, and essential notes only.
- Draw all 40 header pins: odd numbers left, even numbers right, pin 1 at the top left. State that this is a top view with pins facing the viewer.
- Highlight connected pins; keep unused pins muted. Preserve physical positions and electrical accuracy when restyling.
- Distinguish physical header numbers from software GPIO names, for example `Pin 12 / GPIO18`.
- Include component polarity, required resistor values, pin voltages (including GPIO HIGH/LOW levels), and a brief power-off note. Label LED forward voltage as model dependent unless its specification is known.
- Give each SVG a descriptive `title` and `desc`, and supply meaningful Markdown image alt text.

ASCII is the visual language for labels and structure; precise SVG geometry keeps wiring readable. Circuit symbols may use curves where needed to identify a component.

## Reference diagrams

- [Sensor wiring](../images/multisensor-raspberry-pi.svg)
- [Indicator LED wiring](../images/indicator-led.svg)

When adding or changing diagrams, follow these references and this palette. Check that labels fit, wires reach the correct pins, and SVG XML and local links are valid.

[Section index](index.md) · [Wiki index](overview.md)
