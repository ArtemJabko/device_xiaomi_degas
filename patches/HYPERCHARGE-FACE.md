# Degas charging and face enrollment compatibility

The stock input is OS3.0.306.0.WNEEUXM. These changes fix confirmed
integration problems. Charging power and completed enrollment still require
hardware verification; no new device measurements are claimed.

## Xiaomi PD authentication: missing Type-C SELinux label

For degas, `batterysecret::usbpd_dr_swap()` opens
`/sys/devices/platform/rt-pd-manager/typec/port0/data_role` with `O_RDWR`.
It reads the Type-C data role and requests `host` before sending Xiaomi VDMs;
the verification path subsequently restores `device`.
The packaged policy had no label for that node: it inherited `sysfs`, and
`vendor_batterysecret` was denied `open`, `read` and `write`. Parent directory
search already worked. This prevents the stock daemon from even attempting
the authenticated Xiaomi charger exchange on the normal sink-ready path.

After four failed role-swap attempts, `verify_pd_digest()` records failure and
writes zero to `pd_adapter/usbpd_verifed`. In the factory kernel,
`adapter_class::usbpd_verifed_store()` passes failure type 4 to
`mtk_pd_adapter::pd_get_cap()`, which sets USB property 2,
`pd_authentication`, to zero. Success type 5 refreshes source capabilities and
sets that property to one. The getter table and switch targets were checked
against the ELF symbols and relocations, not inferred from property names.

`mtk_charger_framework::do_algorithm()` tests that authentication flag when
choosing the charging path. Its unauthenticated fallback includes a 1.7 A
input-current ceiling for multiple source capabilities, a 1.5 A variant,
and a separate up-to-3 A rule below 6 V. These are conditional fallback
limits, not a universal 11 W cap. FFC additionally requires the adapter's
verified flag. `pd_cp_manager::pdm_psy_change()` waits for `pd_verify_done`;
that completion flag is set even after failed authentication. Generic PPS
can still run when suitable APDOs exist. Do not claim that failed Xiaomi
authentication disables every charge-pump/PPS path.

The fix labels only `data_role` as `sysfs_usb_nonplat`, using the daemon's
existing access to that type. No new allow rule is needed:

```text
genfscon sysfs /devices/platform/rt-pd-manager/typec/port0/data_role u:object_r:sysfs_usb_nonplat:s0
```

The combined PixelOS policy was rebuilt with neverallow assertions enabled.
44 effective policy queries verify the exact path before and after the fix,
the unchanged authentication nodes and parent search, denied writes to
unrelated sysfs and by applications, and the retained face camera callback.
The same source label is included in both public device branches; a full
LineageOS build and its combined policy remain untested.
This removes a proven software blocker for Xiaomi authentication. It does
not establish the exact cause of a particular 11 W measurement or measured
67 W operation without a charger test.

Binary references in the factory inputs: `batterysecret` role open at `0x5df8`,
verification failure at `0x6ea8`, result write at `0x73b4`;
`adapter_class.ko` result dispatch at `0x57e0`/`0x5804`;
`mtk_pd_adapter.ko` authentication writes at `0x52d8`/`0x53a0`;
`mtk_charger_framework.ko` authentication branch at `0x1c850`, fallback
ceiling at `0x1d808`, FFC verified condition at `0x23458`.
Addresses refer to the corresponding analysis databases, not file offsets.

## Accelerated charging property consistency

Stock `batterysecret` initializes its acceleration feature to one, then clears
it in the `degas` device branch. `verify_pd_digest()` consequently forces
`persist.vendor.accelerate.charge=false`, overriding the existing init default.
Saved degas logs confirm both `accelerate_charge:0` and the false property.

`tools/hypercharge_compat.py` changes `sturh wzr, [x19, #0x31]` to
`sturb wzr, [x19, #0x31]`. Reverse authentication stays disabled for degas;
acceleration stays enabled. Battery/charger digest verification, Xiaomi VDM
negotiation, EEA detection, smart-sense and kernel limits are unchanged.
The fix rejects every unrecognized input hash and is idempotent. Run:

```sh
python3 device/xiaomi/degas/tools/test_hypercharge.py \
  /path/to/stock/vendor/bin/batterysecret
```

The init property also repairs the persistent false value from older builds.
This fixes the mismatch between the device's declared charging default and the
stock daemon. It is not a verified fix for the reported approximately 11 W limit:
the property is only logged by `verify_pd_digest()`, and a charging driver
consumer has not been established. Do not equate the property with charger power.

The shipped charging driver selects FFC and current limits itself, using battery
authentication, negotiated adapter capabilities, temperature and charge level.
Its 2 A charge-current cap is conditional on failed battery authentication;
saved logs show authentication succeeds. Those logs also show a 5 V / 1.5 A
adapter and a nearly full battery, so they cannot establish the reported charger
failure. No authentication result, current limit or thermal vote is forced.

## Face enrollment

The Xiaomi AIDL v3 HAL owns the front camera and accepts a preview native handle
in `enrollWithContext`. Its startup and trusted application load already succeed.
Both matching Android 17 Settings sources provide
`config_face_enroll_hal_owns_camera`, but default it to false. Degas previously
had no override: Settings opened a competing camera and passed a null preview.

The Settings overlay enables that option, so enrollment waits for a valid
Surface and passes it to the HAL. Its 640 x 480 preview is a supported front
camera PRIVATE/YUV output in the saved camera metadata. AIDL v3 already selects
`enrollWithContext`; no interface version spoofing or biometric-strength changes
are needed. No template, TEE, authentication-token or SELinux bypass is added.

The native camera client also needs camera callbacks in the reverse Binder
direction. `binder_call(hal_face_default, cameraserver)` only allowed reverse
transfer; it did not allow `cameraserver` to call the face client's listeners.
The stock Xiaomi domain had that access through `binderservicedomain`, whereas
the AOSP face domain does not. Add the explicit camera-to-face call and FD use,
camera attribution reads, HIDL preview token lookup and gralloc client access.
These are limited to the native camera path and retain SELinux enforcement.
The compiled policy was checked with neverallow assertions enabled; a native
host compiler first reproduced the installed policy byte for byte. Effective
binary-policy queries confirmed the previously denied camera accesses now work.

Source references: PixelOS Settings `752694e6e1a32fc744aca9b65f0b4d8ea2a58f01`,
LineageOS Settings `31b1a9f1cab9638bc6af9f4e6412fbf3b3a7947a`,
`FaceEnrollPreviewFragment.java`, `FaceEnrollEnrolling.java`, and
`res/values/custom_config.xml`.
