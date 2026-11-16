#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
device_dir="$(cd -- "$(dirname -- "$0")/.." && pwd)"
if [[ $# != 1 ]]; then
    echo "Usage: $0 <prepared-stock-dump>" >&2
    exit 2
fi
dump_dir="$(cd -- "$1" && pwd)"
python3 "$device_dir/tools/validate-tree.py" --stock "$dump_dir"
cd "$device_dir"
PYTHONPATH=../../../tools/extract-utils python3 extract-files.py "$dump_dir"
python3 fix-generated-bp.py
python3 verify-hand-edits.py
python3 tools/validate-tree.py --vendor
