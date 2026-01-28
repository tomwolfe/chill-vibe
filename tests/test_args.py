import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from chill_vibe import cli, config

class TestArgs(unittest.TestCase):
    def test_default_args(self):
        registry = config.get_agent_registry()
        parser = cli.get_parser(registry)
        args = parser.parse_args(['.'])
        self.assertEqual(args.path, '.')
        self.assertEqual(args.context_file, 'codebase_context.txt')
        self.assertFalse(args.cleanup)
        self.assertFalse(args.dry_run)

    def test_custom_context_file(self):
        registry = config.get_agent_registry()
        parser = cli.get_parser(registry)
        args = parser.parse_args(['.', '--context-file', 'custom.txt'])
        self.assertEqual(args.context_file, 'custom.txt')

    def test_cleanup_flag(self):
        registry = config.get_agent_registry()
        parser = cli.get_parser(registry)
        args = parser.parse_args(['.', '--cleanup'])
        self.assertTrue(args.cleanup)

    def test_dry_run_flag(self):
        registry = config.get_agent_registry()
        parser = cli.get_parser(registry)
        args = parser.parse_args(['.', '--dry-run'])
        self.assertTrue(args.dry_run)

    def test_doctor_flag(self):
        registry = config.get_agent_registry()
        parser = cli.get_parser(registry)
        args = parser.parse_args(['--doctor'])
        self.assertTrue(args.doctor)

    def test_depth_arg(self):
        registry = config.get_agent_registry()
        parser = cli.get_parser(registry)
        args = parser.parse_args(['.', '--depth', '3'])
        self.assertEqual(args.depth, 3)

    def test_include_ext_arg(self):
        registry = config.get_agent_registry()
        parser = cli.get_parser(registry)
        args = parser.parse_args(['.', '--include-ext', 'py,md'])
        self.assertEqual(args.include_ext, 'py,md')

    def test_history_flag(self):
        registry = config.get_agent_registry()
        parser = cli.get_parser(registry)
        args = parser.parse_args(['--history'])
        self.assertTrue(args.history)

if __name__ == '__main__':
    unittest.main()
