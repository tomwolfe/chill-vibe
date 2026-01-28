import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys
from pathlib import Path
import json

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from chill_vibe import cli, reasoning, execution, config, doctor, context

class TestChillVibe(unittest.TestCase):

    def test_run_git_dump_success(self):
        with patch('git_dump.core.RepoProcessor') as mock_processor_class, \
             patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_dir', return_value=True):
            context.run_git_dump("repo/path", "output.txt", ["*.log"], depth=2, include_ext="py,md")
            mock_processor_class.assert_called_once_with(
                "repo/path", "output.txt", 
                ignore_patterns=["*.log"],
                include_patterns=["*.py", "*.md"]
            )
            mock_processor_class.return_value.process.assert_called_once()

    def test_run_git_dump_non_git(self):
        with patch('git_dump.core.RepoProcessor') as mock_processor_class, \
             patch('pathlib.Path.exists', return_value=False), \
             patch('builtins.print') as mock_print:
            context.run_git_dump("repo/path", "output.txt")
            mock_print.assert_any_call("[!] Warning: repo/path is not a valid git repository. Falling back to standard folder processing.")
            mock_processor_class.assert_called_once_with(
                "repo/path", "output.txt", 
                ignore_patterns=None,
                include_patterns=None
            )

    @patch('builtins.open', new_callable=mock_open, read_data="code context")
    @patch('os.path.exists')
    @patch.dict('os.environ', {'GEMINI_API_KEY': 'test_key'})
    def test_get_strategic_reasoning_success(self, mock_exists, mock_file):
        mock_exists.side_effect = lambda p: p == "context.txt"
        
        with patch('google.genai.Client') as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_response = MagicMock()
            mock_response.text = "Analysis... <agent_prompt>Work on this project</agent_prompt> Goals..."
            mock_client.models.generate_content.return_value = mock_response
            
            prompt = reasoning.get_strategic_reasoning(".", "context.txt", "model-id", "HIGH")
            
            self.assertEqual(prompt, "Work on this project")
            mock_client.models.generate_content.assert_called_once()

    @patch('subprocess.Popen')
    @patch('threading.Thread')
    def test_run_coding_agent_with_extra_args(self, mock_thread, mock_popen):
        mock_process = MagicMock()
        mock_popen.return_value = mock_process
        mock_process.stdin = MagicMock()
        mock_process.wait.return_value = 0
        
        registry = config.get_agent_registry()
        config_data = {"extra_args": ["--no-auto-commit", "--verbose"]}
        exit_code = execution.run_coding_agent("gemini-cli", "Start mission", registry, config_data)
        
        self.assertEqual(exit_code, 0)
        args, kwargs = mock_popen.call_args
        command = args[0]
        self.assertIn("--no-auto-commit", command)
        self.assertIn("--verbose", command)
        self.assertIn("npx", command)

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists', return_value=True)
    def test_load_config_json(self, mock_exists, mock_file):
        mock_file.return_value.__enter__.return_value.read.return_value = '{"extra_args": ["--test"]}'
        
        with patch('json.load', return_value={"extra_args": ["--test"]}):
            conf = config.load_config(".")
            self.assertEqual(conf, {"extra_args": ["--test"]})

    @patch('builtins.open', new_callable=mock_open)
    def test_log_mission(self, mock_file):
        reasoning.log_mission("New Prompt", "model-x", "gemini-cli", 12.34, status="COMPLETED")
        
        mock_file.assert_called_with(Path(".chillvibe_logs.jsonl"), "a")
        handle = mock_file()
        write_call = handle.write.call_args[0][0]
        log_entry = json.loads(write_call)
        self.assertEqual(log_entry["agent_prompt"], "New Prompt")
        self.assertEqual(log_entry["model_id"], "model-x")
        self.assertEqual(log_entry["agent_name"], "gemini-cli")
        self.assertEqual(log_entry["duration_seconds"], 12.34)
        self.assertEqual(log_entry["status"], "COMPLETED")
        self.assertIn("timestamp", log_entry)

    @patch('builtins.print')
    @patch('builtins.input', return_value='n')
    @patch('shutil.which', return_value="/usr/bin/git")
    @patch('subprocess.check_output', return_value="git version 2.39.2")
    @patch.dict('os.environ', {'GEMINI_API_KEY': 'AIza...test'})
    def test_run_doctor_interactive_decline(self, mock_git_ver, mock_which, mock_input, mock_print):
        registry = config.get_agent_registry()
        with patch('chill_vibe.doctor.genai', None), \
             patch('chill_vibe.doctor.git_dump', None):
            doctor.run_doctor(registry)
            
        mock_print.assert_any_call("[✗] google-genai: Not installed")
        mock_print.assert_any_call("[✗] git-dump: Not installed")

    @patch('builtins.print')
    @patch('builtins.input', return_value='y')
    @patch('shutil.which', return_value="/usr/bin/git")
    @patch('subprocess.check_output', return_value="git version 2.39.2")
    @patch.dict('os.environ', {'GEMINI_API_KEY': 'AIza...test'})
    def test_run_doctor_interactive_accept(self, mock_git_ver, mock_which, mock_input, mock_print):
        registry = config.get_agent_registry()
        with patch('chill_vibe.doctor.genai', None), \
             patch('chill_vibe.doctor.git_dump', MagicMock()), \
             patch('chill_vibe.doctor.install_package') as mock_install:
            doctor.run_doctor(registry)
            mock_install.assert_any_call("google-genai")

    @patch('subprocess.check_call')
    @patch('builtins.print')
    def test_install_package(self, mock_print, mock_call):
        doctor.install_package("some-pkg")
        mock_call.assert_called_once()
        mock_print.assert_any_call("[✓] Successfully installed some-pkg")

    def test_forward_stdin(self):
        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        mock_process.poll.side_effect = [None, None, None, 0]
        
        with patch('sys.stdin.read', side_effect=['a', 'b', '']), \
             patch('sys.stdin.isatty', return_value=False):
            execution.forward_stdin(mock_process)
            
        self.assertEqual(mock_process.stdin.write.call_count, 2)
        mock_process.stdin.write.assert_any_call('a')
        mock_process.stdin.write.assert_any_call('b')
        mock_process.stdin.close.assert_called_once()

    @patch('shutil.which')
    @patch('sys.exit')
    def test_validate_environment_success(self, mock_exit, mock_which):
        mock_which.return_value = "/usr/bin/something"
        registry = config.get_agent_registry()
        with patch('chill_vibe.doctor.genai', MagicMock()), \
             patch('chill_vibe.doctor.git_dump', MagicMock()):
            doctor.validate_environment("gemini-cli", registry)
        mock_exit.assert_not_called()

    def test_get_agent_registry_defaults(self):
        registry = config.get_agent_registry()
        self.assertIn("gemini-cli", registry)
        self.assertIn("aider", registry)
        self.assertEqual(registry["gemini-cli"].command, ["npx", "@google/gemini-cli", "--yolo"])

    def test_get_agent_registry_merging(self):
        with patch('chill_vibe.config.load_config') as mock_load_config, \
             patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', new_callable=mock_open), \
             patch('yaml.safe_load') as mock_yaml:
             
            mock_load_config.return_value = {"agents": {"custom-local": {"command": ["local-cmd"]}}}
            mock_yaml.return_value = {"custom-global": {"command": ["global-cmd"]}}
            
            registry = config.get_agent_registry(repo_path=".")
            self.assertIn("custom-global", registry)
            self.assertIn("custom-local", registry)
            self.assertIn("gemini-cli", registry)
            self.assertEqual(registry["custom-global"].command, ["global-cmd"])
            self.assertEqual(registry["custom-local"].command, ["local-cmd"])

if __name__ == '__main__':
    unittest.main()
