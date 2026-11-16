#!/usr/bin/env python3
"""Compile and exercise the exact UDFPS state machine stored in patch 0005."""
from pathlib import Path
import subprocess
import tempfile
here = Path(__file__).resolve().parent
patch = here.parents[1] / 'patches/lineage24/0005-udfps-idle-aod-refresh-rate.patch'
source = patch.read_text().split('+++ b/packages/SystemUI/src/com/android/systemui/biometrics/UdfpsRefreshRateController.java\n', 1)[1]
source = '\n'.join(line[1:] for line in source.splitlines() if line.startswith('+')) + '\n'
with tempfile.TemporaryDirectory(prefix='degas-udfps-test-') as tmp:
    java = Path(tmp) / 'UdfpsRefreshRateController.java'
    java.write_text(source)
    subprocess.run(['javac', '-d', tmp, str(java), str(here / 'UdfpsRefreshRateControllerTest.java')], check=True)
    subprocess.run(['java', '-cp', tmp, 'com.android.systemui.biometrics.UdfpsRefreshRateControllerTest'], check=True)
