#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Disambiguate camera DB modules and normalize literal-star model source paths."""
import hashlib
import re
import shutil
from pathlib import Path

VENDOR = Path(__file__).resolve().parents[3] / 'vendor/xiaomi/degas'
MODEL_ALIASES = {
    name: name.replace('*', 'x') for name in (
        'SR270*480.dla', 'SR288*640.dla', 'SR360*640.dla',
        'SR376*896.dla', 'SR480*864.dla', 'SR486*864.dla',
        'SR504*896.dla', 'SR540*960.dla', 'SR720*1280.dla',
    )
}

def fix_model_copy_rules(mk):
    """Only source paths change; retain the factory filenames in vendor.img."""
    for factory, alias in MODEL_ALIASES.items():
        source = f'vendor/xiaomi/degas/proprietary/vendor/data/model/{factory}'
        normalized = f'vendor/xiaomi/degas/proprietary/vendor/data/model/{alias}'
        mk = mk.replace(source + ':', normalized + ':')
    return mk

def fix(bp, mk):
    replacements = []
    def rename(match):
        block = match.group()
        name = re.search(r'(?m)^\s*name:\s*"(ISP_(?:param|mapping)\.db)"', block)
        sub = re.search(r'(?m)^\s*sub_dir:\s*"([^"]+)"', block)
        if not name or not sub:
            return block
        tag = hashlib.sha1(sub[1].encode()).hexdigest()[:12]
        new = name[1].replace('.', '_') + '_' + tag
        replacements.append((name[1], new))
        return block[:name.start(1)] + new + block[name.end(1):]
    bp = re.sub(r'\b(?:sh_binary|prebuilt_etc)\s*\{.*?\n\}', rename, bp, flags=re.S)
    queue = list(replacements)
    lines = []
    for line in mk.splitlines(keepends=True):
        token = line.strip().rstrip('\\').strip()
        if queue and token == queue[0][0]:
            old, new = queue.pop(0)
            line = line.replace(old, new, 1)
        lines.append(line)
    if queue:
        raise ValueError(f'Unmatched vendor package entries: {queue}')
    names = re.findall(r'\bname:\s*"([^"]+)"', bp)
    if len(names) != len(set(names)):
        raise ValueError('Duplicate vendor module names remain')
    return bp, ''.join(lines), len(replacements)

def main():
    bp, mk = VENDOR / 'Android.bp', VENDOR / 'degas-vendor.mk'
    fixed_bp, fixed_mk, count = fix(bp.read_text(), mk.read_text())
    fixed_mk = fix_model_copy_rules(fixed_mk)
    model_dir = VENDOR / 'proprietary/vendor/data/model'
    for factory, alias in MODEL_ALIASES.items():
        shutil.copy2(model_dir / factory, model_dir / alias)
    bp.write_text(fixed_bp)
    mk.write_text(fixed_mk)
    print(f'OK: renamed {count} camera DB modules; no duplicate names remain')
    print(f'OK: normalized {len(MODEL_ALIASES)} model source paths; factory install filenames preserved')

if __name__ == '__main__':
    main()
