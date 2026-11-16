#!/usr/bin/env python3
"""Read validated sparse LP images without allocating a complete raw super."""
import argparse
import bisect
import hashlib
import struct
from pathlib import Path


class SparseReader:
    def __init__(self, path):
        self.path = Path(path)
        self.chunks = []
        with self.path.open('rb') as stream:
            header = stream.read(28)
            magic, major, minor, fh, ch, bs, blocks, count, crc = struct.unpack('<I4H4I', header)
            if (magic, major, minor, fh, ch, bs, crc) != (0xed26ff3a, 1, 0, 28, 12, 4096, 0):
                raise ValueError('Unexpected sparse header')
            offset = 0
            for _ in range(count):
                kind, reserved, n, total = struct.unpack('<2H2I', stream.read(12))
                length = n * bs
                payload = {0xcac1: length, 0xcac2: 4, 0xcac3: 0}.get(kind)
                if not n or reserved or payload is None or total != 12 + payload:
                    raise ValueError('Unexpected sparse chunk')
                physical = stream.tell()
                fill = stream.read(4) if kind == 0xcac2 else b'\0' * 4
                if kind == 0xcac1:
                    stream.seek(length, 1)
                if len(fill) != 4 or stream.tell() > self.path.stat().st_size:
                    raise ValueError('Truncated sparse chunk')
                self.chunks.append((offset, length, kind, physical, fill))
                offset += length
            if offset != blocks * bs or stream.read(1):
                raise ValueError('Sparse size mismatch')
        self.size = offset
        self.starts = [c[0] for c in self.chunks]

    def read(self, offset, length):
        if offset < 0 or length < 0 or offset + length > self.size:
            raise ValueError('Read outside image')
        result = bytearray()
        with self.path.open('rb') as stream:
            while length:
                start, size, kind, physical, fill = self.chunks[bisect.bisect_right(self.starts, offset) - 1]
                relative = offset - start
                n = min(length, size - relative)
                if kind == 0xcac1:
                    stream.seek(physical + relative)
                    data = stream.read(n)
                else:
                    phase = relative % 4
                    data = (fill * ((phase + n + 3) // 4))[phase:phase+n]
                if len(data) != n:
                    raise ValueError('Truncated read')
                result.extend(data)
                offset += n
                length -= n
        return bytes(result)

    def partitions(self):
        geometry = self.read(4096, 4096)
        if geometry != self.read(8192, 4096):
            raise ValueError('LP geometry copies disagree')
        magic, size = struct.unpack_from('<II', geometry)
        if magic != 0x616c4467 or size != 52 or any(geometry[size:]):
            raise ValueError('Unexpected LP geometry')
        check = bytearray(geometry[:size])
        check[8:40] = b'\0' * 32
        if hashlib.sha256(check).digest() != geometry[8:40]:
            raise ValueError('LP geometry checksum')
        maximum, slots, blocksize = struct.unpack_from('<III', geometry, 40)
        if slots not in (2, 3) or blocksize != 4096 or maximum % 4096:
            raise ValueError('Unexpected LP metadata geometry')
        copies = [self.read(12288 + i * maximum, maximum) for i in range(slots * 2)]
        if any(c != copies[0] for c in copies):
            raise ValueError('LP metadata copies disagree')
        metadata = copies[0]
        magic, major, minor, hs = struct.unpack_from('<IHHI', metadata)
        ts = struct.unpack_from('<I', metadata, 44)[0]
        if magic != 0x414c5030 or major != 10 or minor not in (0, 1, 2) or hs not in (128, 256):
            raise ValueError('Unexpected LP header')
        check = bytearray(metadata[:hs])
        check[12:44] = b'\0' * 32
        if hashlib.sha256(check).digest() != metadata[12:44]:
            raise ValueError('LP header checksum')
        if hs + ts > maximum or hashlib.sha256(metadata[hs:hs+ts]).digest() != metadata[48:80] or any(metadata[hs+ts:]):
            raise ValueError('LP table checksum/padding')
        tables = []
        cursor = 0
        for pos, width in zip((80, 92, 104, 116), (52, 24, 48, 64)):
            off, count, actual = struct.unpack_from('<III', metadata, pos)
            if off != cursor or actual != width or off + count * width > ts:
                raise ValueError('LP table layout')
            tables.append([metadata[hs+off+i*width:hs+off+(i+1)*width] for i in range(count)])
            cursor += count * width
        if cursor != ts or len(tables[3]) != 1:
            raise ValueError('LP extra data/devices')
        firstsector, alignment, alignmentoffset, device_size = struct.unpack_from('<QIIQ', tables[3][0])
        if device_size != self.size:
            raise ValueError('LP device size')
        result, ranges, used = {}, [], []
        for part in tables[0]:
            name = part[:36].split(b'\0')[0].decode('ascii')
            first, count, group = struct.unpack_from('<III', part, 40)
            if name in result or first + count > len(tables[1]) or group >= len(tables[2]):
                raise ValueError('LP partition indices')
            extents = []
            used.extend(range(first, first+count))
            for extent in tables[1][first:first+count]:
                length, kind, sector, device = struct.unpack('<QIQI', extent)
                if kind or device or not length or sector < firstsector or (sector+length)*512 > self.size:
                    raise ValueError('LP physical extent')
                extents.append((sector*512, length*512))
                ranges.append((sector, sector+length))
            result[name] = extents
        ranges.sort()
        if sorted(used) != list(range(len(tables[1]))) or any(a[1] > b[0] for a, b in zip(ranges, ranges[1:])):
            raise ValueError('LP overlap/shared extent')
        return result

    def extract(self, name, output):
        extents = self.partitions()[name]
        digest = hashlib.sha256()
        with Path(output).open('xb') as stream:
            for offset, length in extents:
                while length:
                    n = min(length, 8*1024*1024)
                    data = self.read(offset, n)
                    digest.update(data)
                    if any(data):
                        stream.write(data)
                    else:
                        stream.seek(n, 1)
                    offset += n
                    length -= n
            stream.truncate()
        return digest.hexdigest()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('partition')
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(SparseReader(args.image).extract(args.partition, args.output))
