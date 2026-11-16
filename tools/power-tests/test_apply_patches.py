import difflib
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('applier', Path(__file__).parents[1] / 'apply-patches.py')
applier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(applier)

class StackedPatches(unittest.TestCase):
    def test_clean_partial_complete_and_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def git(*args):
                return subprocess.check_output(['git', '-C', tmp, *map(str, args)])
            git('init', '-q')
            git('config', 'user.name', 'Test')
            git('config', 'user.email', 'test@example.invalid')
            target = root / 'file'
            target.write_text('before\n')
            git('add', 'file'); git('commit', '-qm', 'base')
            patches = []
            for i, (before, after) in enumerate([('before\n', 'first\n'), ('first\n', 'second\n')]):
                patch = root / f'{i}.patch'
                patch.write_text(''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile='a/file', tofile='b/file')))
                patches.append(patch)
            patches[1].write_text(patches[1].read_text() + '--- /dev/null\n+++ b/new\n@@ -0,0 +1 @@\n+new file\n')
            index = (root / '.git/index').read_bytes()
            for count in range(3):
                pending = applier.validate_series(root, patches)
                self.assertEqual(pending, set(patches[count:]))
                self.assertEqual((root / '.git/index').read_bytes(), index)
                if count < 2:
                    git('apply', patches[count])
            self.assertEqual(target.read_text(), 'second\n')
            target.write_text('conflict\n')
            with self.assertRaises(SystemExit):
                applier.validate_series(root, patches)
            self.assertEqual(target.read_text(), 'conflict\n')
            self.assertEqual((root / '.git/index').read_bytes(), index)

if __name__ == '__main__': unittest.main()
