import unittest
from unittest.mock import patch
import sys
import os
import importlib.util

# Load chill-vibe.py as a module
file_path = os.path.abspath("chill-vibe.py")
module_name = "chill_vibe"

# Mock the genai and git_dump imports before executing the module
sys.modules["google.genai"] = unittest.mock.MagicMock()
sys.modules["google.genai.types"] = unittest.mock.MagicMock()
sys.modules["git_dump"] = unittest.mock.MagicMock()
sys.modules["git_dump.core"] = unittest.mock.MagicMock()

spec = importlib.util.spec_from_file_location(module_name, file_path)
chill_vibe = importlib.util.module_from_spec(spec)
sys.modules[module_name] = chill_vibe
spec.loader.exec_module(chill_vibe)

class TestArgs(unittest.TestCase):
    def test_default_args(self):
        registry = chill_vibe.get_agent_registry()
        parser = chill_vibe.get_parser(registry)
        args = parser.parse_args(['.'])
        self.assertEqual(args.path, '.')
        self.assertEqual(args.context_file, 'codebase_context.txt')
        self.assertFalse(args.cleanup)
        self.assertFalse(args.dry_run)

    def test_custom_context_file(self):
        registry = chill_vibe.get_agent_registry()
        parser = chill_vibe.get_parser(registry)
        args = parser.parse_args(['.', '--context-file', 'custom.txt'])
        self.assertEqual(args.context_file, 'custom.txt')

    def test_cleanup_flag(self):
        registry = chill_vibe.get_agent_registry()
        parser = chill_vibe.get_parser(registry)
        args = parser.parse_args(['.', '--cleanup'])
        self.assertTrue(args.cleanup)

    def test_dry_run_flag(self):
        registry = chill_vibe.get_agent_registry()
        parser = chill_vibe.get_parser(registry)
        args = parser.parse_args(['.', '--dry-run'])
        self.assertTrue(args.dry_run)

if __name__ == '__main__':
    unittest.main()