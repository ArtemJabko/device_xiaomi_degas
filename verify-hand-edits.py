#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check the audited IMS dex and MTK Codec2 compatibility edits."""
import hashlib
import sys
import zipfile
from pathlib import Path

from tools.codec2_compat import FIXES
from tools.hypercharge_compat import FIXED_SHA256 as BATTERYSECRET_SHA256

EXPECTED = 'cc2312e54d4a4ce18de6d12d32fbe2522cf88273e2aab36c7194b5d1cf48a6b7'

def main():
    vendor = Path(__file__).resolve().parents[3] / 'vendor/xiaomi/degas/proprietary'
    apk = vendor / 'system_ext/priv-app/ImsService/ImsService.apk'
    try:
        with zipfile.ZipFile(apk) as archive:
            actual = hashlib.sha256(archive.read('classes.dex')).hexdigest()
    except (OSError, KeyError, zipfile.BadZipFile) as error:
        print(f'FAIL: {error}')
        return 1
    if actual != EXPECTED:
        print(f'FAIL: IMS dex {actual}; expected audited receiver-compatible dex {EXPECTED}')
        return 1
    print('OK: audited IMS dex with 10 explicit legacy receiver registrations')
    for kind, name in (
        ('store', 'vendor/bin/hw/android.hardware.media.c2@1.2-mediatek-64b'),
        ('memory', 'vendor/lib64/libcodec2_mtk_vdec.so'),
    ):
        try:
            digest = hashlib.sha256((vendor / name).read_bytes()).hexdigest()
        except OSError as error:
            print(f'FAIL: {error}')
            return 1
        if digest != FIXES[kind][1]:
            print(f'FAIL: unpatched or unrecognized Codec2 {kind} blob: {digest}')
            return 1
    print('OK: pinned Codec2 allocation and DMA-BUF backend fixes')
    digest = hashlib.sha256((vendor / 'vendor/bin/batterysecret').read_bytes()).hexdigest()
    if digest != BATTERYSECRET_SHA256:
        print(f'FAIL: unpatched or unrecognized degas batterysecret: {digest}')
        return 1
    print('OK: degas batterysecret acceleration fix')
    return 0

if __name__ == '__main__':
    sys.exit(main())
