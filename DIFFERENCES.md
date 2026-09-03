# degas (Xiaomi 14T) vs duchamp (POCO X6 Pro 5G) — porting notes

Both devices are MediaTek MT6897 (Dimensity 8300 / 8300-Ultra), so the platform
(kernel ABI, HAL stack, sepolicy base, init scripts) is shared. This file lists
every hardware/board difference found while porting, and the source of truth
used for each degas-specific value.

Sources used for degas facts:
- `Jiovanni-dump/xiaomi_degas_dump` — full HyperOS 2 dump, OS2.0.202.0.VNEMIXM
  (Android 15 system / Android 14 vendor, fingerprint
  `Xiaomi/degas_global/degas:14/UP1A.231005.007/OS2.0.202.0.VNEMIXM`)
- `Advnirr/twrp_device_xiaomi_degas` — TWRP tree with working board config
- Xiaomi / GSMArena spec pages

## Identity

| | duchamp | degas |
|---|---|---|
| Market name | POCO X6 Pro 5G / Redmi K70E | Xiaomi 14T |
| Model (global) | 2311DRK48G | 2406APNFAG |
| ro.product.board | duchamp | degas |
| ro.product.mod_device | duchamp_global | degas_global |
| Stock fingerprint | POCO/duchamp_global/duchamp:16/... | Xiaomi/degas_global/degas:14/UP1A.231005.007/... |
| Shipping API | 34 | 34 (`ro.board.first_api_level=34`) |

## Display

| | duchamp | degas |
|---|---|---|
| Panel | 6.67" AMOLED 1220x2712 | 6.67" AMOLED 1220x2712 |
| Refresh rate | 120 Hz | **144 Hz** → `config_defaultPeakRefreshRate=144` |
| Peak brightness | 1800 nits | 4000 nits (HBM; driver-level, no overlay change) |
| Density | 480 dpi | 480 dpi (same, `ro.sf.lcd_density=480`) |
| MediaTek branch | alps-mp-u0.mp1.tc8sp1 | alps-mp-u0.mp1.tc8sp3 |

## Fingerprint (UDFPS)

Both use under-display optical Goodix sensors driven through the same Xiaomi
stack (`/dev/mi_display/disp_feature` local-HBM ioctl + `/dev/xiaomi-touch`).

- degas stock props: `persist.vendor.sys.fp.fod.location.X_Y=505,2339`
  (top-left corner), `persist.vendor.sys.fp.fod.size.width_height=210,210`,
  `persist.vendor.sys.fp.expolevel=0x88` (same value as duchamp).
- Converted to center|radius for `hardware/xiaomi` FingerprintHalProperties:
  `persist.vendor.fingerprint.sensor_location=610|2444|105`
  (duchamp: `610|2442|114`).
- Goodix firmware on degas lives in `odm/firmware/` (duchamp: `vendor/firmware/`),
  files are codename-suffixed: `goodix_firmware_degas.bin`,
  `goodix_cfg_group_degas.bin`, `goodix_cfg_group_degas_nowater.bin`.
- `vendor.xiaomi.hardware.displayfeature_aidl` (V2 NDK) exists in both dumps —
  the in-tree `interfaces/displayfeature_aidl` applies unchanged.

## Cameras

| Module | duchamp | degas |
|---|---|---|
| Main | 64 MP OmniVision OV64B (`ov64b40wide`) | 50 MP Sony IMX906 (`imx906wide`) |
| Telephoto | — | 50 MP Samsung S5KJN1 (`s5kjn1tele`) |
| Ultrawide | 8 MP OV08D10 (`ov08d10ultra`) | 12 MP OmniVision OV13B10 (`ov13b10ultra`) |
| Macro | 2 MP SC202PCS (`sc202pcsmacro`) | — |
| Front | 16 MP OV16A1Q / GC16B3 | 32 MP Samsung S5KKD1 (`s5kkd1front`) |

`proprietary-files.txt` camera tuning/IdxMgr entries were replaced with the
degas modules (names confirmed in the dump: `vendor/lib64/mt6897/degas*_mipi_raw_*.so`).

## Partitions

| | duchamp | degas |
|---|---|---|
| super | 9663676416 | **9126805504** |
| dynamic group size | super - 4 MiB | 9122611200 (matches super - 4 MiB) |
| dynamic partitions | odm odm_dlkm product system system_dlkm system_ext vendor vendor_dlkm | same set confirmed by dump (mi_ext exists but is intentionally not built/flashed, same as duchamp) |
| boot / vendor_boot | 64 MiB / 64 MiB | 64 MiB / 64 MiB (TWRP tree) |
| init_boot / dtbo | 8 MiB / 8 MiB | assumed same — TODO verify via `fastboot getvar all` |
| dedicated recovery | none (ramdisk in vendor_boot) | none (no recovery.img in dump; TWRP also uses vendor_boot) |
| userdata FBE | fstab: `:aes-256-hctr2:inlinecrypt_optimized` | stock: `aes-256-xts:aes-256-cts:v2+inlinecrypt_optimized` (`ro.crypto.volume.filenames_mode=aes-256-cts`) → fstab updated |
| userdata | same UFS node `112b0000.ufshci` | same |

## Radio / modem

- Same MT6897 modem stack and prop set (DSDS, `ro.vendor.mtk_ril_mode=c6m_1rild`,
  mtkradioex AIDL v2). No degas-specific deltas found in the dump props.
- Modem firmware (`modem.img`) must come from degas firmware — see
  `proprietary-firmware.txt` (TODO: re-pin hashes after extraction).

## Battery / charging

- duchamp: 5000 mAh, 67 W. degas: 5000 mAh, 67 W — identical class.
- degas-only odm props added from dump: `persist.vendor.battery.health*`,
  `persist.vendor.night.charge`, `persist.vendor.smartchg=342`,
  `persist.vendor.hightemp.notice`, `persist.vendor.region.charger=GL`,
  `persist.vendor.darkcal.hilimit/lolimit`.

## Misc hardware

- Touch firmware: `odm/firmware/focaltech_ts_fw_degas.bin` (codename-suffixed,
  odm partition) — path updated.
- Haptics: aw8697 firmware present in both (`vendor/firmware/aw8697*`).
- degas is IP68 (duchamp IP54) — no build impact.
- IR blaster, NFC (NXP), Wi-Fi 6E/7-class connsys — same MTK connsys2x stack.

## Known TODO / verify on hardware

1. `BOARD_INIT_BOOT_IMAGE_PARTITION_SIZE` / `BOARD_DTBOIMG_PARTITION_SIZE`
   assumed 8 MiB (duchamp values) — verify with `fastboot getvar all`.
2. Kernel: no public `device_xiaomi_degas-kernel` yet. Build from
   `android-kernels/xiaomi-bsp-degas-u-oss` (branch `bsp-degas-u-oss`) with the
   mt6897-devs module stack, or assemble prebuilts from stock
   boot/init_boot/vendor_boot/vendor_dlkm.
3. `vendor/xiaomi/degas`: must be generated with `./extract-files.py` against a
   degas dump; blob list is inherited from duchamp and marked TODO.
4. Radio config XMLs (`DegasCarrierConfigOverlay`) are inherited from duchamp —
   diff against degas stock `carrier_config` if MVNO issues appear.
5. Thermal (`thermal_info_config.json`) and `powerhint.json` are duchamp-tuned —
   validate skin-temp thresholds on degas (IP68 sealed body differs).
6. UDFPS icon position may need fine-tuning in SystemUI dimens after first boot
   (current values converted from stock props, see above).
