# Xiaomi 14T (degas) — Evolution X 17

Device tree for **Xiaomi 14T** targeting [Evolution X cnb / Android 17](https://github.com/Evolution-X/manifest/tree/cnb). Lunch target: `lineage_degas-cp2a-user`, build target: `m evolution`.

| Item | Specification |
| --- | --- |
| Device | Xiaomi 14T, codename `degas`, model `2406APNFAG` |
| SoC | MediaTek Dimensity 8300-Ultra / MT6897 |
| GPU | Mali-G615 MC6 |
| Display | 6.67-inch AMOLED, 1220 × 2712, up to 144 Hz |
| ROM target | Evolution X cnb, `lineage_degas` (GMS by default, `WITH_GMS := false` for vanilla) |
| Stock base | HyperOS **OS3.0.306.0.WNEEUXM**, EEA, Android 16 |
| Kernel | Prebuilt GKI 6.1.157 ([mt6897-degas lineage-24.0](https://github.com/mt6897-degas/android_device_xiaomi_degas-kernel/tree/lineage-24.0)) |

## Status

**Experimental.** Based on the [mt6897-degas lineage-24.0 adaptation](https://github.com/mt6897-degas/android_device_xiaomi_degas/tree/lineage-24.0) of the original degas tree by [Mikhail Mlhcnn (Advnirr)](https://github.com/Advnirr) / [Degas Developers](https://github.com/degas-developers). The same tree passed build/device checks on PixelOS 17; neither the LineageOS 24.0 adaptation nor this Evolution X port has been verified on hardware. Evolution X adds its own GMS/vendor layer on top, which is untested here.

## Vendor blobs

Not published. Generate `vendor/xiaomi/degas` from an **OS3.0.306.0.WNEEUXM** fastboot dump with:

```bash
device/xiaomi/degas/tools/extract-vendor.sh /path/to/stock/dump
```

The older OS3.0.4.0 blobs from `ArtemJabko/vendor_xiaomi_degas` only match the [`lineage-23.2`](https://github.com/ArtemJabko/device_xiaomi_degas/tree/lineage-23.2) tree, not this one.

## Dependencies

[`evolution.xml`](evolution.xml) pins the required LineageOS `lineage-24.0` platform revisions (hardware_mediatek, hardware_xiaomi, sepolicy_vndr) and the matching kernel prebuilts. Place it in `.repo/local_manifests/` before `repo sync`.

## Credits and license

Original tree: [Mikhail Mlhcnn (Advnirr)](https://github.com/Advnirr) / [Degas Developers](https://github.com/degas-developers), [mt6897-degas](https://github.com/mt6897-degas). ROM bases: [Evolution X](https://github.com/Evolution-X), [LineageOS](https://github.com/LineageOS), [PixelOS](https://github.com/PixelOS-AOSP). Original copyright, attribution and Git history are retained — see [LICENSE](LICENSE) and [NOTICE](NOTICE). Unofficial, no support implied.
