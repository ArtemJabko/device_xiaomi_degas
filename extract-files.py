#!/usr/bin/env -S PYTHONPATH=../../../tools/extract-utils python3
#
# SPDX-FileCopyrightText: 2024 The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#

import copy
import json
from pathlib import Path

from tools.libsink_compat import fix_libsink_fields
from tools.codec2_compat import fix_codec2_memory_backend, fix_codec2_store_size
from tools.hypercharge_compat import fix_batterysecret_acceleration

from extract_utils.fixups_blob import (
    blob_fixup,
    blob_fixups_user_type,
)
from extract_utils.fixups_lib import (
    lib_fixups,
    lib_fixups_user_type,
)
from extract_utils.main import (
    ExtractUtils,
    ExtractUtilsModule,
)

namespace_imports = [
    'device/xiaomi/degas',
    'hardware/mediatek',
    'hardware/xiaomi',
]

def lib_fixup_vendor_suffix(lib: str, partition: str, *args, **kwargs):
    return f'{lib}-{partition}' if partition == 'vendor' else None

def lib_fixup_vendor_or_odm_suffix(lib: str, partition: str, *args, **kwargs):
    return f'{lib}-vendor' if partition in ('vendor', 'odm') else None


lib_fixups: lib_fixups_user_type = {
    **lib_fixups,
    # Keep stock typed AIDL helpers separate from Android 17's latest versions.
    ('libaudio_aidl_conversion_common_ndk',
     'lib_android_keymaster_keymint_utils',
     'libkeymint',
     'libkeymint_support',
     'libkeymint_remote_prov_support'): lib_fixup_vendor_or_odm_suffix,
    # Preserve MTK prebuilts without overriding source-built platform modules.
    ('libmnl',
     'libformatter',
     'vendor.mediatek.hardware.mtkpower-V1-ndk',
     'vendor.mediatek.hardware.bluetooth.audio-V1-ndk',
     'vendor.mediatek.hardware.bluetooth.audio@2.1',
     'vendor.mediatek.hardware.bluetooth.audio@2.2',
     'vendor.mediatek.hardware.netdagent@1.0'): lib_fixup_vendor_or_odm_suffix,
    # Stock ships distinct vendor and ODM/system_ext copies of these libraries.
    # MODULE_SUFFIX keeps the installed ELF filename; qualify vendor dependencies too.
    ('libHISCppAlgos',
     'libcameraopt',
     'libcom.xiaomi.hwadapter.decoupleutil',
     'libcom.xiaomi.hwadapter.postprocinterface',
     'libhis_face_tracking',
     'libhis_motion_tracker',
     'libmialgo_aio_seg',
     'libmialgo_utils',
     'libremosaic_wrapper',
     'vendor.mediatek.hardware.mbrain-V2-ndk',
     'vendor.mediatek.hardware.pq_aidl-V7-ndk'): lib_fixup_vendor_suffix,
    ('libtflite_mtk',
     'vendor.mediatek.hardware.apuware.utils-V1-ndk',
     'vendor.mediatek.hardware.apuware.utils@2.0',
     'vendor.mediatek.hardware.videotelephony-V1-ndk'): lib_fixup_vendor_suffix,
}


blob_fixups: blob_fixups_user_type = {
    'vendor/bin/batterysecret': blob_fixup()
        .call(fix_batterysecret_acceleration),
    'vendor/bin/hw/android.hardware.media.c2@1.2-mediatek-64b': blob_fixup()
        .call(fix_codec2_store_size, need_tmp_dir=False),

    'vendor/lib64/libcodec2_mtk_vdec.so': blob_fixup()
        .call(fix_codec2_memory_backend, need_tmp_dir=False),

    # Stock MTK IMS still uses legacy receivers in WFC, RCS and config paths.
    'system_ext/priv-app/ImsService/ImsService.apk': blob_fixup()
        .apktool_patch('patches/ims-receivers'),

    'vendor/lib64/hw/audio.primary.mediatek.so': blob_fixup()
        .replace_needed('libalsautils.so', 'libalsautils-v34.so')
        .replace_needed('libtinyxml2.so', 'libtinyxml2-v34.so'),

    'vendor/lib64/vendor.mediatek.hardware.bluetooth.audio-V1-ndk-vendor.so': blob_fixup()
        .replace_needed('android.hardware.audio.common-V1-ndk.so', 'android.hardware.audio.common-V2-ndk.so'),

    ('vendor/etc/init/hw/init.batterysecret.rc',
     'vendor/etc/init/hw/init.mi_thermald.rc'): blob_fixup()
        .regex_replace('.*seclabel.*\n', ''),

    ('vendor/lib64/libarmnn_ndk.mtk.vndk.so',
     'vendor/lib64/mt6897/lib3a.ae.stat.so'): blob_fixup()
        .add_needed('liblog.so'),

    # These stock AF libraries import NDK chrono clocks from the existing ODM
    # runtime, but omit it from DT_NEEDED. Platform libc++ uses a different ABI.
    ('vendor/lib64/libaaa_afassistctrl.so',
     'vendor/lib64/libaaa_afassist_V2.so'): blob_fixup()
        .add_needed('libc++_shared.so'),

    'vendor/lib64/mt6897/libmtkcam_hal_aidl_common.so': blob_fixup()
        .replace_needed('android.hardware.camera.common-V2-ndk.so', 'android.hardware.camera.common-V1-ndk.so'),

    ('vendor/lib64/mt6897/libmtkcam_grallocutils.so',
     'vendor/lib64/libmtkcam_grallocutils_aidlv1helper.so'): blob_fixup()
        .replace_needed('android.hardware.graphics.allocator-V1-ndk.so', 'android.hardware.graphics.allocator-V2-ndk.so')
        .replace_needed('android.hardware.graphics.common-V4-ndk.so', 'android.hardware.graphics.common-V7-ndk.so')
        # same libui unification as the camera blobs below
        .replace_needed('libui.so', 'libui-v34.so'),

    # Android 17's vendor LLNDK stub exports these names without symbol versions.
    # Cover both linked camera libraries and their dlopen copies under etc/camera.
    ('odm/lib64/libAncHumanVideoBokehV4.so',
     'odm/lib64/libMiVideoFilter.so',
     'odm/lib64/libTrueSight.so',
     'odm/lib64/libalLDC.so',
     'odm/lib64/libalAILDC.so',
     'odm/lib64/libalhLDC.so',
     'odm/lib64/libwa_widelens_undistort.so',
     'vendor/etc/camera/beauty/libTrueSight.so',
     'vendor/etc/camera/ldc/libwa_widelens_undistort.so',
     'vendor/lib64/libMiPhotoFilter.so',
     'vendor/lib64/libmcve.so',
     'vendor/lib64/mt6897/libneuralnetworks_sl_driver_mtk_prebuilt.so'): blob_fixup()
        .clear_symbol_version('AHardwareBuffer_allocate')
        .clear_symbol_version('AHardwareBuffer_createFromHandle')
        .clear_symbol_version('AHardwareBuffer_describe')
        .clear_symbol_version('AHardwareBuffer_getNativeHandle')
        .clear_symbol_version('AHardwareBuffer_isSupported')
        .clear_symbol_version('AHardwareBuffer_lock')
        .clear_symbol_version('AHardwareBuffer_lockPlanes')
        .clear_symbol_version('AHardwareBuffer_release')
        .clear_symbol_version('AHardwareBuffer_unlock'),

    'vendor/lib64/mt6897/libmtkcam_hwnode.jpegnode.so': blob_fixup()
        .replace_needed('libultrahdr.so', 'libultrahdr-v34.so'),

    (
        'odm/lib64/camera/plugins/com.xiaomi.plugin.gainmap.so',
        'odm/lib64/camera/plugins/com.xiaomi.plugin.jpegrAggr.so',
    ): blob_fixup()
        .replace_needed('libultrahdr.so', 'libultrahdr-v34.so'),

    'vendor/lib64/libultrahdr-v34.so': blob_fixup()
        .replace_needed('libjpegencoder.so', 'libjpegencoder-v34.so')
        .replace_needed('libjpegdecoder.so', 'libjpegdecoder-v34.so'),

    ('vendor/bin/hw/mt6897/android.hardware.graphics.allocator-V2-service-mediatek.mt6897',
     'vendor/lib64/egl/mt6897/libGLES_mali.so',
     'vendor/lib64/hw/mt6897/android.hardware.graphics.allocator-V2-mediatek.so',
     'vendor/lib64/hw/mt6897/android.hardware.graphics.mapper@4.0-impl-mediatek.so',
     'vendor/lib64/hw/mt6897/mapper.mediatek.so',
     'vendor/lib64/libaimemc.so',
     'vendor/lib64/libcodec2_fsr.so',
     'vendor/lib64/vendor.mediatek.hardware.camera.isphal-V1-ndk.so',
     'vendor/lib64/vendor.mediatek.hardware.pq_aidl-V2-ndk.so',
     'vendor/lib64/vendor.mediatek.hardware.pq_aidl-V4-ndk.so',
     'vendor/lib64/vendor.mediatek.hardware.pq_aidl-V6-ndk.so',
     'vendor/lib64/vendor.mediatek.hardware.pq_aidl-V7-ndk.so'): blob_fixup()
        .replace_needed('android.hardware.graphics.common-V4-ndk.so', 'android.hardware.graphics.common-V7-ndk.so'),

    'vendor/lib64/mt6897/libpqconfig.so': blob_fixup()
        .replace_needed('android.hardware.sensors-V2-ndk.so', 'android.hardware.sensors-V3-ndk.so'),

    ('vendor/etc/init/android.hardware.graphics.allocator-V2-service-mediatek.rc',
     'vendor/etc/init/android.hardware.graphics.composer@3.2-service.rc' ): blob_fixup()
        .regex_replace('.*writepid.*\n', ''),

    'vendor/lib64/hw/mt6897/vendor.mediatek.hardware.pq_aidl-impl.so': blob_fixup()
        .replace_needed('libtinyxml2.so', 'libtinyxml2-v34.so')
        .replace_needed('libui.so', 'libui-v34.so'),

    # GraphicBufferMapper::lock/unlock (old libui API removed in A16).
    #
    # mihal drags the rest of the camera stack with it: everything below shares
    # android::GraphicBuffer objects with it, and a process holding both libui
    # and libui-v34 ends up with two layouts of that class under the same symbol
    # names. The mismatch corrupts the heap in the vendor tract - caught with
    # malloc_debug guard on 2026-08-16 (CORRUPTED REAR GUARD in
    # RealtimePostProcessor::deleteRecord) and gone once these are relinked.
    'vendor/lib64/libmicamera_hal_core.so': blob_fixup()
        .replace_needed('libui.so', 'libui-v34.so'),

    ('vendor/lib64/libcom.xiaomi.ecoenginemonitor.so',
     'vendor/lib64/libcom.xiaomi.grallocutils.so',
     'vendor/lib64/libcom.xiaomi.pluginutils.so',
     'vendor/lib64/libcom.xiaomi.sensorpolicy.so',
     'vendor/lib64/libecoengine.so',
     'vendor/lib64/libmialgoengine.so',
     'vendor/lib64/mt6897/libmtkcam_thirdparty.customer.so',
     'odm/lib64/camera/plugins/com.xiaomi.plugin.beautydeformation.so',
     'odm/lib64/camera/plugins/com.xiaomi.plugin.filter.so',
     'odm/lib64/camera/plugins/com.xiaomi.plugin.videofilter.so'): blob_fixup()
        .replace_needed('libui.so', 'libui-v34.so'),

    # plain-C SetTaskProfiles came from VNDK v34 libprocessgroup on stock
    'vendor/lib64/libcameraopt.so': blob_fixup()
        .add_needed('libprocessgroup_shim.so'),

    # libmiface carries a vestigial DT_NEEDED on libdumpstateutil, which is a
    # /system library the vendor namespace cannot reach. It imports ZERO symbols
    # from it (checked: 0 of its 33 exports are undefined in libmiface), so the
    # entry is simply dropped instead of shipping a system lib into /vendor.
    'vendor/lib64/libmiface.so': blob_fixup()
        .remove_needed('libdumpstateutil.so'),

    # remosaic_process_gain_set exporter must be loaded first (BIND_NOW)
    'odm/lib64/libmiremosaic.so': blob_fixup()
        .add_needed('libremosaic_wrapper.so'),

    ('odm/lib64/hw/displayfeature.default.so',
     'vendor/lib64/libaudiocloudctrl.so',
     'vendor/lib64/libpqxmlflagparser.so',
     'vendor/lib64/libpqxmlparser.so',
     'vendor/lib64/librt_extamp_intf.so',
     'vendor/lib64/libsilkybrightnesscore.so',
     'vendor/lib64/mt6897/libmmlpqImpl.so'): blob_fixup()
        .replace_needed('libtinyxml2.so', 'libtinyxml2-v34.so'),

    ('odm/lib64/libmt_mitee.so',
     'vendor/bin/hw/android.hardware.security.keymint@3.0-service.mitee',
     'vendor/lib64/lib_android_keymaster_keymint_utils-vendor.so',
     'vendor/lib64/libkeymint-vendor.so',
     'vendor/lib64/libkeymint_support-vendor.so',
     'vendor/lib64/libkeymint_remote_prov_support-vendor.so'): blob_fixup()
        .replace_needed('android.hardware.security.keymint-V3-ndk.so', 'android.hardware.security.keymint-V3-ndk-v34.so'),

    'vendor/etc/vintf/manifest/manifest_media_c2_V1_2_default.xml': blob_fixup()
        .regex_replace('.+dolby.+\n', ''),

    'system_ext/lib64/libimsma.so': blob_fixup()
        .replace_needed('libsink.so', 'libsink-mtk.so'),

    'system_ext/lib64/libsink-mtk.so': blob_fixup()
        .call(fix_libsink_fields, need_tmp_dir=False)
        .add_needed('libaudiotrack_degas_shim.so'),

    'odm/bin/hw/vendor.xiaomi.sensor.citsensorservice.aidl': blob_fixup()
        .replace_needed('libtinyxml2.so', 'libtinyxml2-v34.so')
        .replace_needed('libui.so', 'libui-v34.so'),
}  # fmt: skip

# Exact DT_NEEDED consumers from the pinned stock dump. Rename installed ELFs as
# well as modules so source-built vendor variants retain their own install paths.
renames = json.loads(Path(__file__).with_name('stock-library-renames.json').read_text())
expanded_fixups = {}
for paths, fixup in blob_fixups.items():
    for path in (paths if isinstance(paths, tuple) else (paths,)):
        expanded_fixups[path] = copy.deepcopy(fixup)
# fmt v7 is part of VNDK 34 libbase; current platform libbase exports fmt v11.
for path in ('vendor/lib64/libkeymint_remote_prov_support-vendor.so',
             'vendor/lib64/libcppbor_external-degas-compat.so'):
    expanded_fixups.setdefault(path, blob_fixup()).replace_needed(
        'libbase.so', 'libbase-degas-v34.so')
for path, libraries in renames['consumers'].items():
    fixup = expanded_fixups.setdefault(path, blob_fixup())
    for library in libraries:
        fixup.replace_needed(library, renames['libraries'][library])
blob_fixups = expanded_fixups

module = ExtractUtilsModule(
    'degas',
    'xiaomi',
    blob_fixups=blob_fixups,
    lib_fixups=lib_fixups,
    namespace_imports=namespace_imports,
    add_firmware_proprietary_file=True,
)

if __name__ == '__main__':
    utils = ExtractUtils.device(module)
    utils.run()
