# SPDX-License-Identifier: Apache-2.0
"""Guarded AudioTrack field fixup for the pinned OS3.0.306 EEA IMS sink."""

from pathlib import Path


# ldr w20, [x0, #600] -> [x0, #568] (AudioTrack::initCheck).
# ldr x8, [x0, #168] -> [x0, #112] (AudioTrack::frameCount).
# ldr x9, [x0, #592] -> [x0, #560] (AudioTrack::frameSize).
# Keep neighboring instructions in each signature to reject other stock versions.
PATCHES = (
    (
        bytes.fromhex('800240f9 145842b9 74030035'),
        bytes.fromhex('800240f9 143842b9 74030035'),
    ),
    (
        bytes.fromhex('085440f9 080109cb 092841f9 08010a8b'),
        bytes.fromhex('083840f9 080109cb 091841f9 08010a8b'),
    ),
)


def patch_libsink_bytes(data: bytes) -> bytes:
    result = data
    for original, patched in PATCHES:
        before, after = result.count(original), result.count(patched)
        if before == 1 and after == 0:
            result = result.replace(original, patched, 1)
        elif before != 0 or after != 1:
            raise ValueError('libsink AudioTrack instruction signature is missing or ambiguous')
    return result


def fix_libsink_fields(ctx, file, file_path, *args, **kwargs):
    path = Path(file_path)
    original = path.read_bytes()
    patched = patch_libsink_bytes(original)
    if patched != original:
        path.write_bytes(patched)
