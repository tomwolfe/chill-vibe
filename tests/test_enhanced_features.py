import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys
from pathlib import Path
import json
import re

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from chill_vibe import execution, reasoning, context

class TestEnhancedFeatures(unittest.TestCase):

    def test_mission_contract_from_json(self):
        mission_json = json.dumps({
            "objectives": ["Goal 1"],
            "success_criteria": ["exists: file.txt"],
            "summary": "Fix the bug",
            "checklist": ["Task 1"],
            "non_goals": ["Goal 2"],
            "forbidden_actions": ["Delete all"]
        })
        mission = context.MissionContract.from_json(mission_json, "Prompt")
        self.assertEqual(mission.objectives, ["Goal 1"])
        self.assertEqual(mission.success_criteria, ["exists: file.txt"])
        self.assertEqual(mission.agent_prompt, "Prompt")
        self.assertEqual(mission.summary, "Fix the bug")

    def test_mission_contract_validation(self):
        mission = context.MissionContract(
            objectives=["Goal 1"],
            success_criteria=["exists: file.txt"],
            agent_prompt="Prompt"
        )
        valid, msg = mission.validate()
        self.assertTrue(valid)

        # Missing objectives
        mission_invalid = context.MissionContract(
            objectives=[],
            success_criteria=["exists: file.txt"],
            agent_prompt="Prompt"
        )
        valid, msg = mission_invalid.validate()
        self.assertFalse(valid)
        self.assertIn("at least one objective", msg)

        # Objectives not a list
        mission_invalid = context.MissionContract(
            objectives="not a list",
            success_criteria=["exists: file.txt"],
            agent_prompt="Prompt"
        )
        valid, msg = mission_invalid.validate()
        self.assertFalse(valid)

        # Success criteria not a list
        mission_invalid = context.MissionContract(
            objectives=["Goal 1"],
            success_criteria="not a list",
            agent_prompt="Prompt"
        )
        valid, msg = mission_invalid.validate()
        self.assertFalse(valid)

        # Empty agent prompt
        mission_invalid = context.MissionContract(
            objectives=["Goal 1"],
            success_criteria=["exists: file.txt"],
            agent_prompt="   "
        )
        valid, msg = mission_invalid.validate()
        self.assertFalse(valid)
        self.assertIn("non-empty agent prompt", msg)

    def test_mission_contract_validation_success_criteria_type(self):
        # Success criterion not a string
        mission_invalid = context.MissionContract(
            objectives=["Goal 1"],
            success_criteria=[123],
            agent_prompt="Prompt"
        )
        valid, msg = mission_invalid.validate()
        self.assertFalse(valid)
        self.assertIn("must be a string", msg)

    @patch('chill_vibe.execution.get_file_baseline')
    def test_verify_success_no_new_files(self, mock_get_baseline):
        mock_get_baseline.return_value = {"file1.txt"}
        criteria = ["no_new_files"]
        
        # Scenario 1: No new files
        with patch('chill_vibe.execution.get_file_baseline', side_effect=[{"file1.txt"}]) as mock_current:
            passed, results = execution.verify_success(criteria, ".", file_baseline={"file1.txt"})
            self.assertTrue(passed)

        # Scenario 2: New files detected
        with patch('chill_vibe.execution.get_file_baseline', side_effect=[{"file1.txt", "file2.txt"}]) as mock_current:
            passed, results = execution.verify_success(criteria, ".", file_baseline={"file1.txt"})
            self.assertFalse(passed)
            self.assertIn("file2.txt", results[0]["message"])

    @patch('subprocess.run')
    def test_verify_success_pytest(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="Tests passed", stderr="")
        criteria = ["pytest"]
        passed, results = execution.verify_success(criteria, ".")
        self.assertTrue(passed)
        mock_run.assert_called_with("pytest", shell=True, cwd=".", capture_output=True, text=True)
        self.assertEqual(results[0]["details"]["exit_code"], 0)

    @patch('subprocess.run')
    def test_verify_success_ruff(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="Lint errors", stderr="")
        criteria = ["ruff"]
        passed, results = execution.verify_success(criteria, ".")
        self.assertFalse(passed)
        mock_run.assert_called_with("ruff check .", shell=True, cwd=".", capture_output=True, text=True)
        self.assertEqual(results[0]["details"]["exit_code"], 1)

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
            self.assertIn("exists: True", results[0]["message"])

    def test_verify_success_contains(self):
        content = "Hello World\nSuccess criteria met."
        with patch('builtins.open', mock_open(read_data=content)), \
             patch('chill_vibe.execution.Path.exists', return_value=True):
            criteria = ["contains: log.txt Success"]
            passed, results = execution.verify_success(criteria, ".")
            self.assertTrue(passed)
            self.assertEqual(results[0]["passed"], True)
            self.assertIn("found in log.txt", results[0]["message"])

    def test_verify_success_not_contains(self):
        content = "Error: something went wrong."
        with patch('builtins.open', mock_open(read_data=content)), \
             patch('chill_vibe.execution.Path.exists', return_value=True):
            criteria = ["not_contains: log.txt Success"]
            passed, results = execution.verify_success(criteria, ".")
            self.assertTrue(passed)
            self.assertEqual(results[0]["passed"], True)
            self.assertIn("not found in log.txt", results[0]["message"])

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
