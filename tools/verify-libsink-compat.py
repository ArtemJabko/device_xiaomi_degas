#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify the guarded instruction fixup against an actual pinned stock sink."""

import argparse
from pathlib import Path

from libsink_compat import PATCHES, patch_libsink_bytes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stock_libsink', type=Path)
    raw = parser.parse_args().stock_libsink.read_bytes()
    patched = patch_libsink_bytes(raw)
    assert len(patched) == len(raw)
    assert sum(before != after for before, after in zip(raw, patched)) == 3
    assert patch_libsink_bytes(patched) == patched
    status_at = raw.index(PATCHES[0][0]) + 4
    frame_at = raw.index(PATCHES[1][0])
    for position, scale, expected in ((status_at, 4, 568), (frame_at, 8, 112),
                                      (frame_at + 8, 8, 560)):
        instruction = int.from_bytes(patched[position:position + 4], 'little')
        assert ((instruction >> 10) & 0xfff) * scale == expected
    for malformed in (raw + PATCHES[0][0],
                      raw.replace(PATCHES[0][0], b'\xff' + PATCHES[0][0][1:], 1)):
        try:
            patch_libsink_bytes(malformed)
        except ValueError:
            continue
        raise AssertionError('Changed or ambiguous stock instruction signature accepted')
    print('PASS: real stock patch, three decoded field offsets, unchanged size, '
          'idempotence, changed/ambiguous stock rejection')


if __name__ == '__main__':
    main()
