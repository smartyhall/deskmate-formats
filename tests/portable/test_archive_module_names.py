"""Guard archival module names against standard-library collisions.

``tools/archive`` is placed on ``sys.path`` so its modules can be run and
imported directly. A file in that directory therefore shadows any standard
library module with the same name for the rest of the process. Python 3.14
added a ``compression`` package, which is exactly how the suite broke under
3.14 while passing under 3.13.
"""

import importlib
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


TOOLS = Path(__file__).resolve().parents[2] / 'tools' / 'archive'
ARCHIVE_MODULES = ('compression_streams', 'disk_images', 'intelligence_extract')


class ModuleNameTests(unittest.TestCase):
    def test_no_archival_module_shadows_a_standard_library_name(self):
        names = {path.stem for path in TOOLS.glob('*.py')}
        self.assertIn('compression_streams', names)
        self.assertEqual(sorted(names & set(sys.stdlib_module_names)), [])

    def test_stream_module_imports_after_the_standard_library_package(self):
        # Emulate a process in which the standard-library package is already
        # imported, whether or not this interpreter actually ships it.
        stdlib = types.ModuleType('compression')
        stdlib.__path__ = []
        with patch.dict(sys.modules, {'compression': stdlib}):
            sys.modules.pop('compression_streams', None)
            with patch.object(sys, 'path', [str(TOOLS), *sys.path]):
                module = importlib.import_module('compression_streams')
            self.assertIs(sys.modules['compression'], stdlib)
            self.assertEqual(module.__name__, 'compression_streams')
            self.assertTrue(callable(module.decode_unix_compress))
            self.assertTrue(callable(module.decode_bzip2))
        # The stand-in must not survive the test.
        self.assertIsNot(sys.modules.get('compression'), stdlib)

    def test_extractor_imports_while_the_standard_library_package_is_loaded(self):
        stdlib = types.ModuleType('compression')
        stdlib.__path__ = []
        with patch.dict(sys.modules, {'compression': stdlib}):
            for name in ARCHIVE_MODULES:
                sys.modules.pop(name, None)
            with patch.object(sys, 'path', [str(TOOLS), *sys.path]):
                module = importlib.import_module('intelligence_extract')
            self.assertTrue(module.CONTAINER_KINDS)
            self.assertIn('unix-compress', module.CONTAINER_KINDS)
            self.assertIs(sys.modules['compression'], stdlib)

    def test_capability_checker_resolves_the_stream_module(self):
        with patch.object(sys, 'path', [str(TOOLS), *sys.path]):
            capabilities = importlib.import_module('capabilities')
        modules = capabilities._modules()
        self.assertIn('compression_streams', modules)
        self.assertNotIn('compression', modules)
        self.assertTrue(hasattr(modules['compression_streams'], 'decode_xz'))


if __name__ == '__main__':
    unittest.main()
