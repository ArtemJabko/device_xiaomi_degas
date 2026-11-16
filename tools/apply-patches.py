#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check every LineageOS 24 patch before applying; accept already-applied patches."""
import argparse
import os
import subprocess
import tempfile
from pathlib import Path

DEVICE = Path(__file__).resolve().parents[1]
ROOT = DEVICE.parents[2]
SERIES = (
    ('frameworks/base', '0001-udfps-session-refresh-rate.patch'),
    ('frameworks/native', '0002-surfaceflinger-powered-off-modeset.patch'),
    ('external/wpa_supplicant_8', '0003-wpa-mtk-gen4m-sae.patch'),
    ('frameworks/native', '0004-scheduler-suspended-display-vsync.patch'),
    ('frameworks/base', '0005-udfps-idle-aod-refresh-rate.patch'),
    ('build/soong', '0006-check-boot-jars-xiaomi.patch'),
)

def validate_series(project, patches):
    """Validate stacked patches in a scratch index, preserving the real index/tree."""
    with tempfile.TemporaryDirectory(prefix='degas-patches-') as scratch:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(scratch) / 'index'))
        def git(*args, check=True):
            return subprocess.run(['git', '-C', str(project), *map(str, args)],
                                  env=env, capture_output=True, text=True, check=check)
        git('read-tree', 'HEAD')
        # Snapshot only files named by the patches, including newly added files.
        paths = set()
        for patch in patches:
            for line in patch.read_text().splitlines():
                if line.startswith(('--- a/', '+++ b/')):
                    paths.add(line[6:].split('\t')[0])
        for path in sorted(paths):
            if (project / path).exists() or git('ls-files', '--', path).stdout.strip():
                git('add', '-A', '--', path)
        index = Path(env['GIT_INDEX_FILE'])
        snapshot = index.read_bytes()
        # Find the applied prefix. Undo newest first because incremental patches
        # can edit lines introduced by earlier patches. Never alter the real tree.
        for count in range(len(patches), -1, -1):
            index.write_bytes(snapshot)
            valid = True
            for patch in reversed(patches[:count]):
                result = git('apply', '--cached', '--reverse', patch, check=False)
                if result.returncode:
                    valid = False
                    break
            if not valid:
                continue
            # Verify the complete series, with each patch seeing its predecessors.
            for patch in patches:
                result = git('apply', '--cached', patch, check=False)
                if result.returncode:
                    valid = False
                    break
            if valid:
                return set(patches[count:])
        raise SystemExit(f'FAIL: incompatible or incomplete patch series in {project}\n'
                         f'{result.stderr}')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='validate without applying')
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    projects = {}
    for directory, name in SERIES:
        project = args.root.resolve() / directory
        patch = DEVICE / 'patches/lineage24' / name
        projects.setdefault(project, []).append(patch)
    pending = []
    for project, patches in projects.items():
        missing = validate_series(project, patches)
        for patch in patches:
            status = 'applicable' if patch in missing else 'already applied'
            print(f'OK: {status} {project.relative_to(args.root.resolve())}/{patch.name}')
            if patch in missing:
                pending.append((project, patch))
    if not args.check:
        for project, patch in pending:
            subprocess.run(['git', '-C', str(project), 'apply', str(patch)], check=True)
        print(f'OK: applied {len(pending)} patches')

if __name__ == '__main__':
    main()
