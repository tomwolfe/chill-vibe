# MIT License
# 
# Copyright (c) 2026 Thomas Wolfe
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from chill_vibe import cli

class TestConfigHierarchy(unittest.TestCase):
    def setUp(self):
        self.registry = {}
        self.parser = cli.get_parser(self.registry)

    def test_cli_overrides_all(self):
        args = self.parser.parse_args(['.', '--thinking', 'LOW', '--model', 'cli-model', '--depth', '1'])
        config_data = {'thinking_level': 'MEDIUM', 'model': 'local-model', 'depth': 2}
        global_config = {'thinking_level': 'HIGH', 'model': 'global-model', 'depth': 3}
        
        resolved_args = cli.resolve_config(args, config_data, global_config)
        
        self.assertEqual(resolved_args.thinking, 'LOW')
        self.assertEqual(resolved_args.model, 'cli-model')
        self.assertEqual(resolved_args.depth, 1)

    def test_local_overrides_global(self):
        args = self.parser.parse_args(['.']) # No CLI flags for these
        config_data = {'thinking_level': 'MEDIUM', 'model': 'local-model', 'depth': 2}
        global_config = {'thinking_level': 'HIGH', 'model': 'global-model', 'depth': 3}
        
        resolved_args = cli.resolve_config(args, config_data, global_config)
        
        self.assertEqual(resolved_args.thinking, 'MEDIUM')
        self.assertEqual(resolved_args.model, 'local-model')
        self.assertEqual(resolved_args.depth, 2)

    def test_global_overrides_defaults(self):
        args = self.parser.parse_args(['.'])
        config_data = {}
        global_config = {'thinking_level': 'HIGH', 'model': 'global-model', 'depth': 3}
        
        resolved_args = cli.resolve_config(args, config_data, global_config)
        
        self.assertEqual(resolved_args.thinking, 'HIGH')
        self.assertEqual(resolved_args.model, 'global-model')
        self.assertEqual(resolved_args.depth, 3)

    def test_defaults_fallthrough(self):
        args = self.parser.parse_args(['.'])
        config_data = {}
        global_config = {}
        
        # We need to mock DEFAULT_CONFIG as it's used in resolve_config
        with patch('chill_vibe.cli.DEFAULT_CONFIG', {'model': 'default-model'}):
            resolved_args = cli.resolve_config(args, config_data, global_config)
        
        self.assertEqual(resolved_args.thinking, 'HIGH') # Hardcoded default in resolve_config
        self.assertEqual(resolved_args.model, 'default-model')
        self.assertIsNone(resolved_args.depth)

        def test_flash_shortcut(self):
            args = self.parser.parse_args(['.', '--model', 'flash'])
            config_data = {}
            global_config = {}
        
            resolved_args = cli.resolve_config(args, config_data, global_config)
            self.assertEqual(resolved_args.model, 'gemini-2.0-flash')
if __name__ == '__main__':
    unittest.main()
