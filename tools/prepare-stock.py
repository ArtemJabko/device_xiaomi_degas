#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Prepare EEA 3.0.306 stock inputs and matched kernel; no device flashing.

Requires fsck.erofs and lz4 on PATH. Use a new work directory. The sparse LP
reader lives beside this script. This accepts the supplied Xiaomi fastboot
layout, not arbitrary OTA releases.
"""
import argparse
import hashlib
import json
import shutil
import struct
import subprocess
from pathlib import Path, PurePosixPath
from sparse_lp_extract import SparseReader

DEVICE = Path(__file__).resolve().parents[1]
ROOT = DEVICE.parents[2]
PARTITIONS = ('system', 'system_ext', 'product', 'vendor', 'odm',
              'system_dlkm', 'vendor_dlkm', 'odm_dlkm')


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def cpio_modules(data, output):
    pos = 0
    while pos + 110 <= len(data):
        header = data[pos:pos+110]
        if header[:6] not in (b'070701', b'070702'):
            raise ValueError('Unsupported vendor ramdisk CPIO')
        fields = [int(header[6+i*8:14+i*8], 16) for i in range(13)]
        mode, size, namesize = fields[1], fields[6], fields[11]
        namebytes = data[pos+110:pos+110+namesize]
        if not namesize or not namebytes.endswith(b'\0'):
            raise ValueError('Malformed CPIO filename')
        name = namebytes[:-1].decode()
        pos = (pos + 110 + namesize + 3) & ~3
        body = data[pos:pos+size]
        if len(body) != size:
            raise ValueError('Truncated CPIO entry')
        pos = (pos + size + 3) & ~3
        if name == 'TRAILER!!!':
            return
        p = PurePosixPath(name)
        if '..' in p.parts or p.is_absolute():
            raise ValueError('Unsafe CPIO path')
        if str(p).startswith('lib/modules/') and (mode & 0o170000) == 0o100000:
            target = output / p
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
    raise ValueError('Missing CPIO trailer')


def prepare_kernel(images, dump, work, kernel):
    boot = (images / 'boot.img').read_bytes()
    assert boot[:8] == b'ANDROID!' and struct.unpack_from('<I', boot, 40)[0] == 4
    size = struct.unpack_from('<I', boot, 8)[0]
    vendor = (images / 'vendor_boot.img').read_bytes()
    assert vendor[:8] == b'VNDRBOOT' and struct.unpack_from('<I', vendor, 8)[0] == 4
    page = struct.unpack_from('<I', vendor, 12)[0]
    ramdisk_size = struct.unpack_from('<I', vendor, 24)[0]
    dtb_size = struct.unpack_from('<I', vendor, 2100)[0]
    header_size = struct.unpack_from('<I', vendor, 2096)[0]
    ramdisk_offset = ((header_size + page - 1) // page) * page
    dtb_offset = ramdisk_offset + ((ramdisk_size + page - 1) // page) * page
    table_size, table_count, entry_size = struct.unpack_from('<3I', vendor, 2112)
    assert table_size == table_count * entry_size and entry_size == 108
    table_offset = dtb_offset + ((dtb_size + page - 1) // page) * page
    platform = []
    for index in range(table_count):
        size_, offset, kind = struct.unpack_from('<3I', vendor, table_offset + index * entry_size)
        if kind == 1:
            platform.append((size_, offset))
    assert len(platform) == 1
    size_, offset = platform[0]
    assert offset + size_ <= ramdisk_size
    packed = work / 'vendor-platform.lz4'
    packed.write_bytes(vendor[ramdisk_offset+offset:ramdisk_offset+offset+size_])
    cpio = work / 'vendor-platform.cpio'
    subprocess.run(['lz4', '-d', str(packed), str(cpio)], check=True)
    ramdisk = work / 'vendor_ramdisk'
    cpio_modules(cpio.read_bytes(), ramdisk)
    kernel.mkdir(parents=True, exist_ok=False)
    (kernel / 'Image.lz4').write_bytes(boot[4096:4096+struct.unpack_from('<I', boot, 8)[0]])
    (kernel / 'dtb').mkdir()
    (kernel / 'dtb/degas.dtb').write_bytes(vendor[dtb_offset:dtb_offset+dtb_size])
    shutil.copyfile(images / 'dtbo.img', kernel / 'dtbo.img')
    for name, source in (
        ('system', dump / 'system_dlkm/lib/modules'),
        ('vendor', dump / 'vendor_dlkm/lib/modules'),
        ('vendor_ramdisk', ramdisk / 'lib/modules'),
    ):
        target = kernel / 'modules' / name
        target.mkdir(parents=True)
        for module in source.glob('*.ko'):
            shutil.copyfile(module, target / module.name)
    lock = {'stock': 'OS3.0.306.0.WNEEUXM', 'separate_zram_variants': True,
            'files': {str(p.relative_to(kernel)): sha(p) for p in kernel.rglob('*') if p.is_file()}}
    (kernel / 'stock-kernel.lock.json').write_text(json.dumps(lock, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fastboot', type=Path, help='directory containing images/')
    parser.add_argument('--work', type=Path, required=True, help='new stock work directory')
    parser.add_argument('--kernel', type=Path, default=ROOT / 'device/xiaomi/degas-kernel')
    args = parser.parse_args()
    images = args.fastboot.resolve() / 'images'
    reader = SparseReader(images / 'super.img')
    assert reader.size == 9663676416, 'Unexpected super partition geometry'
    assert not args.kernel.exists(), 'Use a new kernel output directory'
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=False)
    parts, dump = work / 'partitions', work / 'dump'
    parts.mkdir()
    dump.mkdir()
    record = {}
    for name in PARTITIONS:
        image = parts / (name + '.img')
        print(f'Extracting {name}', flush=True)
        record[name] = reader.extract(name + '_a', image)
        target = dump / name
        if name == 'product':
            # Only product/etc contributes blobs to this tree. fsck puts the
            # contents of --path=/etc directly into its extraction directory.
            target /= 'etc'
        args_ = ['fsck.erofs', '--no-preserve', '--extract=' + str(target)]
        if name == 'product':
            args_.append('--path=/etc')
        subprocess.run(args_ + [str(image)], check=True)
    vendor_props = (dump / 'vendor/build.prop').read_text()
    assert 'OS3.0.306.0.WNEEUXM' in vendor_props and 'ro.product.vendor.device=degas' in vendor_props
    for raw in (DEVICE / 'proprietary-firmware.txt').read_text().splitlines():
        if not raw or raw.startswith('#'):
            continue
        name = raw.split(';')[0]
        assert hashlib.sha1((images / name).read_bytes()).hexdigest() == raw.split('|')[1], name
        shutil.copyfile(images / name, dump / name)
    prepare_kernel(images, dump, work, args.kernel.resolve())
    (work / 'partitions.json').write_text(json.dumps(record, indent=2) + '\n')
    print(f'Prepared stock dump: {dump}')
    print(f'Prepared kernel: {args.kernel.resolve()}')


if __name__ == '__main__':
    main()
