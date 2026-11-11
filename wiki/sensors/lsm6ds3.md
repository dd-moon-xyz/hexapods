---
type: Documentation
title: LSM6DS3 accelerometer and gyroscope
---

# LSM6DS3 accelerometer and gyroscope

The PIM745 motion sensor uses I²C address `0x6a`. See [motion control](../operation/motion-control.md) for client thresholds and polling.

## Motion sensor axes


Hold the stick with the components facing you and the labels upright: **TEMP/PRES/HUMID on the left, LUX/PROX on the right**.

```text
                         -X
                          ^
                          |
     .---------------------------------------------------------.
     |       TEMP         |                    LUX             |
     | [Qw/ST]  O  PRES    |  GYRO / ACCEL       PROX  O [Qw/ST] |
     |             HUMID  |  +---------+                        |
-Y <-------------------------| LSM6DS3 |--------------------------> +Y
     |             [BME]     +---------+       [LTR559]         |
     '---------------------------|-----------------------------'
                                 |
                                 v
                                +X

                 +Z = out of the component side, toward you
                 -Z = through the board, away from you

     O = mounting hole                 [Qw/ST] = cable connector
```

The board-axis mapping is inferred by matching the chip orientation and pin-one marking in [Pimoroni's component-side photo](https://cdn.shopify.com/s/files/1/0389/1025/files/multi-sensor-stick-1_e19782ce-e0c0-47df-99a9-3bccf86e5fd5.jpg?v=1728035318) to [ST's LSM6DS3TR-C datasheet, Figure 1, page 18](https://www.st.com/resource/en/datasheet/lsm6ds3tr-c.pdf). It is not a board-axis diagram published by Pimoroni.

The accelerometer measures acceleration along these axes. The gyroscope measures rotation around them:

| Reading | Physical movement |
|---|---|
| `gx` | Rock the stick so its left and right connector ends move up/down oppositely. |
| `gy` | Roll the stick around its length, like twisting a screwdriver. |
| `gz` | Spin the stick flat on a table, like a clock hand. |

Positive rotation follows the right-hand rule: point your right thumb along the positive axis; your curled fingers show positive rotation. For positive `gz`, that is counterclockwise when looking at the component side.

[Section index](index.md) · [Wiki index](../documentation/overview.md)
