# SPDX-License-Identifier: Apache-2.0
"""Preserve accelerated charging in the pinned degas batterysecret daemon."""

import hashlib
from pathlib import Path


STOCK_SHA256 = 'c9cb726ddd03671010cf94d7a0b539543a82ba209905f98d89dd08bee2cbf5e2'
FIXED_SHA256 = '6cae3723065ad87e89a1d11dba5c6d3f5ff05c2161aa2635676fe5542ebb3dea'

# The degas branch resets two adjacent feature bytes despite main() initially
# enabling acceleration. verify_pd_digest() then forces the persistent property
# false on every connection. Reset reverse_auth only; preserve accelerate=1.
# sturh wzr, [x19, #0x31] -> sturb wzr, [x19, #0x31]
# Neighboring device matching, sysfs paths and EEA/smart-sense flags are retained.
STOCK_SIGNATURE = bytes.fromhex(
    '2001487a 21080054 28208052 745600a9 7f120378 686a0079 39000014'
)
FIXED_SIGNATURE = STOCK_SIGNATURE[:16] + bytes.fromhex('7f120338') + STOCK_SIGNATURE[20:]


def patch_batterysecret_bytes(data: bytes) -> bytes:
    digest = hashlib.sha256(data).hexdigest()
    if digest == FIXED_SHA256:
        return data
    if digest != STOCK_SHA256 or data.count(STOCK_SIGNATURE) != 1:
        raise ValueError(f'Unsupported degas batterysecret blob: {digest}')
    result = data.replace(STOCK_SIGNATURE, FIXED_SIGNATURE, 1)
    if hashlib.sha256(result).hexdigest() != FIXED_SHA256:
        raise ValueError('degas batterysecret patch output mismatch')
    return result


def fix_batterysecret_acceleration(ctx, file, file_path, *args, **kwargs):
    path = Path(file_path)
    original = path.read_bytes()
    fixed = patch_batterysecret_bytes(original)
    if fixed != original:
        path.write_bytes(fixed)
