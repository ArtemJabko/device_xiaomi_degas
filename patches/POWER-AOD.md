# AOD, UDFPS and screen-off power — Android 17 / degas

Code review and patches, 2026-11-14. No battery-life or suspend-residency measurements were performed for this change. CPU/GPU frequency caps, thermal protection and modem behavior are unchanged.

## Why 120 Hz appeared in idle AOD

Platform patch 0001 held the UDFPS refresh vote for the complete overlay session. The keyguard overlay can remain visible during AOD, so the vote outlived scanning. Local HBM requires 120 Hz on this panel; changing modes while HBM is lit can cause a full-screen flash. Setting the resource to zero is insufficient: the original per-touch path sends `onPointerDown` before its refresh request and can select the maximum 144 Hz.

Patch 0005 releases the vote during idle doze. Interactive overlays retain the fixed rate. A dozing scan reacquires the vote and waits for DisplayManager's actual physical mode report at 120 Hz, with display state ON or DOZE, plus 20 ms settlement, before sending `onPointerDown`. The ordinary provider's enable callback only acknowledges the request and cannot establish physical readiness.

Finger-up, acquisition and overlay teardown cancel deferred illumination. A separate dispatched-pointer flag prevents sending pointer-up for a scan that never started. A pending mode switch times out after 800 ms without lighting the sensor. Vote release is delayed 200 ms to outlast the vendor helper's 150 ms HBM-off reassert; another scan or return to interactive mode cancels release. Generations also reject callbacks delivered after cancellation.

A refresh-rate counter reports the Android display mode. It does not measure the panel controller's internal AOD scan frequency; releasing the vote does not guarantee that this counter reads 1 Hz or a specific lower number.

## Other power changes

- XiaomiParts AodService selects 5 nit indoors, 60 nit at >=1500 lux, returning to low mode at <=1000 lux. The bright path preserves LBM -> 50 ms -> HBM to work around the driver's cached brightness value. A non-wakeup, on-change light sensor is registered only during DOZE/DOZE_SUSPEND; it uses no wakelock, periodic timer or wakeup alarm. Brightness changes debounce for 1 second and stale writes are cancelled on display transitions/destruction.
- SystemUI overlay enables DOZE_SUSPEND. This permits the existing doze state machine to suspend display composition between AOD updates. HWC/kernel advertise doze capability; actual panel behavior and fingerprint resume still need functional verification.
- Platform patch 0004 prevents hardware-vsync resync while OFF/DOZE_SUSPEND and extends Android 17's existing synchronized modeset rejection to suspended displays. DOZE remains refreshable.
- Framework overlay disables the ambient wallpaper.
- `DISPLAY_INACTIVE` and `DEVICE_IDLE` end INTERACTION, LAUNCH and EXPENSIVE_RENDERING hints, releasing CPU/GPU/memory/uclamp boosts when the display becomes inactive or device idle starts. The source libperfmgr parser accepts EndHint-only hints and its NodeLooperThread accepts an empty node-action request. Values/frequency tables are preserved.

The IMS healer's 15-second Handler is an uptime timer, not an alarm that wakes a suspended AP. The observed CPU policies restore 480/400/400 MHz minimums with schedutil; the observed GPU minimum is 265 MHz. These snapshots do not prove good suspend or battery life, but do not justify arbitrary frequency caps. Known Codec2 crash/retry loops were fixed separately.

## Verification

`python3 device/xiaomi/degas/tools/power-tests/run.py` extracts and compiles the exact helper from patch 0005 and checks eight deterministic timing/cancellation scenarios. `test_apply_patches.py` checks clean, partially applied and fully applied overlapping patches, new files, rejection of conflicts and preservation of the real Git index/worktree. The applier validates the whole series in a scratch index before changing platform files.

Historical PixelOS 17 validation: all five power/connectivity patches apply on the then-pinned Android 17 sources and pass a second, idempotent check. Targeted build: `m -j32 XiaomiParts DegasSystemUIOverlay DegasFrameworksOverlay SystemUI surfaceflinger`. The targeted build completed successfully in 09:04, exit 0. Local output hashes match the server, all APK ZIP CRCs pass, and SystemUI/XiaomiParts retain the original platform signing certificate. The compiled overlays contain DOZE_SUSPEND=true, ambient wallpaper=false, and UDFPS rate=120. Saved payload/source/evidence and complete hashes are in `out/connectivity-20261114/power-build/`; see workspace memory section 18. These power patches were subsequently installed on the device; the user confirmed AOD/Power operation. Battery consumption and panel suspend residency have not been measured.

## LineageOS 24.0 adaptation

The power patches in `lineage24/` were rebased and checked against the LineageOS revisions in `lineage24-source.lock.json`. The deterministic UDFPS helper and applier tests pass. The full LineageOS build, AOD transitions and fingerprint unlock have not yet been tested on the device. The build and runtime results above refer to the previous PixelOS 17 port.
