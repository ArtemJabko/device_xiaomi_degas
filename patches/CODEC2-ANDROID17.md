# MTK Codec2 crashes on Android 17

Device: degas, using OS3.0.306.0.WNEEUXM blobs. Investigated on November 14, 2026. The guarded fixes live in `tools/codec2_compat.py` and are applied by `extract-files.py`. Input and output SHA256 hashes are pinned; other blob versions are rejected.

## ComponentStore heap corruption

The stock `android.hardware.media.c2@1.2-mediatek-64b` allocates `0x108` (264) bytes in `main` at `0x21c0`. The stock `libcodec2_hidl@1.2.so` constructor places its `RefBase` subobject at offset `0xf8`.

Android 17's built library places that subobject at `0x110`, requiring a complete object size of `0x120` (288) bytes. Calling the new constructor with the old allocation size corrupts the heap. The tombstone shows a SIGSEGV in `RefBase::incStrong+24`, called from `main+404` immediately after construction. The virtual `RefBase` offset is obtained from the vtable, so it does not need to be patched manually.

The fix changes one instruction: `mov w0, #0x108` to `mov w0, #0x120`. Interfaces, dependencies and the remaining instructions are preserved.

## First secure decoder request without ION

In `libcodec2_mtk_vdec.so`, `MemoryDevice(bool)` starts with a shared backend enum of zero. This kernel has DMA-BUF heaps and no `/dev/ion`. The first ordinary request selects DMA-BUF (enum 3), but the first secure request skips detection. A zero enum causes `[MemoryDevice] MemoryDevice type unknown` and an `abort()` at `0xd2070`; this is a separate confirmed crash.

At `0xd1f94`, `tbnz w20, #0, existing_backend` is replaced with `cbnz w0, existing_backend`. The condition now uses the result of `BufferAllocator::CheckIonSupport()`. Without ION, the first request of either type initializes the existing DMA-BUF backend. With ION, selection of ordinary or secure ION still follows the `secure` argument.

Secure playback and DRM behavior have not been fully tested.

## Validation

Both files were first tested through tmpfs bind mounts without `nosuid`, with SELinux enforcing. Six consecutive cold starts of the C2 HAL, media and cameraserver successfully enumerated codecs. The C2 PID remained stable and neither `Fatal signal` nor `MemoryDevice type unknown` appeared. The fixes were subsequently included in the flashed images and checked after installation. These results establish initialization and codec enumeration; they do not establish complete encode/decode/DRM functionality.

An earlier executable bind mount from `/data` failed because of `nosuid_transition`, so that attempt was not evidence that the patch worked. Runtime logs and diagnostic captures are kept in the local development workspace, outside this repository.

The runtime evidence above comes from the prior PixelOS 17 port. This LineageOS 24.0 branch preserves the guarded edits; Codec2 layout, initialization and playback still require verification in a full LineageOS build.
