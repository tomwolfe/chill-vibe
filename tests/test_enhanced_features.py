import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys
from pathlib import Path
import json
import re

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from chill_vibe import execution, reasoning

class TestEnhancedFeatures(unittest.TestCase):

    def test_verify_success_exists(self):
        criteria = ["exists: README.md"]
        with patch('chill_vibe.execution.Path') as mock_path:
            # Mock the result of Path(repo_path) / path_str
            mock_path_obj = MagicMock()
            mock_path.return_value.__truediv__.return_value = mock_path_obj
            mock_path_obj.exists.return_value = True
            
            passed, results = execution.verify_success(criteria, ".")
            self.assertTrue(passed)
            self.assertEqual(results[0]["passed"], True)
            self.assertIn("exists: True", results[0]["info"])

    def test_verify_success_contains(self):
        content = "Hello World\nSuccess criteria met."
        with patch('builtins.open', mock_open(read_data=content)), \
             patch('chill_vibe.execution.Path.exists', return_value=True):
            criteria = ["contains: log.txt Success"]
            passed, results = execution.verify_success(criteria, ".")
            self.assertTrue(passed)
            self.assertEqual(results[0]["passed"], True)
            self.assertIn("found in log.txt", results[0]["info"])

    def test_verify_success_not_contains(self):
        content = "Error: something went wrong."
        with patch('builtins.open', mock_open(read_data=content)), \
             patch('chill_vibe.execution.Path.exists', return_value=True):
            criteria = ["not_contains: log.txt Success"]
            passed, results = execution.verify_success(criteria, ".")
            self.assertTrue(passed)
            self.assertEqual(results[0]["passed"], True)
            self.assertIn("not found in log.txt", results[0]["info"])

    def test_verify_success_contains_fail(self):
        content = "Error: something went wrong."
        with patch('builtins.open', mock_open(read_data=content)), \
             patch('chill_vibe.execution.Path.exists', return_value=True):
            criteria = ["contains: log.txt Success"]
            passed, results = execution.verify_success(criteria, ".")
            self.assertFalse(passed)
            self.assertEqual(results[0]["passed"], False)

    def test_classify_failure_signals(self):
        output = ["Traceback (most recent call last):\n", "  File \"test.py\", line 1, in <module>\n", "    import non_existent_module\n", "ModuleNotFoundError: No module named 'non_existent_module'\n"]
        signals = reasoning.classify_failure_signals(1, output)
        self.assertIn("DEPENDENCY_MISSING", signals)

        output = ["/bin/sh: line 1: some-command: command not found\n"]
        signals = reasoning.classify_failure_signals(127, output)
        self.assertIn("COMMAND_NOT_FOUND", signals)

        output = ["AssertionError: 1 != 2\n"]
        signals = reasoning.classify_failure_signals(1, output)
        self.assertIn("TEST_FAILURE", signals)

    @patch('google.genai.Client')
    def test_get_recovery_strategy_with_signals(self, mock_client_class):
        mock_client = mock_client_class.return_value
        mock_response = MagicMock()
        mock_response.text = "Analysis... <classification>TOOLING</classification> <agent_prompt>Try installing the module</agent_prompt>"
        mock_client.models.generate_content.return_value = mock_response
        
        output = ["ModuleNotFoundError: No module named 'requests'\n"]
        prompt, classification = reasoning.get_recovery_strategy(".", "model-id", "Original Prompt", output, exit_code=1)
        
        self.assertEqual(classification, "TOOLING")
        self.assertEqual(prompt, "Try installing the module")
        
        # Verify that signals were likely in the prompt (by checking the call)
        call_args = mock_client.models.generate_content.call_args[1]
        self.assertIn("DEPENDENCY_MISSING", call_args['contents'])

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists', return_value=True)
    def test_log_mission_with_verification(self, mock_exists, mock_file):
        verification_results = [{"command": "exists: test.txt", "passed": True, "info": "Path test.txt exists: True"}]
        reasoning.log_mission("Prompt", "model", "agent", 1.0, status="COMPLETED", verification_results=verification_results)
        
        handle = mock_file()
        write_call = handle.write.call_args[0][0]
        log_entry = json.loads(write_call)
        self.assertEqual(log_entry["verification_results"], verification_results)

if __name__ == '__main__':
    unittest.main()
