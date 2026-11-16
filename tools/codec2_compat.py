# SPDX-License-Identifier: Apache-2.0
"""Guarded fixes for the pinned OS3.0.306 MTK Codec2 blobs on Android 17."""

import hashlib
from pathlib import Path


# ComponentStore grew from 0x108 to 0x120 bytes. Its Android 17 RefBase
# subobject starts at 0x110, beyond the stock executable's allocation.
# mov w0, #0x108 -> mov w0, #0x120; preserve the constructor and virtual calls.
STORE_SIGNATURE = bytes.fromhex(
    '00218052 93010094 a88300d1 f30300aa '
    'b0010094 a18300d1 e00313aa b1010094'
)

# MemoryDevice's first secure request used to skip DMA-BUF detection, leaving
# the shared backend enum at zero on kernels without /dev/ion, then aborting.
# tbnz w20, #0, existing_backend -> cbnz w0, existing_backend
# (w20 = secure, w0 = CheckIonSupport()). ION still selects its secure backend;
# without ION, either first request initializes the existing DMA-BUF backend.
MEMORY_SIGNATURE = bytes.fromhex(
    'd50b0294 56010035 34010037 1f2003d5 '
    '212ca470 00020036 22faffd0'
)

FIXES = {
    'store': (
        '46aeada816718c4963b642934fa0adcab5608772667fb26efe8ba97373324a2a',
        'ecb549c005cb01e8ff8908d2f5edb1ef8bd628f0131fb6a9c8640e100be064c5',
        STORE_SIGNATURE,
        bytes.fromhex('00248052') + STORE_SIGNATURE[4:],
    ),
    'memory': (
        'ac36eaf28b6d73711741c3ea235bc0d2a7163cf67059973ff47730144f596535',
        '00bbb57dc51b50d56608c958a17b460ca3d1e797ec317fa76b456e61d6225185',
        MEMORY_SIGNATURE,
        MEMORY_SIGNATURE[:8] + bytes.fromhex('20010035') + MEMORY_SIGNATURE[12:],
    ),
}


def patch_codec2_bytes(data: bytes, kind: str) -> bytes:
    original_hash, fixed_hash, original, fixed = FIXES[kind]
    digest = hashlib.sha256(data).hexdigest()
    if digest == fixed_hash:
        return data
    if digest != original_hash or data.count(original) != 1:
        raise ValueError(f'Unsupported MTK Codec2 {kind} blob: {digest}')
    result = data.replace(original, fixed, 1)
    if hashlib.sha256(result).hexdigest() != fixed_hash:
        raise ValueError(f'MTK Codec2 {kind} patch output mismatch')
    return result


def fix_codec2_store_size(ctx, file, file_path, *args, **kwargs):
    path = Path(file_path)
    path.write_bytes(patch_codec2_bytes(path.read_bytes(), 'store'))


def fix_codec2_memory_backend(ctx, file, file_path, *args, **kwargs):
    path = Path(file_path)
    path.write_bytes(patch_codec2_bytes(path.read_bytes(), 'memory'))
