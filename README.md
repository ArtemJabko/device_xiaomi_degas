# Device tree for Xiaomi 14T (degas)

```
#
# SPDX-FileCopyrightText: The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#
```

The Xiaomi 14T (codename `degas`) is a smartphone from Xiaomi announced in September 2024.

## Device specifications

| Feature     | Specification                                        |
| :---------- | :--------------------------------------------------- |
| Chipset     | MediaTek Dimensity 8300-Ultra (MT6897)               |
| CPU         | Octa-core (1x3.35 GHz Cortex-A715 & 3x3.20 GHz Cortex-A715 & 4x2.20 GHz Cortex-A510) |
| GPU         | Mali-G615 MC6                                        |
| Memory      | 12/16 GB RAM (LPDDR5X)                               |
| Shipped OS  | Android 14, HyperOS (ro.board.first_api_level=34)    |
| Storage     | 256/512 GB / 1 TB UFS 4.0                            |
| Battery     | 5000 mAh, 67W wired                                  |
| Display     | 6.67" AMOLED, 1220 x 2712, 144 Hz, up to 4000 nits peak |
| Rear camera | 50 MP Sony IMX906 (wide) + 50 MP Samsung S5KJN1 (2x tele) + 12 MP OmniVision OV13B10 (ultrawide) |
| Front camera| 32 MP Samsung S5KKD1                                 |
| Fingerprint | Under-display optical (Goodix)                       |

## Status / known gaps

See `DIFFERENCES.md` for the full duchamp->degas porting notes and the list of
values that still need verification on real hardware.
