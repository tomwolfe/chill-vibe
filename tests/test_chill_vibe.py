import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys
import importlib.util
from pathlib import Path
import json

# Load chill-vibe.py as a module
file_path = os.path.abspath("chill-vibe.py")
module_name = "chill_vibe"

# Mock the genai and git_dump imports before executing the module
mock_genai = MagicMock()
sys.modules["google.genai"] = mock_genai
sys.modules["google.genai.types"] = MagicMock()
mock_git_dump = MagicMock()
sys.modules["git_dump"] = mock_git_dump
sys.modules["git_dump.core"] = MagicMock()
mock_git_dump_core = sys.modules["git_dump.core"]
sys.modules["yaml"] = MagicMock()

spec = importlib.util.spec_from_file_location(module_name, file_path)
chill_vibe = importlib.util.module_from_spec(spec)
sys.modules[module_name] = chill_vibe
spec.loader.exec_module(chill_vibe)

class TestChillVibe(unittest.TestCase):

    def test_run_git_dump_success(self):
        with patch('git_dump.core.RepoProcessor') as mock_processor_class, \
             patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_dir', return_value=True):
            chill_vibe.run_git_dump("repo/path", "output.txt", ["*.log"])
            mock_processor_class.assert_called_once_with("repo/path", "output.txt", ignore_patterns=["*.log"])
            mock_processor_class.return_value.process.assert_called_once()

    def test_run_git_dump_non_git(self):
        with patch('git_dump.core.RepoProcessor') as mock_processor_class, \
             patch('pathlib.Path.exists', return_value=False), \
             patch('builtins.print') as mock_print:
            chill_vibe.run_git_dump("repo/path", "output.txt")
            mock_print.assert_any_call("[!] Warning: repo/path is not a valid git repository. Falling back to standard folder processing.")
            mock_processor_class.assert_called_once_with("repo/path", "output.txt", ignore_patterns=None)

    @patch('builtins.open', new_callable=mock_open, read_data="code context")
    @patch('os.path.exists')
    @patch.dict('os.environ', {'GEMINI_API_KEY': 'test_key'})
    def test_get_strategic_reasoning_success(self, mock_exists, mock_file):
        mock_exists.side_effect = lambda p: p == "context.txt"
        
        with patch.object(chill_vibe.genai, 'Client') as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_response = MagicMock()
            mock_response.text = "Analysis... <agent_prompt>Work on this project</agent_prompt> Goals..."
            mock_client.models.generate_content.return_value = mock_response
            
            prompt = chill_vibe.get_strategic_reasoning(".", "context.txt", "model-id", "HIGH")
            
            self.assertEqual(prompt, "Work on this project")
            mock_client.models.generate_content.assert_called_once()

    @patch('subprocess.Popen')
    @patch('threading.Thread')
    def test_run_coding_agent_with_extra_args(self, mock_thread, mock_popen):
        mock_process = MagicMock()
        mock_popen.return_value = mock_process
        mock_process.stdin = MagicMock()
        
        registry = chill_vibe.get_agent_registry()
        config_data = {"extra_args": ["--no-auto-commit", "--verbose"]}
        chill_vibe.run_coding_agent("gemini-cli", "Start mission", registry, config_data)
        
        args, kwargs = mock_popen.call_args
        command = args[0]
        self.assertIn("--no-auto-commit", command)
        self.assertIn("--verbose", command)
        self.assertIn("npx", command)

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists', return_value=True)
    def test_load_config_json(self, mock_exists, mock_file):
        mock_file.return_value.__enter__.return_value.read.return_value = '{"extra_args": ["--test"]}'
        
        # We need to mock json.load because it's called on the file handle
        with patch('json.load', return_value={"extra_args": ["--test"]}):
            config = chill_vibe.load_config(".")
            self.assertEqual(config, {"extra_args": ["--test"]})

    @patch('builtins.open', new_callable=mock_open)
    def test_log_mission(self, mock_file):
        chill_vibe.log_mission("New Prompt", "model-x")
        
        mock_file.assert_called_with(Path(".chillvibe_logs.jsonl"), "a")
        handle = mock_file()
        write_call = handle.write.call_args[0][0]
        log_entry = json.loads(write_call)
        self.assertEqual(log_entry["agent_prompt"], "New Prompt")
        self.assertEqual(log_entry["model_id"], "model-x")
        self.assertIn("timestamp", log_entry)

    def test_forward_stdin(self):
        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        
        with patch('sys.stdin.read', side_effect=['a', 'b', '']):
            chill_vibe.forward_stdin(mock_process)
            
        self.assertEqual(mock_process.stdin.write.call_count, 2)
        mock_process.stdin.write.assert_any_call('a')
        mock_process.stdin.write.assert_any_call('b')
        mock_process.stdin.close.assert_called_once()

    @patch('shutil.which')
    @patch('sys.exit')
    def test_validate_environment_success(self, mock_exit, mock_which):
        mock_which.return_value = "/usr/bin/something"
        registry = chill_vibe.get_agent_registry()
        chill_vibe.validate_environment("gemini-cli", registry)
        mock_exit.assert_not_called()

    def test_get_agent_registry_defaults(self):
        registry = chill_vibe.get_agent_registry()
        self.assertIn("gemini-cli", registry)
        self.assertIn("aider", registry)
        self.assertEqual(registry["gemini-cli"].command, ["npx", "@google/gemini-cli", "--yolo"])

    @patch('chill_vibe.load_config')
    @patch('chill_vibe.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    def test_get_agent_registry_merging(self, mock_yaml, mock_file, mock_exists, mock_load_config):
        mock_exists.return_value = True
        mock_load_config.return_value = {"agents": {"custom-local": {"command": ["local-cmd"]}}}
        mock_yaml.return_value = {"custom-global": {"command": ["global-cmd"]}}
        
        registry = chill_vibe.get_agent_registry(repo_path=".")
        self.assertIn("custom-global", registry)
        self.assertIn("custom-local", registry)
        self.assertIn("gemini-cli", registry)
        self.assertEqual(registry["custom-global"].command, ["global-cmd"])
        self.assertEqual(registry["custom-local"].command, ["local-cmd"])

if __name__ == '__main__':
    unittest.main()