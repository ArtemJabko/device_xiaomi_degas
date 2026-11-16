#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Host checks for the device tree, matched stock kernel and extraction inputs.

These checks do not replace Android's build, checkvintf or device tests.
"""
import argparse
import ast
import hashlib
import json
import re
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

DEVICE = Path(__file__).resolve().parents[1]
ROOT = DEVICE.parents[2]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def stock_file(root, source):
    p = root / source
    if not p.exists() and source.startswith('system/'):
        p = root / 'system' / source
    return p


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stock', type=Path)
    parser.add_argument('--vendor', action='store_true')
    args = parser.parse_args()
    for p in DEVICE.rglob('*.xml'):
        ET.parse(p)
    for p in DEVICE.rglob('*.py'):
        ast.parse(p.read_text(), str(p))
    product = (DEVICE / 'lineage_degas.mk').read_text()
    assert 'PRODUCT_NAME := lineage_degas' in product
    assert 'TARGET_PROVIDES_FACE_UNLOCK_HAL := true' in product
    assert 'vendor/lineage/config/common_full_phone.mk' in product
    assert 'WITH_GMS := true' not in product, 'LineageOS must not force bundled GMS'
    assert '$(LOCAL_DIR)/lineage_degas.mk' in (DEVICE / 'AndroidProducts.mk').read_text()
    assert 'BuildFingerprint=' not in product, 'Keep the Android 17 generated fingerprint'
    board = (DEVICE / 'BoardConfig.mk').read_text()
    assert 'BOARD_SUPER_PARTITION_SIZE := 9663676416' in board
    assert 'BOARD_PREBUILT_DTBOIMAGE :=' in board
    assert 'ODM_MANIFEST_FILES +=' in board
    assert ET.parse(DEVICE / 'manifest.xml').getroot().get('target-level') == '8'
    kernel = ROOT / 'device/xiaomi/degas-kernel'
    locked = json.loads((kernel / 'stock-kernel.lock.json').read_text())
    for name, expected in locked['files'].items():
        p = kernel / name
        assert p.is_file() and digest(p) == expected, f'Kernel hash mismatch: {name}'
    # Android's prebuilt DTB rule concatenates only *.dtb files. A .img source
    # silently yields an empty output and a vendor_boot without the device DTB.
    assert 'BOARD_PREBUILT_DTBIMAGE_DIR := $(KERNEL_PATH)/dtb' in board
    assert sorted(p.name for p in (kernel / 'dtb').glob('*.dtb')) == ['degas.dtb']
    dtb = (kernel / 'dtb/degas.dtb').read_bytes()
    magic, total, header, entry, count, offset, page, version = struct.unpack_from('>8I', dtb)
    assert (magic, total, header, entry, count, offset, version) == (
        0xd7b7ab1e, len(dtb), 32, 32, 1, 32, 0), 'Invalid stock DT table'
    dt_size, dt_offset = struct.unpack_from('>2I', dtb, offset)
    assert dt_offset + dt_size == len(dtb)
    assert struct.unpack_from('>2I', dtb, dt_offset) == (0xd00dfeed, dt_size)
    lists = {
        'system_dlkm.modules.load': 'system',
        'vendor_dlkm.modules.load': 'vendor',
        'vendor_ramdisk.modules.load': 'vendor_ramdisk',
        'vendor_ramdisk.modules.load.recovery': 'vendor_ramdisk',
    }
    for name, subdir in lists.items():
        for module in (DEVICE / name).read_text().splitlines():
            if module and not module.startswith('#'):
                p = kernel / 'modules' / subdir / module
                assert p.is_file(), f'{name}: missing {module}'
                assert p.read_bytes()[:4] == b'\x7fELF', f'Invalid module: {module}'
    for module in ('gps_drv_dl_v051.ko', 'gps_pwr.ko', 'gps_scp.ko'):
        assert (kernel / 'modules/vendor' / module).is_file(), module
    print(f'OK: XML/Python/product/FCM checks and {len(locked["files"])} kernel hashes')
    if args.stock:
        locked_blobs = json.loads((DEVICE / 'stock-blobs.lock.json').read_text())
        for f in locked_blobs['files']:
            p = stock_file(args.stock, f['source'])
            assert p.is_file(), f'Missing stock blob: {f["source"]}'
            assert digest(p) == f['sha256'], f'Stock blob mismatch: {f["source"]}'
        for raw in (DEVICE / 'proprietary-firmware.txt').read_text().splitlines():
            if not raw or raw.startswith('#'):
                continue
            name = raw.split(';')[0]
            expected = raw.split('|')[1]
            assert hashlib.sha1((args.stock / name).read_bytes()).hexdigest() == expected, name
        print(f'OK: {len(locked_blobs["files"])} raw blobs and all firmware match EEA 3.0.306')
    if args.vendor:
        vendor = ROOT / 'vendor/xiaomi/degas'
        for name in ('Android.bp', 'degas-vendor.mk', 'BoardConfigVendor.mk'):
            assert (vendor / name).is_file(), f'Missing vendor makefile: {name}'
        names = re.findall(r'\bname:\s*"([^"]+)"', (vendor / 'Android.bp').read_text())
        assert len(names) == len(set(names)), 'Duplicate vendor modules'
        for raw in (DEVICE / 'proprietary-files.txt').read_text().splitlines():
            if not raw or raw.startswith('#'):
                continue
            mapping = raw.lstrip('-').split('|')[0].split(';')[0]
            dst = mapping.split(':')[-1]
            assert (vendor / 'proprietary' / dst).is_file(), f'Missing vendor output: {dst}'
        print('OK: generated vendor makefiles, module names and proprietary output paths')
    print('Build, ELF linkage, checkvintf, SELinux and hardware runtime require Linux/ROM validation')


if __name__ == '__main__':
    main()
