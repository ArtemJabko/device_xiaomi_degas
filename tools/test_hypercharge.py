#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify the degas-only fix against an actual pinned stock dump."""
import hashlib
import sys
from pathlib import Path

from hypercharge_compat import FIXED_SHA256, patch_batterysecret_bytes


def main():
    original = Path(sys.argv[1]).read_bytes()
    fixed = patch_batterysecret_bytes(original)
    assert hashlib.sha256(fixed).hexdigest() == FIXED_SHA256
    assert len(fixed) == len(original)
    # Exact byte delta: AArch64 store width, in the degas branch only.
    assert [(i, a, b) for i, (a, b) in enumerate(zip(original, fixed)) if a != b] == [
        (0x37b7, 0x78, 0x38)
    ]
    assert patch_batterysecret_bytes(fixed) == fixed
    for unsupported in (original[:-1], original + b'\0', fixed[:-1]):
        try:
            patch_batterysecret_bytes(unsupported)
        except ValueError:
            pass
        else:
            raise AssertionError('Unrecognized blob was accepted')
    # Authentication, VDM negotiation and sysfs strings remain byte-identical;
    # the only changed byte lies in main's degas feature initialization.
    assert original[0x6930:] == fixed[0x6930:]
    print('OK: exact degas store-width change; authentication preserved; idempotent; unknown blobs rejected')


if __name__ == '__main__':
    main()
