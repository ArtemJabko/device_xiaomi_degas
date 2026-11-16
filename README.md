# Xiaomi 14T (degas) — LineageOS 24.0

Device tree for **Xiaomi 14T**, targeting [LineageOS 24.0 / Android 17](https://github.com/LineageOS/android/tree/lineage-24.0). Use the [`lineage-24.0` branch](https://github.com/mt6897-degas/android_device_xiaomi_degas/tree/lineage-24.0).

The original **degas device tree was created by [Mikhail Mlhcnn (Advnirr)](https://github.com/Advnirr)** and published by [Degas Developers](https://github.com/degas-developers/android_device_xiaomi_degas). This branch preserves their `lineage-23.2` history at [`e7de73fe295ff07eb08927c9c8c61b536a2cd378`](https://github.com/degas-developers/android_device_xiaomi_degas/commit/e7de73fe295ff07eb08927c9c8c61b536a2cd378) and the subsequent PixelOS 17 hardware compatibility work.

| Item | Specification |
| --- | --- |
| Device | Xiaomi 14T, codename `degas`, model `2406APNFAG` |
| SoC | MediaTek Dimensity 8300-Ultra / MT6897 |
| GPU | Mali-G615 MC6 |
| Display | 6.67-inch AMOLED, 1220 × 2712, up to 144 Hz |
| ROM target | LineageOS 24.0, `lineage_degas`, `userdebug` |
| Stock base | HyperOS **OS3.0.306.0.WNEEUXM**, EEA, Android 16 |
| Vendor API / VINTF level | 34 / 8 |
| Super partition | 9,663,676,416 bytes |

## Status

This is a **source adaptation for LineageOS 24.0**. The product inherits `vendor/lineage/config/common_full_phone.mk` and does not force bundled GMS. The platform patches were rebased and checked against the upstream revisions recorded in [lineage24-source.lock.json](lineage24-source.lock.json). A complete LineageOS build and device boot have **not** been verified.

The branch retains fixes for boot, Wi-Fi, IMS receiver registration, camera database links, audio compatibility, both identified MTK Codec2 crashes and Power/AOD. These fixes previously passed the documented build/device checks on PixelOS 17; those results do not establish LineageOS runtime compatibility. Mobile-network/VoLTE coverage, DRM, camera modes and battery consumption still need testing. See [Codec2 notes](patches/CODEC2-ANDROID17.md) and [Power/AOD notes](patches/POWER-AOD.md).

Camera application selection is left to the ROM maintainer. This tree does not import MiCam or require a MiCam vendor tree.

## Evolution X (Android 17)

The `evolution-17` branch of this repository targets **Evolution X cnb** (Android 17), which is based on LineageOS 24.0 — the same base as this tree. Differences from the LineageOS build above:

- Product: `evolution_degas.mk` (`lunch evolution_degas-userdebug`), inheriting `vendor/evolution/config/common_full_phone.mk`. `lineage_degas.mk` is kept but not listed in `AndroidProducts.mk` because the Evolution X manifest does not sync `vendor/lineage`.
- Local manifest: [`evolution.xml`](evolution.xml) — same pinned LineageOS platform revisions plus the matching `mt6897-degas` kernel prebuilts (`lineage-24.0` branch).
- Vendor: generated the same way, from an **OS3.0.306.0.WNEEUXM** dump via `tools/extract-vendor.sh`. The older OS3.0.4.0 blobs published in `ArtemJabko/vendor_xiaomi_degas` only match the `lineage-23.2` tree and do **not** satisfy this tree's blob list.

```bash
repo init -u https://github.com/Evolution-X/manifest.git -b cnb --git-lfs
# clone this branch as device/xiaomi/degas, add evolution.xml to .repo/local_manifests/, repo sync
# extract vendor from the OS3.0.306 dump, apply patches, then:
source build/envsetup.sh
lunch evolution_degas-userdebug
mka bacon
```

## Build on Linux

Use a Linux x86_64 host with the dependencies described in the [LineageOS build guides](https://wiki.lineageos.org/devices/). There is no official degas build guide or official support implied by this repository.

### 1. Sync LineageOS and the device dependencies

```bash
repo init -u https://github.com/LineageOS/android.git -b lineage-24.0 --git-lfs

git clone -b lineage-24.0 https://github.com/mt6897-degas/android_device_xiaomi_degas.git device/xiaomi/degas
git clone -b lineage-24.0 https://github.com/mt6897-degas/android_device_xiaomi_degas-kernel.git device/xiaomi/degas-kernel

mkdir -p .repo/local_manifests
cp device/xiaomi/degas/degas.xml .repo/local_manifests/degas.xml
repo sync -c -j$(nproc)
```

The local manifest pins the required MediaTek, Xiaomi and vendor SELinux projects to verified `lineage-24.0` revisions. The main LineageOS manifest already includes Lineage compat/interfaces, Google pixel, extract-utils and Qualcomm vibrator; do not declare duplicate projects for those paths. The source lock records the revisions checked during this adaptation; platform branches may move, so recheck patch applicability after syncing.

### 2. Extract the matching proprietary vendor files

Use an existing full stock dump of **OS3.0.306.0.WNEEUXM**:

```bash
device/xiaomi/degas/tools/extract-vendor.sh /absolute/path/to/stock/dump
```

This generates `vendor/xiaomi/degas`, validates the input hashes and applies the guarded compatibility fixes. A separate published vendor repository is not required for this extraction workflow. Regenerate vendor for this tree; an existing vendor modified for a separate MiCam port can contain unavailable dependencies.

If a stock dump is not available, obtain the matching Xiaomi fastboot package. With `fsck.erofs` and `lz4` installed, use new output directories:

```bash
python3 device/xiaomi/degas/tools/prepare-stock.py \
    /absolute/path/to/degas_eea_global_images_OS3.0.306.0.WNEEUXM_16.0 \
    --work "$PWD/stock/degas" \
    --kernel "$PWD/stock/degas-kernel-verification"

device/xiaomi/degas/tools/extract-vendor.sh "$PWD/stock/degas/dump"
```

The separately extracted kernel is for comparison with the already cloned [matching kernel prebuilts](https://github.com/mt6897-degas/android_device_xiaomi_degas-kernel/tree/lineage-24.0). Keep the Image, DTB, DTBO and partition-specific modules together, including the different factory zram variants.

### 3. Apply the platform patches and build

```bash
python3 device/xiaomi/degas/tools/apply-patches.py --check
python3 device/xiaomi/degas/tools/apply-patches.py
source build/envsetup.sh
breakfast degas userdebug
m -j$(nproc) bacon
```

The product is **`lineage_degas`**. The six-patch series covers optical UDFPS refresh voting, suspended-display modesets, the MTK gen4m WPA3 path and Xiaomi IMS boot-jar packages. The applier checks the complete series before changing platform files and accepts already-applied patches. See [the patch guide](patches/README.md).

## Validation

From the Android checkout root, with matching kernel and generated vendor:

```bash
python3 device/xiaomi/degas/tools/validate-tree.py --stock "$PWD/stock/degas/dump" --vendor
python3 device/xiaomi/degas/verify-hand-edits.py
python3 device/xiaomi/degas/tools/apply-patches.py --check
python3 device/xiaomi/degas/tools/power-tests/run.py
python3 device/xiaomi/degas/tools/power-tests/test_apply_patches.py
```

Host checks cover XML/Python syntax, product configuration, 519 kernel hashes, stock blob/firmware hashes, module-load paths, generated vendor paths and guarded blob edits. Android/Soong, ELF linkage, VINTF and combined SELinux checks must also pass during a full build; device testing remains necessary.

Use the normal Android OTA tools for signed packages. If repacking payload operations separately, use XZ settings supported by recovery's `xz-embedded`; `CHECK_NONE` matches the previously working payload format. Python `lzma` defaults to CRC64, which the previous degas recovery rejected with `kDownloadOperationExecutionError` / error 28.

## Credits and license

- **[Mikhail Mlhcnn (Advnirr)](https://github.com/Advnirr)** — original Xiaomi 14T / degas device tree.
- **[Degas Developers](https://github.com/degas-developers)** — original LineageOS degas tree.
- **[mt6897-devs](https://github.com/mt6897-devs/device_xiaomi_duchamp)** and the original contributors — duchamp platform foundation.
- **[LineageOS](https://github.com/LineageOS)** and **[PixelOS](https://github.com/PixelOS-AOSP)** — ROM sources and prior Android 17 compatibility work.

Original copyright, attribution and Git history are retained. See [LICENSE](LICENSE) and [NOTICE](NOTICE). This is an unofficial adaptation maintained in the mt6897-degas repositories.

Charging and face enrollment integration fixes are documented in
[HYPERCHARGE-FACE.md](patches/HYPERCHARGE-FACE.md). They are checked against the
pinned stock inputs and matching Settings sources. The Type-C SELinux label
fix removes a confirmed blocker in Xiaomi PD authentication; charging wattage
and completed face enrollment remain unmeasured on hardware.
